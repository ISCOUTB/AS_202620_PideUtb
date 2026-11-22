# ADR 0013: Pedir siempre el correo, para que el código de recogida tenga una copia fuera de la pantalla

## Estado

Aceptada — 21/11/2026. **Modifica en parte
[ADR-0012](0012-avisos-y-comprobante-prescindibles.md)**: el correo deja de ser
opcional. El resto de aquella decisión —el comprobante como salida prescindible, sin
cola ni reintentos— sigue en pie, y más abajo está por qué.

## Contexto

Hasta hoy el correo era opcional: «pedir sin dejar ningún dato sigue siendo pedir»
(ADR-0012). El código de recogida vivía solo en la pantalla de quien pagó, y en el
almacenamiento de su navegador para sobrevivir a una recarga.

Para no perderlo, «Hacer otro pedido» con un código vivo abría una advertencia, y
había que confirmar «Ya lo anoté»: al empezar otro pedido el código desaparecía del
teléfono y no quedaba dónde buscarlo.

Había además un defecto que nadie había documentado. El seguimiento del pedido
consulta su estado cada cinco segundos, y en cada vuelta **volvía a llevar a la
pantalla del código y vaciaba el carrito**. Quien tocaba «Carta» después de pagar era
devuelto al código antes de terminar de elegir, con el carrito en cero. En la
práctica, la única forma de pedir otra cosa era confirmar «Ya lo anoté» y tirar el
código.

El cliente pidió tres cosas:

1. Que el correo sea obligatorio, para que quien compra tenga siempre el respaldo de
   su compra y su código de recogida.
2. Que, con eso, ya no haya que confirmar que se anotó el código, y se pueda volver a
   la carta con normalidad.
3. Que debajo del código salga un aviso: el código y el comprobante llegan al correo,
   y conviene revisar el spam.

El envío del comprobante se comprobó en producción el 21/11/2026, con una cuenta de
Gmail y una contraseña de aplicación.

## Decisión

### 1. El correo es obligatorio al crear el pedido, en la API y en la página

- `CrearPedidoRequest.correo_cliente` deja de admitir `null` y pasa a `required`. Sin
  él, `crearPedido` responde `422`. Es la regla I-3 de la
  [política de versionado](../api/politica-versionado.md), así que el contrato sube a
  **5.0.0**. La ruta sigue siendo `/v1`, por el mismo motivo que en la 3.0.0: el único
  consumidor declarado es el sitio de este repositorio, que se despliega a la vez.
- **Se exige en la API y no solo en el formulario.** Una regla que solo vive en la
  pantalla no es una regla: quien llame a la API directamente se la salta, y el
  contrato diría que el correo es opcional cuando el negocio dice lo contrario.
- `pedidos.service.crear_pedido` sigue admitiendo `None`. La regla vive en la
  frontera HTTP, y los pedidos anteriores a la 5.0.0 existen sin correo. El
  comprobante los sigue tolerando: confirmar uno de ellos no manda nada y no rompe
  nada.
- El nombre sigue siendo opcional.

### 2. «Hacer otro pedido» ya no pide confirmación

Lleva a la carta con el carrito vacío.

- **Un pedido con código vivo se conserva.** Sigue en «Mi código», y se sigue su
  estado, hasta que se crea el siguiente pedido.
- **Uno sin código vivo se suelta, como antes.** Es el caso de un pedido sin pagar,
  cancelado o ya entregado. Uno sin pagar no puede quedarse: «Pagar» reabre el cobro
  del pedido pendiente en vez de crear otro, así que cobraría aquel con el carrito
  nuevo.

### 3. El seguimiento no se adueña de la pantalla

Solo lleva a la pantalla del código en dos casos: cuando el pago acaba de
confirmarse, que es cuando aparece el código, o cuando la persona ya lo está
mirando. En la carta, el seguimiento continúa y el teléfono vibra cuando el pedido
esté listo, pero nadie es arrastrado de vuelta.

El carrito se vacía una sola vez, al pagarse el pedido, y no en cada consulta.

Una respuesta que llega tarde, de un pedido que ya no es el actual, se descarta. Sin
eso, el pedido anterior pisaría al nuevo.

### 4. Debajo del código, el aviso del correo

Es un recuadro ámbar, «Revisa tu correo», con la dirección que se escribió al pedir y
la mención del spam. Ocupa el lugar de la advertencia que se quitó.

La dirección se enseña porque un error de tecleo se descubre ahí o no se descubre.
Vive solo en la memoria de la pestaña: al retomar un pedido guardado, el aviso dice
«tu correo».

**El aviso no afirma que el correo haya llegado.** El correo sale aparte y sin
reintentos, y la página no se entera de si salió.

## Por qué esto no exige una cola

ADR-0012 dejó escrito qué la cambiaría: «Que el comprobante pase a ser obligatorio,
por ejemplo por ser una factura electrónica de verdad. Entonces no se puede perder, y
hace falta una cola y un proveedor autorizado por la DIAN».

Lo que pasa a ser obligatorio es **el campo**, no la entrega. El comprobante sigue sin
ser un documento fiscal, y el código sigue sin depender solo del correo:

- **Mientras el pedido es el actual**, el código está en la pantalla y en el navegador,
  y sobrevive a una recarga.
- **Después de hacer otro pedido**, sigue en «Mi código» hasta que se crea el
  siguiente.
- **Si se pierden la pantalla y el correo**, queda el mostrador, como ya decía la
  advertencia que se quitó. El pedido está en su cola con su número y lo que lleva, y
  el número también viene en el asunto del correo.

Una cola con reintentos añadiría una tabla y un proceso que la vacíe para proteger un
dato que no depende solo de ella. El coste de no tenerla está en las consecuencias.

## Alternativas consideradas

### Exigirlo solo en el formulario

Se ahorraba el salto de MAYOR. Se descartó porque la regla quedaría a merced de quien
llame a la API, y porque aquí el salto es barato: un solo consumidor, desplegado en el
mismo commit.

### Mantener la confirmación «Ya lo anoté» además del correo

El cliente pidió quitarla. Además, una confirmación protege menos cuando el dato que
cuida ya tiene copia, y una que aparece en cada pedido se aprende a despachar sin
leerla, como ya advertía el comentario que la introdujo.

### Una cola con reintentos para el correo

Se descartó, por lo explicado arriba. Pasaría a hacer falta si el correo fuera la
única copia del código.

### Verificar el buzón antes de pagar

Por ejemplo, mandando un código de confirmación. Se descartó porque añade un paso y
una espera a un recorrido que tiene que caber en un minuto. Enseñar la dirección
debajo del código descubre el error de tecleo justo cuando importa.

### Guardar la dirección en el navegador para enseñarla tras recargar

Se descartó: sería un dato personal en un teléfono que puede ser prestado, y lo que se
guarda hoy son datos del pedido, no de la persona.

## Consecuencias

**Positivas.**

- Todo pedido nuevo tiene una copia del código y del comprobante fuera de la pantalla.
- Se puede volver a la carta y pedir otra cosa sin perder el código.
- Se corrigió el arrastre a la pantalla del código y el carrito que se vaciaba solo,
  que existían antes de este cambio. Cada uno tiene su prueba en
  `e2e/flujo-completo.spec.js`, y las dos se comprobaron fallando con el defecto
  puesto.

**Negativas y costes aceptados.**

- **El contrato 5.0.0 es incompatible.** Crear un pedido sin correo responde `422`.
  Los guiones de medición mandan una dirección de `example.com`, un dominio reservado
  que no recibe correo. Con el comprobante encendido, cada pedido pagado de una
  medición gasta un envío de la cuenta, y el rechazo vuelve a su buzón.
- **`pedidos` guarda un dato personal en cada pedido nuevo**, ya no solo en el de quien
  quisiera dejarlo. La retención sigue sin definirse ([arc42 §8.8](../arc42/arc42.md)),
  y ahora pesa más.
- **Un correo puede no llegar sin que el cliente lo sepa.** Por eso el aviso dice
  «revisa», y no «enviado». Si falla y después se hace otro pedido, el código anterior
  solo queda en el mostrador.
- **El aviso habla del correo aunque el despliegue no tenga servidor de correo**, como
  en local o en las pruebas. El sitio no sabe si `PIDEUTB_SMTP_HOST` está puesto.
- **Pedir pide un dato más.** Hay que escribir una dirección antes de pagar.

## Qué cambiaría esta decisión

- **Que el correo pase a ser la única copia del código.** Por ejemplo, si el mostrador
  dejara de tener los pedidos en su cola. Entonces sí harían falta cola y reintentos.
- **Que haya cuentas de cliente.** El código se recuperaría desde la cuenta, y el
  correo podría volver a ser opcional.
- **Que aparezca un consumidor externo de la API.** El siguiente cambio incompatible ya
  no podría quedarse en `/v1` (política de versionado, §5).

## Trazabilidad

| Elemento | Dónde |
|---|---|
| La regla en la API | `backend/app/pedidos/esquemas_api.py` (`CrearPedidoRequest`) |
| El contrato | [`openapi.yaml`](../api/openapi.yaml) 5.0.0 · [`historial/openapi-5.0.0.yaml`](../api/historial/openapi-5.0.0.yaml) · [`consumidor-web.yaml`](../../contracts/consumidor-web.yaml) |
| El formulario y el aviso | `sitio/index.html` · `sitio/app.js` (`dibujarAvisoDelCorreo`, `hacerOtroPedido`, `soltarElPedidoAnterior`) · `sitio/estilos.css` (`.aviso-correo`) |
| Las pruebas | `backend/tests/test_comprobante.py` (`test_sin_correo_no_se_puede_pedir`) · `e2e/flujo-completo.spec.js` |
| El diseño del aviso | [Sistema de diseño](../sistema-de-diseno.md) |
| La decisión que esto modifica | [ADR-0012](0012-avisos-y-comprobante-prescindibles.md) |
