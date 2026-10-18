# ADR 0010: Notificar al panel por sondeo, y conservar el canal de eventos como costura sin suscriptores

## Estado

Aceptada — 18/10/2026

## Contexto

[ADR-0003](0003-estrategia-integracion.md) decidió, el 20/09/2026, que la
notificación «API → panel del establecimiento» fuera **asíncrona**, por un
motivo que sigue siendo bueno: *el cobro no puede depender de que el panel esté
abierto*. Declaró el canal `pideutb.pedidos.pagados` en
[`asyncapi.yaml`](../api/asyncapi.yaml) y lo implementó con un bus en proceso.

Esta decisión no lo revisa por gusto. Lo revisa porque ahora hay algo que
entonces no había: **el sistema lleva desplegado y funcionando, y se puede
mirar qué hace de verdad.**

Y lo que hace es esto:

| Lo que el contrato describe | Lo que corre |
|---|---|
| Un canal que publica `pedido.pagado` a quien se suscriba | `publicar()` se invoca y **no hay ningún suscriptor** |
| El panel se enteraría por ese evento | El panel **pregunta cada 8 segundos** por `GET /v1/pedidos` |

No es un defecto de implementación: es una pieza a medias que nadie declaró como
tal. `app/eventos.py` funciona, está probado y entrega a quien escuche; lo que
no hay es quien escuche. `publicar()` es hoy, literalmente, una operación nula
que devuelve `0`.

Así que la pregunta de esta semana no es «¿asíncrono o síncrono?» —eso ya se
decidió y con razón— sino la que la evidencia obliga a hacer:

> El mecanismo que de verdad notifica al panel es un **sondeo síncrono** que
> nadie documentó como decisión. ¿Se queda, se sustituye por el empuje que el
> contrato promete, o se borra el canal que no se usa?

### El dato que convierte la pregunta en algo medible

[ESC-03](../arc42/arc42.md#esc-03) concede **10 segundos** desde que un pedido se
paga hasta que el encargado lo ha visualizado y cambiado de estado, *sin
recargar la página*.

El sondeo está fijado en **8000 ms** (`sitio/panel.js`). Eso deja **2 segundos**
para que una persona vea el pedido nuevo y pulse.

**El margen de ESC-03 está agotado**, y no lo estaba escrito en ninguna parte. La
constante que lo consume no mencionaba el umbral que sostiene: subirla a 12 000
«para aliviar carga» habría sido un cambio de una línea, sin error visible y sin
nada que se quejara, que incumple un escenario de calidad. Ahora se queja
(`test_escenarios_de_calidad.py`).

## Alternativas consideradas

### A. Sondeo síncrono cada 8 s — **elegida**, y es lo que ya corría

El panel pregunta por su cola en un intervalo fijo.

**Lo que cuesta, medido** contra el despliegue el 18/10/2026:

| | |
|---|---|
| Tiempo de servidor de `GET /v1/pedidos` | **2,79 ms** de p50 *(n=3; muestra corta porque el endpoint pide sesión)* |
| Peticiones por panel abierto | 7,5/min · **3 600 por turno de 8 h** |
| Tiempo de servidor acumulado por turno | **~10 segundos** |

Diez segundos de CPU por turno y por panel. Con un punto de venta en el sistema,
el costo es indistinguible de cero.

**Lo que cuesta de verdad no es la carga: es el margen.** Los 8 segundos se comen
el 80 % de ESC-03, y ese es el único argumento serio en contra de esta
alternativa.

Hay además una mitigación ya implementada que conviene no perder de vista: el
panel **deja de sondear cuando la pestaña está oculta**
(`visibilitychange` en `panel.js`), así que las 3 600 peticiones son el peor
caso de un panel mirado todo el turno, no el caso normal.

### B. Empuje de verdad por el canal, con SSE o WebSocket — **descartada**

Es la alternativa que el contrato parece prometer, y la que más mejora el número:
la frescura pasaría de 8 segundos a inmediata, devolviendo a ESC-03 los 8
segundos de margen que hoy no tiene.

Se descarta por una razón técnica concreta, no por esfuerzo:

**El bus es en proceso, y un bus en proceso no puede servir empuje
correctamente.** Mientras haya un solo proceso funciona. En cuanto haya dos, un
pago que procese el proceso A **no llega** a un panel conectado al proceso B, y
el fallo es silencioso: el panel no se enteraría de que no se está enterando. Un
empuje correcto necesita que el evento salga del proceso, es decir **un broker
desplegado**.

Y ahí la decisión ya está tomada y con aritmética:
[ADR-0009](0009-no-extraer-un-servicio.md) dejó escrito que el servidor del
laboratorio concede **4 contenedores y 512 MB**, de los que hoy se usan 3 y 416.
Un broker entra —son los 96 MB sin asignar— pero entonces se gasta el último
contenedor disponible en mejorar una frescura que ESC-03 no exige.

A eso se suman dos costos que no son de arquitectura pero existen: Cloudflare
está delante y cierra conexiones inactivas, así que SSE necesitaría latidos de
mantenimiento ([arc42 §7.2](../arc42/arc42.md#despliegue-topologia)), y cada
conexión abierta ocupa un hueco en un contenedor con **0,5 CPU**.

**Resumen honesto:** B no es un cambio de 50 líneas. Es SSE, más un broker, más
el último contenedor del presupuesto, para ganar 8 segundos que el escenario no
pide.

### C. Borrar el canal de eventos — **descartada**

Es la alternativa que exige más honestidad, porque tiene un argumento bueno:
**un mecanismo sin usuarios es código que miente.** Alguien que lea
`publicar(CANAL_PEDIDO_PAGADO, ...)` en `confirmar_pago` asume razonablemente
que algo pasa después. No pasa nada. Son ~60 líneas y una trampa conceptual.

Se descarta porque lo que se perdería es justo lo que hace reversibles otras dos
decisiones:

- **El contrato.** `asyncapi.yaml` declara el mensaje y sus garantías. Borrarlo
  y reescribirlo luego significa volver a decidir lo que ya está decidido.
- **La costura.** [ADR-0009](0009-no-extraer-un-servicio.md) apoya su «mantener
  la extracción barata» en que este canal existe: *el día que el panel sea un
  desplegable propio, cambia el transporte y no el contrato*. Sin canal, esa
  frase deja de ser cierta y la decisión de no extraer pierde una de sus patas.
- **El sitio donde vive esta discusión.** Un `publicar()` sin suscriptores es
  visible y da que pensar. Su ausencia no da que pensar nada.

Lo que sí se acepta de esta alternativa es su crítica, y se responde: la trampa
se desactiva **nombrándola** —aquí y en
[arc42 §8.6](../arc42/arc42.md#consistencia)— y con una prueba que falla el día
que deje de ser verdad (`test_el_evento_se_pierde_si_no_hay_nadie_escuchando`).
Esa prueba es lo que impide que esta decisión se herede sin revisarla: el día que
aparezca un suscriptor, falla y obliga a volver aquí.

## Decisión

**Se conservan las dos piezas, y se declara para qué sirve cada una**, que es lo
que faltaba:

| Pieza | Qué es hoy |
|---|---|
| Sondeo de 8 s del panel | **El mecanismo de notificación real.** Pasa a ser una decisión con umbral, no una constante |
| Canal `pideutb.pedidos.pagados` | **Una costura con contrato y sin suscriptores.** No notifica a nadie, y no pretende hacerlo |

La relación entre las dos se escribe aquí porque es lo que no estaba en ningún
sitio: **el sondeo es la implementación actual de la notificación que el canal
describe.** No son dos mecanismos que compiten; son el mismo requisito resuelto
de la forma que el presupuesto permite.

Y se añade lo que faltaba para que la decisión no se degrade sola:

- `test_escenarios_de_calidad.py` ata `MS_ENTRE_REFRESCOS` al presupuesto de
  ESC-03. Subirlo rompe la construcción.
- El margen nulo queda como riesgo en [arc42 §11](../arc42/arc42.md#riesgos),
  con su número, en vez de como una coincidencia afortunada.

### Lo que esta decisión no cambia

ADR-0003 sigue vigente en lo que decidió: la confirmación del pago llega por
webhook asíncrono, y el cobro no depende de que el panel esté abierto. **Eso es
cierto hoy por el sondeo igual que lo sería por el empuje**: un panel cerrado no
impide que `confirmar_pago` termine. El desacoplamiento temporal que ADR-0003
buscaba está conseguido; lo que no está conseguido es el empuje, y nunca fue el
objetivo.

## Qué cambiaría esta decisión

Cada una es comprobable:

- **Que aparezca un segundo suscriptor del canal.** Entonces el bus en proceso
  pasa a ser una limitación real y hay que decidir transporte.
  Vigilado por `test_el_evento_se_pierde_si_no_hay_nadie_escuchando`.
- **Que haya más de un proceso de API.** Es la condición que rompe el bus en
  proceso, y rompe también `GET /metricas`
  ([arc42 §8.6](../arc42/arc42.md#consistencia)). Hoy hay uno.
- **Que ESC-03 se endurezca o se mida y falle.** El margen es cero: cualquier
  recorte del umbral obliga a bajar el intervalo, y bajarlo mucho obliga a
  mirar la alternativa B en serio.
- **Que el presupuesto deje de ser 4 contenedores y 512 MB.** Es lo que hoy hace
  que un broker cueste el último hueco disponible.
- **Que haya más de un establecimiento activo.** Las 3 600 peticiones por turno
  se multiplican por panel abierto. Con uno es ruido; con treinta, hay que
  volver a medir antes de afirmar que es ruido.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Decisión de integración que esta revisa | [ADR-0003](0003-estrategia-integracion.md) |
| Aritmética de contenedores y memoria | [ADR-0009](0009-no-extraer-un-servicio.md) · [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml) |
| Contrato del canal | [`docs/api/asyncapi.yaml`](../api/asyncapi.yaml) |
| Bus en proceso | `backend/app/eventos.py` |
| Publicación del evento | `backend/app/pedidos/service.py::confirmar_pago` |
| Escenario y su umbral | [arc42 §10.4 — ESC-03](../arc42/arc42.md#esc-03) |
| Consistencia y caché | [arc42 §8.6](../arc42/arc42.md#consistencia) |
| El canal sin suscriptores, probado | `backend/tests/test_fallos_parciales.py` |
| Umbral de ESC-03, protegido | `backend/tests/test_escenarios_de_calidad.py` |
