# ADR 0003: Confirmar el pago de forma asíncrona por webhook y mantener síncrono el resto de la API

## Estado

Aceptada — 20/09/2026

## Contexto

Hasta esta entrega, todas las interacciones de PideUTB eran síncronas y ninguna
salía del proceso: el frontend llama a la API y la API llama a sus propios
módulos. El contexto Pagos cambia eso, porque introduce el primer interlocutor
que **el equipo no controla**: la pasarela Wompi en ambiente Sandbox.

Con un interlocutor externo aparece una pregunta que antes no existía: *¿qué le
pasa al usuario si el otro lado tarda, falla o no responde nunca?* Mientras
todas las llamadas fueran internas, la respuesta era «nada, porque si el proceso
está vivo todos los módulos lo están». Deja de serlo en cuanto una operación
depende de un tercero.

### El escenario que fuerza la decisión

<a id="escenario-motivador"></a>

**[ESC-05 — Error en el proceso de pago](../arc42/arc42.md#esc-05)**, cuya medida
de respuesta es: *mensaje claro en menos de 3 segundos y el pedido conservado en
el 100 % de los casos*.

Ese umbral es el que descarta las alternativas. «Menos de 3 segundos» es un
compromiso que solo se puede cumplir si el tiempo de respuesta **no depende de
cuánto tarde la pasarela**, porque la pasarela no se ha comprometido a nada con
nosotros. Y «pedido conservado en el 100 % de los casos» obliga a que el pedido
exista y esté persistido **antes** de que empiece el cobro, no como resultado de
que el cobro salga bien.

También queda afectado [ESC-04](../arc42/arc42.md#esc-04), que exige rechazar el
100 % de las reutilizaciones del código de canje: el código solo puede generarse
una vez por pedido, y la confirmación del pago puede llegar repetida.

### Acoplamiento temporal: qué se está decidiendo en realidad

El acoplamiento temporal es el grado en que dos partes tienen que estar
disponibles **al mismo tiempo** para que una operación tenga éxito. No es lo
mismo que el rendimiento: una llamada síncrona muy rápida sigue teniendo
acoplamiento temporal máximo, porque si el otro lado está caído, la operación
falla, por rápido que fuera cuando funcionaba.

La medida práctica es la pregunta de la sesión: **si apago el otro servicio,
¿qué le pasa al usuario?**

| Integración | Si el otro lado está caído | Acoplamiento temporal |
|---|---|---|
| Frontend → API | El usuario no puede hacer nada | Máximo — y es aceptable: si la API está caída no hay producto |
| API → Pasarela, al **iniciar** el cobro | El usuario ve un error inmediato y puede reintentar | Máximo — aceptable: el usuario está delante y puede reaccionar |
| Pasarela → API, al **confirmar** el cobro | *(depende de esta decisión)* | Es lo que se decide aquí |
| API → panel del establecimiento | *(depende de esta decisión)* | Es lo que se decide aquí |

## Alternativas consideradas

### 1. Integración síncrona completa — **descartada**

La API llama a la pasarela dentro del `POST` de pago y **espera** el resultado
del cobro antes de responder. El frontend recibe en una sola llamada si el pago
se aprobó o no.

Es la alternativa más simple de programar y la que produce la mejor experiencia
cuando todo funciona: una llamada, un resultado, sin pantallas de espera ni
consultas posteriores. Por eso se consideró en serio y no como hombre de paja.

**Por qué se descarta:**

- **Incumple el umbral de ESC-05.** El tiempo de respuesta pasa a ser el nuestro
  más el de la pasarela. Los 3 segundos dejan de estar bajo nuestro control, y
  un compromiso que depende de un tercero que no lo ha firmado no es un
  compromiso.
- **Incumple «pedido conservado en el 100 % de los casos».** Un `timeout`
  durante la espera deja el peor estado posible: no sabemos si el cobro ocurrió.
  Si asumimos que no, podemos estar regalando comida ya pagada; si asumimos que
  sí, podemos entregar sin cobrar. Cualquiera de las dos suposiciones es peor
  que no haber preguntado.
- **La pasarela no lo permite de todas formas.** Los métodos que ofrece el
  sistema —PSE y Nequi— redirigen al usuario a un flujo externo que puede durar
  minutos. No existe una respuesta inmediata que esperar: esperar sería esperar
  a que una persona termine de teclear en otra pantalla.

El tercer punto es el decisivo, y conviene decirlo sin adornos: **para la
confirmación del pago, la asincronía no es una elección de diseño sino una
restricción del entorno.** Lo que sí se elige es cómo se tolera.

### 2. Integración asíncrona completa — **descartada**

Todo pasa por mensajes, incluida la creación del pedido: el `POST /v1/pedidos`
encola una petición, responde `202` y el frontend consulta después si su pedido
llegó a existir.

**Por qué se descarta:**

- **Perjudica a ESC-01** (primer pedido en menos de 3 minutos, sin errores de
  navegación). Un usuario que crea un pedido y no recibe confirmación inmediata
  de que existe tiende a repetir la acción, con lo que se generan pedidos
  duplicados por un problema que solo era de interfaz.
- **Paga un coste sin comprar nada.** El desacoplamiento temporal sirve para
  protegerse de un tercero no disponible. En la creación del pedido no hay
  tercero: el ítem lo valida `menu` y el establecimiento lo valida `usuarios`,
  ambos dentro del mismo proceso. Se estaría añadiendo complejidad —cola,
  reintentos, consultas de estado, diseño de la espera— para desacoplarse de uno
  mismo.
- **Es el error frecuente que señala el material de la semana:** elegir
  asíncrono «porque escala» sin aceptar la consecuencia de que el usuario deja
  de tener respuesta inmediata y hay que diseñar cómo se entera después.

### 3. Integración híbrida por naturaleza de la operación — **elegida**

Cada interacción se decide por separado, según si hay alguien esperando el
resultado y si el interlocutor está bajo nuestro control.

## Decisión

**Se adopta la alternativa 3.** El criterio, aplicable a cualquier integración
futura, es:

> Síncrono cuando hay un usuario esperando el resultado **y** el interlocutor
> está bajo nuestro control. Asíncrono cuando el resultado no existe todavía en
> el momento de la petición, o cuando el interlocutor puede no estar disponible
> sin que eso deba impedir la operación.

Aplicado a las cuatro interacciones del sistema:

| Interacción | Modo | Protocolo y formato | Por qué |
|---|---|---|---|
| Frontend → API | **Síncrono** | HTTPS · JSON (REST) | Hay un usuario esperando y la API es nuestra. |
| Entre contextos, dentro de la API | **Síncrono** | Llamada en proceso · tipos de `contracts` | Mismo proceso: el acoplamiento temporal es inevitable y gratuito. |
| API → Pasarela (**iniciar** cobro) | **Síncrono** | HTTPS · JSON | El usuario espera saber a dónde ir. Si falla, falla delante de él. |
| Pasarela → API (**confirmar** cobro) | **Asíncrono** | HTTPS · JSON (webhook firmado) | El resultado no existe cuando se pide. La pasarela avisa cuando puede. |
| API → panel del establecimiento | **Asíncrono** | Evento `pedido.pagado` · JSON | El cobro no puede depender de que el panel esté abierto. |

El contrato de las dos primeras columnas está en
[`docs/api/openapi.yaml`](../api/openapi.yaml); el de las dos últimas, en
[`docs/api/asyncapi.yaml`](../api/asyncapi.yaml).

### Lo que la decisión obliga a construir

Elegir asíncrono no es elegir «más fácil»: es aceptar tres obligaciones que la
alternativa síncrona no tenía. Están implementadas, no planificadas.

| Obligación | Por qué es obligatoria | Dónde está |
|---|---|---|
| **Idempotencia** | La pasarela entrega al-menos-una-vez y reintenta sin `2xx`. Sin ella, un reintento genera un segundo código de canje y ESC-04 deja de cumplirse. | `pedidos.service.confirmar_pago` · `test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo` |
| **Diseño de la espera** | El usuario vuelve de la pasarela y necesita saber en qué quedó todo. | `GET /v1/pedidos/{pedido_id}` · `test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable` |
| **Autenticación del canal de entrada** | Un webhook es un endpoint público capaz de marcar pedidos como pagados. En la integración síncrona el interlocutor era nuestro propio frontend; aquí es Internet. | Firma HMAC en `pagos.service.firma_valida` · `test_un_evento_sin_firma_valida_se_rechaza` |

## Consecuencias

### Modos de fallo, y qué ve el usuario en cada uno

Es la parte que la alternativa síncrona no podía ofrecer: cada fallo tiene una
respuesta decidida de antemano en lugar de un estado desconocido.

| Fallo | Antes (síncrono) | Ahora | Qué ve el usuario |
|---|---|---|---|
| La pasarela no responde al iniciar | Error tras el `timeout` | Error inmediato | Mensaje claro; el pedido sigue ahí y puede reintentar |
| La pasarela tarda minutos en confirmar | La petición muere por `timeout`, estado desconocido | No afecta: nadie está esperando | «Esperando confirmación»; el estado se consulta |
| **El evento nunca llega** | Pedido en estado desconocido | Pedido en `pendiente_pago` | Estado real y consultable; se puede reintentar el cobro |
| El evento llega repetido | No aplicaba | Se detecta y se ignora | Nada: el código de canje no cambia |
| Los eventos llegan desordenados | No aplicaba | Se resuelve por estado, no por marca de tiempo | Nada |
| El panel del establecimiento está caído | Habría tumbado el cobro | El cobro se completa igual | Su código de canje, con normalidad |

El tercero es el importante: **un evento que no llega deja el pedido en
`pendiente_pago`, que es un estado honesto.** No se afirma que esté pagado ni
que haya fallado. Es la degradación que se acepta a cambio del desacoplamiento,
y es preferible a un estado desconocido porque se puede consultar y se puede
reintentar.

### Lo que empeora

Se declaran porque la decisión no es gratis:

- **El usuario deja de tener una respuesta inmediata al pagar.** Es el coste
  directo del desacoplamiento y hay que diseñar cómo se entera después, que es
  lo que hace `GET /v1/pedidos/{pedido_id}`.
- **Hay más piezas.** Un webhook, una firma, un registro de idempotencia y un
  canal de eventos que no existirían con la alternativa 1.
- **Depurar es más difícil.** Un fallo ya no está en una sola traza: hay que
  correlacionar la petición de inicio con el evento posterior, y por eso la
  `referencia_pago` la genera PideUTB y no la pasarela.
- **Existe una ventana de inconsistencia.** Entre que la pasarela aprueba y
  llega el evento, el pedido figura como no pagado aunque el dinero ya se movió.
  Es visible para el usuario y se acepta; lo que no se acepta es que sea
  invisible, de ahí que el estado se pueda consultar.

### Lo que no cambia

El sistema **sigue siendo un monolito modular**. Esta decisión no introduce
microservicios ni contradice [ADR-0001](0001-estilo-arquitectonico.md): el canal
`pedidos.pagados` se entrega hoy en proceso. Lo que se desacopla no es el
despliegue sino **el momento**, que es de lo que trata el acoplamiento temporal.

El día que el panel del establecimiento sea un desplegable aparte, cambia el
transporte de `app/eventos.py` y no cambian ni los mensajes ni sus garantías,
porque están en el contrato y no en la implementación. Escribir ese contrato
ahora, con un transporte trivial, es precisamente lo que permite que ese cambio
sea sustituir un archivo en vez de renegociar una integración.

## Trazabilidad

| Elemento | Referencia |
|---|---|
| **Escenario que lo motiva** | [ESC-05](../arc42/arc42.md#esc-05) — mensaje en < 3 s y pedido conservado en el 100 % de los casos. También [ESC-04](../arc42/arc42.md#esc-04) — rechazo del 100 % de reutilizaciones del código |
| **Vista de ejecución** | [arc42 §6.3](../arc42/arc42.md#runtime-pagar-pedido) — flujo de pago; [§6.5](../arc42/arc42.md#runtime-modos-de-fallo) — modos de fallo |
| **Diagrama** | [C4 nivel 2](../c4/nivel2-contenedores.md), donde cada flecha lleva su protocolo, formato y modo |
| **Contrato síncrono** | [`docs/api/openapi.yaml`](../api/openapi.yaml) — `POST /v1/pagos/intentos`, `GET /v1/pedidos/{pedido_id}` |
| **Contrato asíncrono** | [`docs/api/asyncapi.yaml`](../api/asyncapi.yaml) — canales `eventos-de-pago` y `pedidos-pagados` |
| **Código — inicio síncrono** | `backend/app/pagos/service.py::iniciar_intento` |
| **Código — entrada asíncrona** | `backend/app/pagos/router.py::recibir_evento`, `pagos/service.py::procesar_evento` |
| **Código — publicación de eventos** | `backend/app/eventos.py`, `pedidos/service.py::confirmar_pago` |
| **Pruebas — idempotencia** | `test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo`, `::test_el_codigo_de_canje_no_cambia_entre_reintentos` |
| **Pruebas — modo de fallo tolerado** | `test_pagos.py::test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable`, `::test_un_pago_rechazado_conserva_el_pedido` |
| **Pruebas — desacoplamiento real** | `test_pagos.py::test_un_suscriptor_que_falla_no_tumba_el_cobro` |
| **Pruebas — seguridad del canal** | `test_pagos.py::test_un_evento_sin_firma_valida_se_rechaza` |
| **Decisiones relacionadas** | [ADR-0001](0001-estilo-arquitectonico.md) — el monolito modular no se abandona; [ADR-0002](0002-propiedad-datos-establecimiento.md) — Pagos solicita la transición, Pedidos la ejecuta por ser su único escritor |
