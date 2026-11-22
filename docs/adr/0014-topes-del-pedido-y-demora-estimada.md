# ADR 0014: Poner topes al pedido por producto y por tipo, y avisar su demora antes de pagar

## Estado

Aceptada — 22/11/2026.

## Contexto

Hasta la 5.0.0 del contrato, un pedido admitía hasta 50 unidades de cada producto y
hasta 30 productos distintos. El tope de 50 venía de
[V-03](../violaciones.md#v-03): estaba pensado para que un error de tecleo no generara
un pedido imposible.

**No bastó.** El 21/11/2026 se pagó un pedido de más de 800 000 pesos. Ningún
mostrador lo prepara en una hora de almuerzo, y quien lo hizo no tenía forma de saber
cuánto iba a esperar.

El cliente pidió dos cosas:

1. **Topes.**
   - Hasta 4 unidades de un mismo producto.
   - Hasta 4 comidas por pedido, sumadas: 2 asados y 2 hamburguesas caben; 4 asados y
     4 hamburguesas, no.
   - Las bebidas y los acompañantes no cuentan contra las comidas. Tienen su propio
     tope de 4, así que el pedido más grande es 4 comidas, 4 bebidas y 4 acompañantes.
2. **Un aviso de demora antes de pagar**, que crezca con el tamaño del pedido y
   pregunte «¿Seguro que quieres seguir con el pago?».

La carta tiene cinco categorías: Asados, Hamburguesas y perros, Bebidas, Adiciones y
Salsas.

## Decisión

### 1. Los topes los exige la API, y la página los anticipa

- **Por producto, en el esquema.** `cantidad` baja su máximo de 50 a 4, y pasarse
  responde `422`. Es la regla I-9 de la [política de versionado](../api/politica-versionado.md)
  (estrechar una restricción de la petición), así que el contrato sube a **6.0.0**.
  La ruta sigue siendo `/v1` por el mismo motivo que en la 3.0.0 y la 5.0.0: hay un
  solo consumidor declarado, y se despliega a la vez.
- **Por tipo, en el servicio.** Depende de qué es cada producto, y eso no cabe en un
  esquema. `pedidos.service.crear_pedido` suma las unidades de cada tipo y responde
  `409` si alguna pasa de 4, con un mensaje que dice cuál. Es `409` y no `422` porque
  la petición está bien formada; lo que no cabe es la suma, igual que un producto
  agotado.
- **Se valida todo antes de escribir nada.** Un pedido que se pasa no se guarda a
  medias.

### 2. El tipo lo decide el Catálogo, a partir de la categoría

`menu.service.TIPO_POR_CATEGORIA` dice qué es cada categoría:

| Tipo | Categorías |
|---|---|
| Comida | Asados, Hamburguesas y perros |
| Bebida | Bebidas |
| Acompañante | Adiciones, Salsas |

El Catálogo lo publica en `ItemMenu.tipo`, que es una adición compatible dentro de la
6.0.0. Pedidos solo cuenta, y lo lee por el contrato del Catálogo, como lee el precio.

Una categoría sin tipo deja a sus productos solo con el tope de 4 por producto. Para
que eso no pase sin que nadie lo vea, `test_cada_categoria_de_la_carta_tiene_tipo`
pide la carta real a PostgreSQL, con las migraciones aplicadas, y falla si alguna
categoría no tiene tipo.

### 3. La página apaga el «+» antes de que la API diga que no

- `sitio/config.js` copia los topes, y `test_el_sitio_conoce_los_mismos_topes`
  impide que se separen de los de la API.
- Al llegar a un tope, el «+» se apaga y una línea ámbar dice por qué: «Llegaste al
  máximo de 4 comidas por pedido».

### 4. La demora se estima por tamaño y se pregunta siempre antes de pagar

- **Cálculo.** 15 minutos con una comida y 5 más por cada comida adicional, así que va
  de 15 a 30 minutos. Las bebidas y los acompañantes no suman.
- **Dónde se ve.** Aparece en «Tu pedido» como «Tiempo estimado», y otra vez en un
  diálogo antes de crear el pedido: «Tu pedido puede demorarse unos X minutos.
  ¿Seguro que quieres seguir con el pago?».
- **Volver no crea el pedido.** Elegir «Volver al pedido», o cerrar con Esc, deja el
  carrito como estaba.
- **Reintentar no vuelve a preguntar.** El cobro de un pedido que ya existe no cambia
  su demora.
- **Se calcula en la página**, que es donde se pregunta. No añade nada al contrato.

## Alternativas consideradas

### Exigir los topes solo en la página

El pedido de 800 000 pesos pasó porque la API lo aceptaba. Una regla que solo vive en
el formulario se salta llamando a la API: es el mismo argumento de
[ADR-0013](0013-correo-obligatorio-para-el-comprobante.md).

### Una columna `tipo` en la base, con su `CHECK`

Sería más firme a nivel de datos, pero pide una migración y tocar el repositorio en
sus dos implementaciones. Todo eso para un dato que ya se deduce de otro que el
Catálogo tiene, en una carta de cinco categorías. Pasaría a hacer falta si una
categoría dejara de corresponder a un solo tipo.

### Un tope por importe, por ejemplo 200 000 pesos

El problema es el tiempo de preparación, no el dinero. Cuatro porciones de salsa no
tardan lo que cuatro asados, y un tope por importe las trataría igual.

### Calcular la demora en la API, o con la cola del mostrador

Sería más preciso, pero exige un dato que no existe: cuánto tarda cada plato. También
habría que llevar el estimado al contrato. El cliente pidió que la demora creciera con
el tamaño del pedido, y eso se calcula donde se pregunta.

### Avisar solo cuando el pedido pase de cierto tiempo

El cliente prefirió que se avise siempre, para que nadie pague sin saber cuánto va a
esperar.

## Consecuencias

**Positivas.**

- **El pedido más grande cabe en una hora de almuerzo.** Con la carta de hoy, el más
  caro posible pasa de más de 800 000 pesos a 184 400: 4 × 33 400 en comidas,
  4 × 5 400 en bebidas y 4 × 7 300 en acompañantes. Su demora estimada es de 30
  minutos.
- **Quien pide sabe cuánto va a esperar antes de pagar.**
- **La página no deja armar un carrito que la API rechazaría.**

**Negativas y costes aceptados.**

- **El contrato 6.0.0 es incompatible.** Una línea con más de 4 unidades responde
  `422`, y pasarse del tope de un tipo, `409`. Los pedidos anteriores con más, incluido
  el de 800 000 pesos, siguen en la base: no se tocan.
- **La demora es una estimación fija por tamaño.** No mira la cola del mostrador, ni
  la hora pico, ni qué plato es: dos pedidos de 4 comidas seguidos esperan más de lo
  que dice el aviso.
- **Los topes viven en dos sitios**, la API y `sitio/config.js`, atados por una prueba.
- **Pagar lleva un paso más:** el diálogo sale en todo pedido nuevo.
- **Una categoría nueva necesita su tipo** en `TIPO_POR_CATEGORIA`, o la construcción
  falla.
- **Quien necesite más tiene que hacer dos pedidos**, por ejemplo para un grupo.

## Qué cambiaría esta decisión

- **Que el mostrador registre cuánto tarda cada plato.** Entonces la demora la
  calcularía la API con esos tiempos y con su cola.
- **Que haya pedidos de grupo o por encargo,** con más anticipación y otro tope.
- **Que una categoría deje de corresponder a un solo tipo.** Entonces haría falta una
  columna `tipo` en la base.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Los topes en la API | `backend/app/pedidos/service.py` (`MAXIMO_POR_PRODUCTO`, `MAXIMO_POR_TIPO`, `LimiteDelPedidoError`) · `backend/app/pedidos/esquemas_api.py` |
| El tipo de cada producto | `backend/app/menu/service.py` (`TIPO_POR_CATEGORIA`) · `backend/app/menu/contracts.py` (`TipoDeProducto`) |
| El contrato | [`openapi.yaml`](../api/openapi.yaml) 6.0.0 · [`historial/openapi-6.0.0.yaml`](../api/historial/openapi-6.0.0.yaml) · [`consumidor-web.yaml`](../../contracts/consumidor-web.yaml) |
| La página | `sitio/config.js` · `sitio/app.js` (`motivoParaNoAgregar`, `minutosEstimados`, `confirmarLaDemora`) · `sitio/index.html` (`#dialogo-demora`) |
| Las pruebas | `backend/tests/test_topes_del_pedido.py` · `e2e/flujo-completo.spec.js` («Los topes del pedido y su demora») |
| Lo que esto revisa | [V-03](../violaciones.md#v-03) |
