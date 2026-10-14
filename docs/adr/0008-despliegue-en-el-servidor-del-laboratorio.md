# ADR 0008: Desplegar en el servidor del laboratorio, con la base de datos dentro del despliegue y bajo un solo origen

## Estado

Aceptada — 13/10/2026. **Reemplaza la elección de plataforma de
[ADR-0004](0004-plataforma-de-despliegue.md)**, cuya premisa dejó de ser cierta.

## Contexto

[ADR-0004](0004-plataforma-de-despliegue.md) eligió Render bajo una condición
operativa explícita —presupuesto **$0**— y aceptó un coste conocido: el plan
gratuito duerme el servicio tras 15 minutos sin tráfico y tarda en volver. Ese
coste se midió después en **42,4 segundos**
([`comparacion-despliegue.md`](../comparacion-despliegue.md) §10).

La semana 10 mostró lo que ese número significaba de verdad. Al medir
[ESC-03](../arc42/arc42.md#esc-03) por capas apareció que **el escenario no se
cumple con el servicio frío**: el umbral son 10 segundos y el arranque son 42.
No era un caso raro, era *el* caso — el patrón de tráfico documentado son dos
picos de almuerzo, así que quien abre el panel al empezar el turno es por
construcción quien paga el arranque.

La conclusión de entonces fue que la solución costaba $7/mes y que la condición
de presupuesto $0 la bloqueaba.

**Esa conclusión caducó.** El curso dispone de un servidor compartido
(`iscoutb.dev`, gestionado con Dokploy sobre una VM de Oracle Cloud) con una
dirección ya reservada para el equipo, HTTPS con certificado comodín, y
contenedores que **no duermen**. Sigue costando $0.

ADR-0004 anticipó esto en su propia sección «qué cambiaría esta decisión». Esto
es esa sección ocurriendo.

## Decisión

Tres decisiones, que se toman juntas porque dependen unas de otras.

### 1 · El sistema se despliega en el servidor del laboratorio

`https://pideutb.iscoutb.dev`, descrito por
[`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml) y dos Dockerfile
versionados.

**Lo que se gana:** desaparece el arranque en frío, y con él el incumplimiento
de ESC-03. La infraestructura como código deja de estar repartida entre
Terraform y pasos manuales en un panel; el compose describe el sistema entero.

**Lo que se pierde, y hay que decirlo:**

| | |
|---|---|
| **No hay copia de seguridad garantizada** de los volúmenes | Es el riesgo real de esta decisión. Se mitiga con la semilla, ver §2 |
| El servidor se comparte entre 23 equipos | 2 compilaciones simultáneas para todos: un despliegue puede quedar en cola |
| Cuota de **512 MB** para todo el equipo | Hoy se usan 416. El margen es deliberado, ver abajo |
| Terraform deja de gestionar la plataforma | `infra/` conserva el proyecto de Supabase y la protección de rama; el despliegue ya no |

Reparto de la cuota:

```
api    192 MB     db  160 MB     web  64 MB     →  416 de 512
```

Los 96 MB sin asignar no son desperdicio: son lo que permitiría añadir un
broker ligero (NATS con JetStream, ~64 MB) sin pedir cuota **si** la decisión de
S12 llega a justificarlo. Hoy no lo está, así que no está en el compose.

### 2 · PostgreSQL es un servicio del compose, no un servicio gestionado

La base de datos pasa de Supabase a un contenedor vecino.

**Por qué:**

- **Desaparece una clase entera de complejidad.** El plan gratuito de Supabase
  obliga al conector de sesión porque su conexión directa es solo IPv6 — un
  detalle que costó una sesión entera descubrir. Con la base en la misma red,
  el host es `db` y no hay más.
- **Lo que corre en un portátil es lo que corre en producción.** Un
  `docker compose up` levanta exactamente el mismo esquema, con los mismos
  parámetros de memoria.
- Una dependencia externa menos en el camino síncrono de cada petición.

**El riesgo, nombrado:** no hay respaldo. Un volumen que desaparece se lleva los
datos. La mitigación es que
[`002_datos_semilla.sql`](../../backend/migraciones/002_datos_semilla.sql) deja
de ser un adorno de desarrollo y pasa a ser **el procedimiento de
recuperación**, y corre sola en cada arranque limpio (ver §3). Lo que la semilla
no cubre son las cuentas del personal, que hay que volver a crear con
`scripts/crear_usuario.py`.

**Es reversible sin tocar código.** La aplicación lee `PIDEUTB_DATABASE_URL`;
apuntarla de nuevo a Supabase es cambiar una variable en el panel. Esa
reversibilidad es parte de por qué la decisión se puede tomar ahora.

### 3 · El sitio y la API comparten origen: la API se publica bajo `/api`

La alternativa evaluada era un host aparte, `api-pideutb.iscoutb.dev`.

| | Un solo origen (`/api`) | Host aparte |
|---|---|---|
| CORS | **Desaparece** | Hay que mantenerlo correcto |
| Cookies `HttpOnly` entre sitio y API | Viables | Exigen `SameSite=None` y defensa CSRF |
| Separación visual | Menor | Mayor |
| Configuración | `--root-path /api` y recorte de prefijo en el proxy | Ninguna |

**Decidió la primera fila.** Esta misma semana, una configuración de CORS
incompleta dejó el panel **roto en el navegador con 250 pruebas en verde**: el
cliente de pruebas no hace *preflight*, así que la suite no podía verlo. Una
clase de fallo que no se puede eliminar con más pruebas se elimina mejor
quitando la condición que la hace posible.

El coste es `--root-path /api`, que es una línea en el arranque.

**Y esto dispara una condición ya escrita.**
[V-12](../violaciones.md#v-12) aceptó guardar el token en `sessionStorage`
—expuesto a XSS— porque la cookie `HttpOnly` habría exigido `SameSite=None`,
CORS con credenciales y protección CSRF. Entre las tres condiciones que
invalidarían esa aceptación está, literalmente: *«el sitio y la API pasan a
compartir origen»*.

Acaba de pasar. **V-12 queda abierta para reconsiderar en S13**, no cerrada ni
silenciada: cambiar el mecanismo de sesión es una decisión de seguridad propia y
no un efecto colateral de una migración de despliegue.

## Consecuencias

### Las migraciones pasan a correr al arrancar la API

Esto **revierte** lo que [ADR-0007](0007-autenticacion-del-panel.md) decidió
hace un día, y conviene decirlo sin rodeos.

ADR-0007 argumentó que un proceso web que modifica el esquema al arrancar lo
hace en cada instancia a la vez y cuando nadie está mirando, y que por eso
`migrar.py` debía ser un paso que alguien ejecuta. **Ese argumento valía para el
despliegue anterior.** Aquí hay dos hechos nuevos:

1. **Un solo contenedor de API, sin autoescalado.** La carrera entre instancias
   que motivaba la regla no existe.
2. **Sin copia de seguridad.** Con las migraciones a mano, un volumen perdido
   deja la API arrancando contra un esquema inexistente y fallando en cada
   petición hasta que alguien lo note. Corriéndolas al arrancar, un despliegue
   limpio siempre deja la base utilizable.

Si una migración falla, el contenedor no arranca: el despliegue queda en rojo en
vez de servir una API contra un esquema a medio aplicar.

### ESC-03 pasa a cumplirse

Queda por medir en el entorno nuevo —es trabajo de S14—, pero el término que lo
incumplía desaparece por construcción.

### Lo que queda pendiente de reconciliar

La documentación de arquitectura todavía describe el despliegue anterior:
[`arc42 §7`](../arc42/arc42.md), el [nivel 2 del C4](../c4/nivel2-contenedores.md)
y [`comparacion-despliegue.md`](../comparacion-despliegue.md). **Se reconcilian
como paso siguiente**, antes de dar la migración por terminada: un diagrama que
describe un despliegue que ya no existe es el mismo defecto que esta semana
encontramos dos veces.

## Qué cambiaría esta decisión

- **Que termine el curso.** El servidor es del laboratorio; cuando deje de estar
  disponible, esta decisión se revisa entera y Render vuelve a ser la referencia.
- **Que el sistema necesite datos que no se puedan perder.** Hoy todo lo que hay
  es recreable desde la semilla. El día que haya pedidos reales con dinero real,
  la ausencia de respaldo deja de ser un riesgo aceptable y la base vuelve a un
  servicio gestionado.
- **Que haga falta más de un contenedor de API.** Ahí vuelve el argumento de
  ADR-0007 y las migraciones salen del arranque.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Decisión que reemplaza | [ADR-0004](0004-plataforma-de-despliegue.md) |
| Decisión que revierte en parte | [ADR-0007](0007-autenticacion-del-panel.md) — migraciones |
| Escenario que desbloquea | [ESC-03](../arc42/arc42.md#esc-03) |
| Violación que reabre | [V-12](../violaciones.md#v-12) |
| Medición que motivó el cambio | [`evidencia-s9.md` §1.3](../evidencia-s9.md) |
| Infraestructura | [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml), `backend/Dockerfile`, `sitio/Dockerfile` |
| Procedimiento de recuperación | `backend/migraciones/002_datos_semilla.sql` + `scripts/crear_usuario.py` |
