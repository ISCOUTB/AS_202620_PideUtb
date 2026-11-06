# ADR 0012: Avisar al cliente y mandarle el comprobante como salidas prescindibles, sin cola ni reintentos

## Estado

Aceptada — 04/11/2026

## Contexto

El cliente pidió dos cosas que cambian la forma del sistema, aunque se vean como
detalles de la interfaz:

- **Un aviso en el teléfono** cuando el mostrador marca el pedido como listo.
- **Un comprobante por correo** cuando se confirma el pago.

Tres afirmaciones de este repositorio dejaban de ser ciertas con ellas, y cada una
estaba escrita para obligar a parar a pensar:

1. [ADR-0009](0009-no-extraer-un-servicio.md) dice que una integración saliente de
   verdad es una de las cosas que cambiarían la decisión de no extraer servicios.
   Estas son las dos primeras.
2. `test_el_evento_se_pierde_si_no_hay_nadie_escuchando` exigía cero suscriptores
   en `pedidos-pagados`, y avisaba de que el día que apareciera uno había que
   decidir si hacía falta un *outbox*.
3. [arc42 §8.8](../arc42/arc42.md) decía que `pedidos` no guarda nada de una
   persona, y lo presentaba como una propiedad de la arquitectura.

## Decisión

**Las dos salidas son prescindibles, y se construyen como tales.**

El pedido no depende de ninguna: se publica un hecho en el bus en proceso
(`app/eventos.py`), un suscriptor lo recoge, y el trabajo va a un hilo aparte. Si el
correo no sale o el aviso no llega, se registra y ya está. **No hay cola, ni
reintentos, ni *outbox*.**

Lo que hace aceptable esa pérdida es que ninguna de las dos lleva información que
no esté ya en otro sitio. El código de canje está en la pantalla de quien pagó, y
esa pantalla se entera sola del estado cada cinco segundos.

### El comprobante

- **SMTP con la biblioteca estándar**, para no atar el código a un proveedor ni
  añadir una dependencia. Cambiar de servicio de correo son cuatro variables.
- **Se llama «comprobante» y no «factura electrónica».** Una factura electrónica de
  venta en Colombia es un documento que valida la DIAN. El consecutivo es propio
  (`PU-000123`) y el pie aclara que no la reemplaza.
- **El correo y el nombre son opcionales.** Pedir sin dejar ningún dato sigue siendo
  pedir. Ninguna respuesta de la API los devuelve, ni siquiera la cola del mostrador.

### El aviso

Web Push con un Service Worker, la opción que no exige una aplicación nativa.

- **El aviso va vacío.** Solo se firma quién lo manda (VAPID); no se cifra ningún
  contenido, porque no hay contenido. La notificación la escribe `sitio/sw.js` y dice
  siempre lo mismo. Así **el código de canje nunca pasa por los servidores de Google
  ni de Apple, ni sale en la pantalla de bloqueo**, donde cualquiera podría leerlo.
- **El Service Worker no toca la caché ni intercepta nada.** Este sitio ya sufrió
  una página rota por mezclar un `index.html` nuevo con un `app.js` viejo (ver
  `sitio/Dockerfile`), y es exactamente lo que trae una caché mal invalidada.
- **Solo se escribe a servicios de push conocidos.** La dirección la da el navegador
  y la llama nuestro servidor: sin esa lista, cualquiera podría hacerle llamar a un
  servicio interno del laboratorio (SSRF). Tampoco se siguen redirecciones.

### Qué funciona en cada teléfono

| Plataforma | Vibración con la página abierta | Notificación con la pantalla apagada |
|---|---|---|
| Android, Chrome o Edge | Sí, si ya tocaron la página | Sí, con permiso. No hay que instalar nada |
| Android, Firefox | **No**: lo retiró en la versión 129 | Sí, con permiso |
| iPhone, en el navegador | **Nunca** | **No** |
| iPhone, instalada en la pantalla de inicio (iOS 16.4+) | **Nunca** | Sí, con permiso, y la vibración la decide el sistema |

Dos consecuencias de iPhone que no se pueden arreglar desde aquí: hay que instalarla
**antes** de pedir, porque la aplicación instalada no comparte almacenamiento con
Safari y no vería el pedido hecho allí; y la propia persona tiene que permitir las
notificaciones con un toque, que es la razón de que el permiso se pida con un botón.

## Alternativas consideradas

### Una cola con *outbox* para no perder nada

Resuelve perder mensajes que aquí se pueden perder. Costaría una tabla, un proceso
que la recorra y lógica de reintentos, en un sistema con 192 MB para la API, para
proteger un correo de respaldo. **Descartada.** El día que dependa algo de un
suscriptor, `test_quien_escucha_los_pagos_es_prescindible` falla y obliga a rehacer
esta cuenta.

### `pywebpush`

Es la biblioteca habitual, y arrastra `aiohttp` y `requests` para hacer un POST. La
S13 sacó de la imagen ocho paquetes que no se usaban. Se usa `cryptography`, que es
la pieza que de verdad hace falta y que tampoco se puede escribir a mano: firmar es
lo único que la biblioteca estándar no sabe hacer. Se importa al usarla, así que un
despliegue sin avisos no paga su memoria. **Descartada.**

### Cifrar el contenido del aviso

Permitiría decir «Pedido #12: K7M2X9» en la notificación. Pide escribir RFC 8291 a
mano, y lo que ganaría es justo lo que no se quiere: el código a la vista en una
pantalla de bloqueo. **Descartada.**

### Una aplicación nativa

Es lo único que daría vibración controlada en iPhone. Son dos bases de código, una
tienda de aplicaciones y un proceso de revisión para vibrar un teléfono en un
proyecto de un campus. **Descartada.**

### Extraer las salidas a un servicio

Es la pregunta que ADR-0009 deja abierta. La respuesta sigue siendo no: las salidas
no escalan distinto, caben en dos hilos, y un fallo suyo ya no afecta a nadie. Un
servicio aparte añadiría un contenedor para aislar algo que ya está aislado.

## Consecuencias

**Positivas.** El pedido no cambió de forma: `pedidos.service` publica y sigue, y no
sabe que existen el correo ni los avisos. La conexión son dos líneas en `main.py`.

**Negativas y costes aceptados.**

- **Un correo puede no llegar, y nadie se entera salvo por los registros**
  (`comprobante_no_enviado`). Tampoco hay forma de reenviarlo.
- **`pedidos` guarda datos de personas por primera vez** cuando alguien los deja, y
  hoy nada los borra (arc42 §8.8). Con clientes reales habría que definir retención
  y una política de tratamiento de datos (Ley 1581 de 2012).
- **`cryptography` es una dependencia más**, con `cffi` y `pycparser` detrás.
- **Se confía en que el laboratorio permita salir a Internet** por 443 y por el
  puerto de SMTP. Si no, ni el correo ni el aviso salen, y el resto sigue igual.

## Qué cambiaría esta decisión

- **Que el comprobante pase a ser obligatorio**, por ejemplo por ser una factura
  electrónica de verdad. Entonces no se puede perder, y hace falta una cola y un
  proveedor autorizado por la DIAN.
- **Que el aviso sea la única forma de enterarse.** Hoy la pantalla también se entera.
- **Que haya más de un proceso de API**: el bus es en memoria (R-03).

## Trazabilidad

| Elemento | Dónde |
|---|---|
| El correo | `backend/app/comprobante.py` · `backend/app/correo.py` |
| El aviso | `backend/app/avisos.py` · `sitio/sw.js` · `sitio/manifest.json` |
| El bus y el hilo de salida | `backend/app/eventos.py` |
| Los contratos | [`openapi.yaml`](../api/openapi.yaml) · [`asyncapi.yaml`](../api/asyncapi.yaml) |
| Las columnas nuevas | [`011_recogida_comprobante_y_aviso.sql`](../../backend/migraciones/011_recogida_comprobante_y_aviso.sql) |
| Las pruebas | `backend/tests/test_comprobante.py` · `test_avisos_push.py` · `e2e/aviso-push.spec.js` |
| Datos personales | [arc42 §8.8](../arc42/arc42.md) |
| La decisión que esto revisa | [ADR-0009](0009-no-extraer-un-servicio.md) · [ADR-0010](0010-notificar-al-panel-por-sondeo.md) |
