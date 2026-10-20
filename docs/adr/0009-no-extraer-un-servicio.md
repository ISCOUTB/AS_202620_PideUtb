# ADR 0009: No extraer ningún módulo a un servicio independiente, y dejar escrito qué lo cambiaría

## Estado

Aceptada — 18/10/2026

## Contexto

[ADR-0001](0001-estilo-arquitectonico.md) eligió un **monolito modular**: cuatro
contextos de dominio en un solo desplegable, que solo se comunican por funciones
públicas de servicio. La pregunta que esta decisión responde es la siguiente:
ahora que el sistema está desplegado y funcionando, **¿alguno de esos cuatro se
ha ganado salir a un servicio propio?**

Es una pregunta legítima y no retórica. El enunciado de la semana 11 pide
justificar **extraer o no extraer**, y responder «no» sin haber mirado sería tan
pobre como responder «sí» porque suena moderno.

### Qué habría que ver para que un módulo se quisiera extraer

Los motivos por los que un contexto se separa, y si este sistema los tiene:

| Motivo | ¿Ocurre aquí? |
|---|---|
| **Escalar una parte distinto del resto** | No. El sistema entero cabe en 512 MB y el cuello de botella medido no es ninguno de los cuatro módulos |
| **Aislar un fallo** para que no tumbe lo demás | No, y además ya está resuelto sin extraer: el bus de eventos aísla a los suscriptores, y el panel caído no afecta al cobro |
| **Equipos distintos con ritmos distintos** | No. Tres personas, un repositorio, un pipeline |
| **Tecnología distinta** para una parte | No. Los cuatro son Python sobre el mismo PostgreSQL |
| **Frontera de seguridad** más estricta | No. El único secreto fuerte —el de la pasarela— ya está aislado por variable de entorno y falla en cerrado |
| **Ciclo de despliegue independiente** | No. Se despliega todo junto y eso no ha estorbado |

Ninguna fila dice que sí. Pero conviene mirar el candidato concreto, porque la
tabla sola es demasiado fácil.

## El candidato real: `pagos`

Si algo se extrajera sería `pagos`, y por dos razones que sí tienen fundamento:

1. **Es la única frontera con un tercero.** Recibe el webhook de la pasarela, y
   esa ruta es alcanzable desde Internet por alguien que no somos nosotros.
2. **Es donde está el dinero**, y donde un fallo cuesta más que una pantalla
   fea.

Y aun así, no.

### Lo que la extracción resolvería

Honestamente: **poco**. La superficie de ataque del webhook ya está acotada por
la firma HMAC y por fallar en cerrado sin secreto
([V-11](../violaciones.md#v-11)). Extraerlo no haría esa firma más fuerte;
movería el mismo código a otro proceso.

### Lo que la extracción rompería

Esto sí es concreto, y es la parte que decide.

**`pagos` y `pedidos` escriben en la misma transacción lógica.** Un cobro
confirmado marca el pedido como pagado, le genera su código de canje y marca el
intento como aprobado. Hoy eso ya ocurre en dos transacciones y
[arc42 §6.7](../arc42/arc42.md#fallos-parciales) documenta la ventana que deja.

Con `pagos` en otro servicio y otra base, esa ventana dejaría de ser un defecto
corregible y pasaría a ser **la arquitectura**:

| Hoy | Con `pagos` extraído |
|---|---|
| Dos transacciones en la misma base; se puede cerrar con una | Dos bases distintas: **no existe** una transacción común |
| La inconsistencia se detecta con una consulta (`conciliar()`) | Haría falta una **saga con compensación**, y compensar un pago es reembolsar |
| El reintento de la pasarela cierra la ventana | Sigue cerrándola, pero ahora sobre dos almacenes que pueden divergir |
| `confirmar_pago` es una llamada en proceso que no puede fallar por red | Pasa a ser una llamada de red: nuevos modos de fallo, reintentos y backoff |

Es decir: **extraer `pagos` crearía exactamente los problemas que la semana 11
pide analizar**, y para los que hoy la respuesta honesta es «no aplican». Se
cambiaría un defecto local y medible por una clase de problema distribuido, sin
ganar nada de las seis filas de la tabla anterior.

### El costo, en lo que de verdad cuesta

| | Monolito modular (hoy) | `pagos` extraído |
|---|---|---|
| **Contenedores** | **3** de 4 permitidos | **5** de 4 — *web, api, db, pagos, pagos-db* |
| Memoria | **416 MB** de 512 *(medido)* | **~704 MB** de 512 *(estimado, ver abajo)* |
| Transacción entre contextos | Local | Saga + compensación |
| Modos de fallo nuevos | — | Red entre servicios, timeouts, reintentos, backoff |
| Despliegue | Uno | Dos, con orden entre ellos |

**La fila que decide es la primera, y conviene decir por qué no es la segunda.**

Un servicio con base propia son dos contenedores más —el proceso y su
PostgreSQL—, y eso deja **cinco donde la cuota permite cuatro**. Ese argumento
es binario: no estima nada, no depende de ninguna medición y no admite
discusión. Con la cuota del servidor del laboratorio, extraer `pagos` **no es
caro: es imposible**.

#### De dónde sale cada número de memoria, porque no son de la misma clase

El **416 es medido** y se puede comprobar: es la suma de los tres límites
declarados en [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml).

```
api 192 MB  +  db 160 MB  +  web 64 MB  =  416 de 512
```

El **704 es una estimación**, y la primera versión de este ADR lo presentaba sin
decirlo — tres cifras significativas que parecían una medición. Su composición:

| | | Por qué |
|---|---|---|
| Lo que ya hay | 416 MB | Medido |
| `pagos` | **~128 MB** | El piso no es la lógica de negocio: es el runtime —Python, uvicorn, psycopg— que `api` ya paga con 192. Un servicio que hace menos no baja de ahí por hacer menos |
| `pagos-db` | **~160 MB** | El mismo piso que la base actual, que además necesitó `max_connections=30` para caber en él |
| | **~704 MB** | |

**Los 128 MB son el número débil**: nadie ha construido ese servicio, así que es
un supuesto, no una medición. Si resultara que necesita lo mismo que `api`
—192 MB, que es lo que cuesta hoy el mismo stack— serían **768**.

Y ahí está lo que importa: **en los dos casos pasa de 512**, así que la
conclusión no depende de la precisión del estimado. Un argumento cuya validez
sobrevive al peor caso de su propia incertidumbre es más fuerte que uno con un
número bonito.

Aun así, el que se cita en una defensa debería ser el conteo de contenedores.

Y si compartiera la base de datos para ahorrarse uno, no sería una extracción:
dos servicios escribiendo en el mismo almacén tienen el acoplamiento del
monolito y los modos de fallo del sistema distribuido. Es la peor de las dos
opciones, y conviene nombrarla porque es la que se elige cuando la cuota aprieta
y la decisión ya se tomó por otros motivos.

## Decisión

**No se extrae ningún módulo.** El sistema sigue siendo un monolito modular, y
los cuatro contextos siguen comunicándose por funciones públicas de servicio.

Lo que sí se hace es **mantener la extracción barata**, que es la otra mitad de
la apuesta de ADR-0001 y lo que hace que esta decisión sea reversible:

- La regla de dependencia la verifica `test_modularidad.py` en cada push. Un
  módulo que empiece a leer el repositorio de otro rompe la construcción, y con
  ella la posibilidad de extraerlo más tarde.
- Las fronteras hablan por **lenguaje publicado** (`contracts.py`), no por
  modelos internos. Esos tipos son los que se convertirían en el contrato del
  servicio nuevo.
- El canal `pedidos-pagados` ya está declarado en
  [`asyncapi.yaml`](../api/asyncapi.yaml) con sus garantías. El día que el panel
  sea un desplegable propio, cambia el transporte y **no el contrato**.

La conciliación de [§6.7](../arc42/arc42.md#fallos-parciales) añadida esta
semana sirve a las dos posibilidades: hoy detecta una ventana local; si algún
día hay dos bases, es el esqueleto de la verificación que una saga necesitaría.

## Qué cambiaría esta decisión

Cada una es comprobable, no una intuición:

- **Que el presupuesto de memoria deje de ser 512 MB.** Es la restricción que
  hoy lo hace imposible aunque se quisiera.
- **Que `pagos` necesite escalar distinto del resto.** Se vería en
  `GET /metricas`: si el p95 de `POST /v1/pagos/intentos` se despegara del de
  `POST /v1/pedidos` bajo carga, habría un argumento medido.
- **Que aparezca un segundo consumidor del canal de eventos** que no sea este
  sistema. Hoy no hay ninguno, y hay una prueba que lo vigila
  (`test_el_evento_se_pierde_si_no_hay_nadie_escuchando`).
- **Que el equipo crezca** hasta que dos personas se estorben en el mismo
  repositorio. Con tres, no ocurre.
- **Que una integración saliente de verdad aparezca.** Hoy no existe ninguna
  (§6.7), así que todo el aparato de reintentos y backoff que justificaría un
  servicio aislado no tiene a qué aplicarse.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Estilo que esta decisión confirma | [ADR-0001](0001-estilo-arquitectonico.md) |
| Propiedad de datos entre contextos | [ADR-0002](0002-propiedad-datos-establecimiento.md) |
| Integración asíncrona y sus garantías | [ADR-0003](0003-estrategia-integracion.md) · [`asyncapi.yaml`](../api/asyncapi.yaml) |
| Presupuesto de memoria | [ADR-0008](0008-despliegue-en-el-servidor-del-laboratorio.md) · [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml) |
| Fallos parciales y la ventana de `procesar_evento` | [arc42 §6.7](../arc42/arc42.md#fallos-parciales) |
| Diseño de idempotencia | [arc42 §8.5](../arc42/arc42.md#idempotencia) |
| Regla de dependencia verificada | `backend/tests/test_modularidad.py` |
