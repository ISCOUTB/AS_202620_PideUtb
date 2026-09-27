# ADR 0004: Desplegar la API en un contenedor con proceso persistente, y no en funciones sin servidor

## Estado

Aceptada — 27/09/2026

## Contexto

Hasta esta entrega el sistema solo existía en las máquinas del equipo. La
condición operativa de la asignatura obliga a desplegarlo en algún entorno
accesible desde fuera, y el equipo no dispone de presupuesto: el coste tiene que
ser **cero**, no «bajo».

Esa restricción no es un detalle administrativo. Elimina de entrada la salida
habitual —pagar por un plan que no tenga las limitaciones molestas— y convierte
la elección en la pregunta interesante: *entre dos plataformas gratuitas que
fallan de maneras distintas, ¿cuál falla de la manera que este sistema puede
absorber?*

### El sistema que hay que desplegar

Tres características importan para la decisión, y las tres salen de decisiones
ya tomadas y documentadas:

1. **El tráfico es una ráfaga, no un goteo.** El pico de almuerzo concentra casi
   todo el uso en unas dos horas; el resto del día el sistema está
   prácticamente ocioso.
2. **La confirmación del pago llega por webhook** ([ADR-0003](0003-estrategia-integracion.md)).
   Es una llamada entrante que origina un tercero, en un momento que nosotros no
   elegimos, y que hay que atender cuando llegue.
3. **El estado tiene que vivir en PostgreSQL gestionado** (arc42 §2.1). La API
   abre conexiones contra una base de datos externa.

### El escenario que fuerza la decisión

<a id="escenario-motivador"></a>

**[ESC-02 — Pedido de un usuario recurrente en hora pico](../arc42/arc42.md#esc-02)**,
cuya medida de respuesta es: *el proceso completo toma menos de **2 minutos** en
al menos el 90 % de los intentos*.

Conviene ser preciso con qué mide ese escenario, porque de ahí sale el
argumento. No son 2 segundos de latencia de API: son **120 segundos para el
recorrido entero del usuario** —ver la carta, elegir, confirmar y llegar a la
confirmación del pago—, y ese presupuesto incluye el tiempo que tarda una
persona en decidir.

Es el umbral que discrimina porque es el único que una plataforma gratuita puede
incumplir **sin estar caída**. Un servicio dormido que tarda unos 60 segundos en
despertar está funcionando perfectamente según su proveedor, y acaba de
consumir **la mitad del presupuesto de ESC-02** antes de que el usuario vea la
carta.

## Alternativas consideradas

Las dos se evaluaron contra veinte criterios en
[`docs/comparacion-despliegue.md`](../comparacion-despliegue.md). Aquí se
resumen los tres puntos en que difieren de verdad.

### A — Contenedor con proceso persistente (plan gratuito de Render)

Un proceso que vive entre peticiones, con 512 MB de memoria y sin límite de
horas de CPU. Se duerme tras 15 minutos sin tráfico y tarda alrededor de un
minuto en volver.

### B — Funciones sin servidor (plan Hobby de Vercel)

Una función que arranca por petición, con arranque en frío de cientos de
milisegundos en vez de un minuto, pero con **cuota mensual de CPU activa**: al
agotarse, el servicio deja de responder hasta el mes siguiente.

### Las dos se rompen, y ese es el hallazgo

Lo que hace decidible la comparación es que **no fallan por lo mismo**:

| | A · contenedor | B · funciones |
|---|---|---|
| **Cómo se rompe** | Latencia, desde el primer día | Cuota, al superar cierto volumen |
| **Cuándo** | En cada primer pedido tras 15 min de silencio | Estimado en ~1920 pedidos/día, ≈10× el volumen previsto |
| **Qué le pasa al usuario** | Espera ~60 s una vez, luego todo es rápido | El servicio deja de existir hasta el mes siguiente |
| **Se puede mitigar** | Sí: avisar y precalentar | No desde el código |

La cuota de B está lejos del volumen esperado; su riesgo es remoto pero
**irreversible dentro del mes**. La latencia de A es segura y ocurre a diario,
pero es **acotada, visible y mitigable**.

### Por qué no decidió eso, sino las conexiones

El motivo decisivo resultó ser otro, y conviene decirlo porque no era el
esperado al empezar la comparación.

Una función sin servidor **abre una conexión nueva a la base de datos en cada
arranque en frío** y no puede mantener un pool entre invocaciones: no hay
proceso donde guardarlo. Contra un plan gratuito de PostgreSQL, con su límite
bajo de conexiones concurrentes, un pico de almuerzo —justo el patrón de tráfico
de este sistema (contexto, punto 1)— produce muchas invocaciones simultáneas,
cada una reclamando su conexión. El modo de fallo no es lentitud: es
agotamiento del pool y errores.

Un contenedor con proceso persistente mantiene **un pool y lo reutiliza**. La
característica que parecía una desventaja de A —que el proceso siga vivo entre
peticiones— es exactamente lo que resuelve el problema.

## Decisión

**Se despliega la API como contenedor con proceso persistente en el plan
gratuito de Render**, y el sitio como estático en la misma plataforma.

La razón decisiva es el **manejo de conexiones a la base de datos**, no la
comparación de latencias ni la de cuotas. El patrón de tráfico del sistema es
una ráfaga concentrada, y es el peor caso posible para un modelo que abre una
conexión por invocación.

El arranque en frío se acepta **como coste conocido y se mitiga**, en lugar de
ignorarse:

- El sitio muestra un aviso explícito si la comprobación inicial tarda más de
  2,5 segundos (`sitio/config.js`, `MS_ANTES_DE_AVISAR_ARRANQUE_EN_FRIO`), para
  que el usuario sepa que el sistema está despertando y no que está roto.
- Se documenta que ESC-02 **no se cumple en la primera petición tras un periodo
  de inactividad**. Es una violación conocida y declarada, no un supuesto que
  nadie verificó.

## Consecuencias

### Lo que mejora

- Coste real de **0 USD/mes**, verificable en el plan de cada servicio.
- Un solo pool de conexiones, dimensionable, contra una base de datos gratuita
  con pocas conexiones disponibles.
- El webhook llega a un proceso vivo: no hay arranque en frío en el camino
  crítico de confirmar un pago, que es donde más caro sale.
- Sitio y API se despliegan por separado, así que un fallo de construcción del
  sitio no tumba la API.

### Lo que empeora, y hay que decir

- **ESC-02 queda en riesgo en el primer pedido tras 15 minutos de inactividad.**
  El arranque en frío se come unos 60 de los 120 segundos disponibles, así que
  el margen para el resto del recorrido —incluida la decisión del usuario— se
  reduce a la mitad. Ocurre al menos una vez al día, en el pico, y le toca a un
  usuario real.
- **El disco es efímero.** Nada que se escriba en el sistema de archivos
  sobrevive a un despliegue. Por eso los logs van a salida estándar y no a un
  archivo (`app/observabilidad.py`).
- **La API queda fuera de Terraform.** El proveedor de Render no sabe gestionar
  servicios web del plan gratuito
  ([issue #105](https://github.com/render-oss/terraform-provider-render/issues/105)),
  así que se crea a mano. Está anotado en [`infra/README.md`](../../infra/README.md)
  en lugar de fingir que está declarada.
- **Dependencia de un proveedor concreto** en la definición de infraestructura.
  Se acota manteniendo la aplicación en un contenedor estándar, sin usar
  ninguna API propietaria de la plataforma: mudarse exige reescribir `infra/`,
  no la aplicación.

### Cómo se sabrá si fue un error

Esta decisión se revisa si se cumple cualquiera de estas condiciones, que son
observables y no opiniones:

1. El p95 de `POST /v1/pedidos` en `GET /metricas`, **excluyendo** la primera
   petición tras inactividad, deja de ser despreciable frente a los 120 s de
   ESC-02. La métrica no mide ESC-02 —no puede: el escenario incluye tiempo
   humano en un navegador—, mide la parte del presupuesto que el servidor
   controla. Si esa parte crece, el problema ya no es el arranque en frío sino
   la plataforma.
2. Los 512 MB de memoria se quedan cortos al conectar la base de datos real.
3. El aviso de arranque en frío resulta insuficiente en pruebas con usuarios:
   si la gente abandona igual, la mitigación no mitiga.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Comparación completa, 20 criterios | [`docs/comparacion-despliegue.md`](../comparacion-despliegue.md) |
| Escenario que fuerza la decisión | [ESC-02](../arc42/arc42.md#esc-02) |
| Vista de despliegue | [arc42 §7](../arc42/arc42.md#7-vista-de-despliegue) |
| Restricción actualizada | arc42 §2.1 |
| Infraestructura declarada | [`infra/`](../../infra/) |
| Excepción fuera de Terraform | [`infra/README.md`](../../infra/README.md) |
| Mitigación del arranque en frío | `sitio/config.js`, `sitio/app.js` |
| Métrica de seguimiento | `GET /metricas` (`app/main.py`) |
| Integración asíncrona que condiciona el despliegue | [ADR-0003](0003-estrategia-integracion.md) |
