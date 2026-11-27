# ADR 0016: Entregar leyendo un QR con la cámara del mostrador, y ordenar la cola en un tablero por estado

## Estado

Aceptada — 27/11/2026.

## Contexto

En la sustentación final del 25/11/2026 hubo dos observaciones sobre el mostrador:

1. **El panel se veía como una lista**, y en hora pico quien atiende tenía que leer el
   estado de cada fila para saber cuál era la suya. La recomendación fue mejorar el
   diseño del frente, y el mostrador en particular.
2. **Teclear el código es lento.** El cliente dicta seis caracteres por encima del
   ruido de una freidora, quien atiende los escribe, y si uno se oye mal se repite. Se
   propuso que la pantalla del cliente mostrara un QR y que el mostrador lo escaneara.

Las dos tocan la misma pantalla y la misma operación (entregar, [ESC-04](../arc42/arc42.md#esc-04)),
así que se deciden juntas.

Lo que **no** cambia es la regla de ESC-04: entregar exige presentar el código, el
servidor lo compara en tiempo constante, y el panel no lo muestra mientras el pedido
esté por entregar. Cualquier forma de leerlo tiene que seguir pasando por ahí.

## Decisión

### 1. El billete lleva el código también como QR, dibujado en el navegador

`sitio/qr.js` es un port de `backend/scripts/generar_qr.py`: el mismo algoritmo (ISO/IEC
18004, modo byte, nivel Q), sin dependencias, y una prueba exige que las dos copias
dibujen la **misma matriz** para los mismos textos. El QR va debajo del código grande y
más pequeño que sus letras: la cámara lo lee a un palmo, y el código grande sigue siendo
lo que se dicta si la cámara falla.

Lo que se codifica es `pideutb:<pedido>:<código>`. El número de pedido va dentro
porque el mostrador necesita saber **a cuál** pedirle la entrega: con el código a secas
tendría que probarlo contra cada pedido listo, que es exactamente la enumeración que
ESC-04 prohíbe. El número ya es secuencial y visible en las dos pantallas, así que el QR
no revela nada nuevo; el código sigue siendo la llave.

Se dibuja solo mientras el pedido está en `pagado`, `en_preparacion` o
`listo_para_recoger`. Entregado o cancelado, un QR escaneable sería una llave dibujada
sobre una puerta ya cerrada.

### 2. El panel lo lee con `BarcodeDetector`, y donde no esté se teclea

El lector es la API del navegador para leer códigos, sin bibliotecas, por el mismo
motivo que el resto del sitio. La traen Chrome y Edge en escritorio y Android, que es lo
que hay en el mostrador. Donde no esté —Firefox, Safari de escritorio— los botones de
cámara no aparecen y se teclea, que es lo que siempre funcionó. **La cámara es la forma
rápida, no la única.**

Hay dos sitios desde donde escanear, porque hay dos situaciones:

- **«Escanear QR», en la barra.** Quien atiende no sabe de qué pedido es el cliente que
  tiene delante: lee el QR, el panel saca el número y el código, y pide la entrega. Una
  interacción. Si el pedido no está listo todavía, el servidor responde `409` y el
  mensaje lo dice.
- **«Leer el QR con la cámara», dentro del diálogo del código.** Ya se pulsó «Entregado»
  en una tarjeta concreta. Si el QR es de otro pedido, se dice y el diálogo sigue
  abierto: lo más probable es que haya dos clientes en el mostrador y se haya pulsado
  el botón del pedido equivocado.

La lectura se valida con la misma forma que exige la API (`^[A-Z0-9]{6}$` para el
código, un entero para el pedido) **antes** de armar ninguna ruta, y el identificador va
codificado en la URL como el resto del sitio. La cámara se apaga siempre al cerrar el
diálogo, pase lo que pase: una cámara encendida en un equipo compartido es un problema
distinto de todos los demás de esa pantalla.

### 3. La cola pasa a ser un tablero de tres columnas

Por preparar, en preparación, listos para recoger. El estado es la columna, y la cuenta
de cada una dice cuánto trabajo hay sin contar tarjetas. Los pedidos que esperan el pago
van en la primera, con borde punteado y sin botones: no se pueden preparar todavía, pero
ya existen y conviene verlos venir. Entregados y cancelados quedan plegados debajo: están
para resolver un reclamo —«¿con qué código se entregó el 41?»—, no para operar.

La tarjeta se pone de pie: número grande con la letra de los títulos, hora de recogida
al lado, una línea por producto con la cantidad delante, estado y total, y los botones
abajo a lo ancho. Las columnas se apilan en el teléfono y van una al lado de la otra a
partir de 900 px, que es una tablet apaisada.

Lo que no cambia: los mismos colores y tipografías de la hoja, la misma máquina de
estados (`ACCIONES_POR_ESTADO` es la misma tabla), el sondeo de 5 s de
[ADR-0010](0010-notificar-al-panel-por-sondeo.md), y `#cola .pedido` como lo que buscan
las pruebas de navegador. Se tomó la estructura de los mockups que el equipo preparó
—tres columnas, tarjeta por pedido, cuenta por columna— y no su paleta ni sus funciones:
casilleros, becas o ventas del día no existen en este sistema y no se dibujan.

## Alternativas consideradas

### Que la API sirva el QR como imagen

Un `GET /v1/pedidos/{id}/qr.svg` con el token del pedido. Descartado: el código ya está
en el teléfono, y pedirle al servidor una imagen de un dato que la pantalla ya tiene es
una petición más justo cuando la red del auditorio está peor. Además metería el token
de consulta en una URL, que es donde no debe ir.

### Una biblioteca de lectura de QR en JavaScript

Las hay buenas, y funcionarían en Firefox y Safari. Descartado porque el sitio no tiene
paso de construcción ni dependencias, y meter una de 300 KB para una pantalla que usa un
solo equipo con Chrome no sale a cuenta. Si el mostrador cambiara de navegador, sería el
momento de volver a mirarlo.

### Codificar solo el código en el QR

Más corto, y un lector cualquiera mostraría solo seis letras. Descartado porque el panel
no sabe de qué pedido es cada código —a propósito— y tendría que probarlo contra todos
los listos.

### Una pantalla del mostrador distinta por columna, o pestañas

Descartado: en hora pico se mira todo a la vez, y cambiar de pestaña para ver si hay algo
listo es una interacción que ESC-03 no concede.

## Consecuencias

- Entregar un pedido pasa de tres interacciones (botón, teclear, confirmar) a una
  (escanear), cuando hay cámara.
- Hay dos copias del codificador de QR, en Python y en JavaScript. Son el mismo algoritmo
  a propósito y `test_qr.py` las ata: el que cambie una tiene que arrastrar la otra.
- `qr.js` entra en la lista de activos que el `Dockerfile` sella con su huella, como el
  resto de los guiones. Una prueba comprueba que la lista cubre lo que las páginas piden.
- La lectura depende de una API que no está en todos los navegadores. La degradación es
  explícita —los botones no aparecen— y no silenciosa.
- La pantalla del cliente muestra el número de pedido dentro del QR. Ya lo mostraba en
  texto; no cambia lo que se puede saber desde fuera.
- Las pruebas de navegador del mostrador siguen buscando `#cola .pedido`,
  `.pedido-recogida` y `.item-nombre`, y pasan sin cambios.

## Qué cambiaría esta decisión

- **Que el mostrador use un navegador sin `BarcodeDetector`.** Entonces habría que
  elegir entre una biblioteca de lectura y seguir tecleando.
- **Que aparezca un segundo tipo de QR en el sistema** (una mesa, una promoción). El
  prefijo `pideutb:` está para eso: el lector distingue los nuestros, y un formato nuevo
  es un prefijo nuevo.
- **Que el código deje de ser la llave** —por ejemplo, con cuentas de cliente—. Entonces
  el QR podría ser un token firmado y no el código en claro.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| El codificador del sitio | `sitio/qr.js` |
| El billete con el QR | `sitio/app.js`, `dibujarElBillete` |
| El tablero y la cámara | `sitio/panel.html` · `sitio/panel.js` (`tarjeta`, `pintar`, `escanearQR`, `entregarEscaneando`) |
| Los estilos | `sitio/estilos.css`, sección «El tablero (S17)» y «La cámara» |
| El sellado del guion nuevo | `sitio/Dockerfile` |
| La prueba que ata las dos copias | `backend/tests/test_qr.py::test_el_qr_del_sitio_dibuja_la_misma_matriz_que_python` |
| El escenario que sostiene | [ESC-04](../arc42/arc42.md#esc-04) · [ESC-03](../arc42/arc42.md#esc-03) |
| De dónde viene la regla del código | [ADR-0005](0005-maquina-de-estados-del-mostrador.md) |
