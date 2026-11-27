# ADR 0015: Un conteo diario de unidades por producto, que el pedido reserva y la cancelación devuelve

## Estado

Aceptada — 27/11/2026.

## Contexto

Hasta la 6.0.0 del contrato, lo único que decía si un producto se podía vender era
`disponible`: un sí o un no que el mostrador marca a mano. La app no sabía **cuántas**
unidades había de nada.

En la sustentación del 25/11/2026 se señaló lo que eso no cubre: nada impedía pagar
diez arepas cuando quedaban tres. El pedido se creaba, el cobro se confirmaba, el
comprobante salía con su código, y el mostrador se enteraba al ir a prepararlo. Un
pedido pagado que no se puede preparar es el peor caso del sistema: hay que devolver
dinero fuera de la aplicación, y la persona ya hizo la fila.

El mostrador de El Asao sabe por la mañana cuántas porciones de cada cosa va a tener
en el día; lo que no tiene es dónde decirlo.

## Decisión

### 1. Un número por producto, que fija el mostrador

`menu_items.unidades_hoy` (migración `017`): un entero, nulo por defecto.

- **Nulo = sin control.** El producto se vende como hasta ahora, sin descontar nada.
  Es el valor de **toda** la carta al aplicar la migración, y es lo que hace que este
  cambio no altere el comportamiento de nadie hasta que un mostrador decida contar.
- **Cero = agotado.** El Catálogo lo publica con `disponible: false`, igual que si el
  mostrador lo hubiera marcado, y la carta con `solo_disponibles` lo omite. El
  mostrador no tiene que tocar dos cosas.

Lo fija `POST /v1/menu/items/{item_id}/inventario` (`fijarInventarioDelDia`), con la
sesión del mostrador y sobre su propio establecimiento. El número se escribe **tal
cual**, no se suma a lo que había: el mostrador cuenta lo que tiene en la vitrina y
ese número manda. Un ítem de otro establecimiento responde `404` y no `403`, por la
misma razón que un pedido ajeno: confirmar que existe permitiría recorrer la carta
ajena probando identificadores.

Es un sub-recurso con nombre y no un `PATCH` sobre el ítem, por coherencia con
`/estado` en Pedidos: la ruta dice que lo único que el mostrador puede tocar del
catálogo es el conteo del día.

### 2. El pedido reserva al crearse, y la cancelación devuelve

`pedidos.service.crear_pedido` llama a `menu.service.reservar_unidades` **después de
todas las validaciones y antes de guardar**. Después de validar, para que un carrito
que la hora o los topes van a rechazar no toque el inventario; antes de guardar,
porque si no alcanza no debe existir el pedido.

- **Todo o nada.** Un carrito con un producto que no alcanza se rechaza entero y no
  descuenta ninguna línea, ni de ese producto ni de los demás. Contra PostgreSQL es
  una transacción con `rollback`; en memoria, comprobar todo antes de escribir.
- **La condición viaja dentro del `UPDATE`:** `WHERE unidades_hoy >= cantidad`. Es la
  misma primitiva que `marcar_pagado` y por el mismo motivo: dos pedidos a la vez por
  la última arepa leen «queda 1» los dos, y lo único que impide venderla dos veces es
  que el motor deje pasar a uno solo. `test_dos_reservas_de_la_ultima_unidad_solo_una_gana`
  lo ejecuta con dos hilos.
- **Catálogo es el único escritor de `menu_items`.** Pedidos no descuenta: *pide* que
  se descuente, por la interfaz pública del Catálogo (ADR-0001), igual que Pagos pide
  a Pedidos que confirme un pago.
- **Responde `409`**, con el mensaje del Catálogo —«Solo quedan 2 de 'Arepa de huevo'»—
  dentro del mismo error de disponibilidad que ya existía. Para quien pidió es la misma
  situación que un producto agotado, y el router no cambia.
- **Al cancelar**, `avanzar_estado` devuelve las unidades de las líneas guardadas.

### 3. Dos escrituras, dos contextos, sin transacción compartida

Reservar y guardar el pedido son dos escrituras en dos repositorios, y **no comparten
transacción**: compartirla sería que Pedidos tocara la tabla del Catálogo por la
puerta de atrás. Así que si guardar falla después de reservar, Pedidos **compensa**
devolviendo las unidades antes de propagar el error.

Se reserva primero y no al revés **a propósito**. Si la compensación también fallara,
lo que quedaría es una unidad retenida de más, que el mostrador corrige escribiendo
un número; al revés quedaría un pedido pagable sin unidades detrás, que es vender lo
que no hay — justo lo que esto existe para impedir.

### 4. La carta avisa antes de que la API diga que no

`ItemMenu` publica `unidades_hoy`. El sitio pinta «Quedan N» cuando quedan cinco o
menos —«quedan 40» no cambia la decisión de nadie— y apaga el «+» al llegar a ese
número, con «Solo quedan N». Si la carta ya está vieja y alguien se pasa igual, el
`409` trae el mismo mensaje desde la API. Quien decide si alcanza es siempre la API.

### 5. El contrato sube a 6.1.0, y es MENOR

Un campo anulable nuevo en una respuesta y una operación nueva: §2 de la política lo
clasifica como compatible. El `409` por unidades merece una palabra, porque el tope
por tipo de la 6.0.0 también era un `409` con un código ya declarado y **sí** contó
como rotura: aquel rechazaba desde el primer despliegue una petición que la 5.0.0
aceptaba; este no rechaza ninguna hasta que un mostrador fija un conteo, y entonces
rechaza por el **estado del recurso**, que es lo que `409` significaba ya para un
producto agotado. Está escrito en la política, §6.

## Alternativas consideradas

### No controlar: lo que había

Seguir confiando en `disponible`. Es exactamente lo que se criticó, y el modo de
fallo —un pedido pagado que no se puede preparar— cuesta una devolución fuera del
sistema. No se defiende.

### Descontar al confirmar el pago

Reservar solo cuando la pasarela confirma, para que un pendiente de pago abandonado
no retenga nada. El problema es la ventana: entre crear el pedido y confirmarlo pasan
uno o dos minutos en la pasarela, y en ese tiempo la carta seguiría ofreciendo la
arepa que alguien está pagando. Dos personas podrían **pagar** la misma última
unidad, y entonces el `409` llegaría después del cobro, que es peor que antes del
cobro: habría que devolver dinero. Descontar al crear cierra la puerta antes de que
alguien pague por pasar.

### Reservar al crear y devolver al cancelar — la elegida

Es la única de las tres que garantiza que **ningún pedido pagado se queda sin sus
unidades**. Su coste es la reserva retenida por un pendiente de pago abandonado, y
se acepta con los ojos abiertos (abajo).

### Inventario en tiempo real con WebSocket

Empujar el conteo a cada carta abierta en cuanto cambia, para que «Quedan 2» pase a
«Quedan 1» sin recargar. Se descarta por lo mismo que ADR-0010 descartó el empuje
para el panel: el sondeo de 5 s ya cubre el refresco que hace falta, no hay un
segundo consumidor que lo justifique, y una conexión persistente por cada teléfono
con la carta abierta es un coste de memoria en un contenedor de 160 MB. La carta vieja
no vende nada de más: el `409` de la API es quien decide.

## Consecuencias

**Positivas.**

- **No se vende lo que no hay.** Un pedido solo existe si sus unidades existían al
  crearlo, y la última se vende una sola vez aunque dos la pidan a la vez.
- **El mostrador tiene dónde decir cuántas tiene**, y la carta lo repite.
- **Nada cambia para quien no cuenta.** Toda la carta arranca sin control.
- **Cero es agotado sin un segundo paso.**

**Negativas y costes aceptados.**

- **Un pedido en `pendiente_pago` que nadie termina de pagar retiene sus unidades.**
  No hay caducidad, y **es una decisión, no un olvido**: una caducidad automática
  liberaría la arepa de quien está terminando de pagar en la pasarela, y elegir el
  plazo sería adivinar cuánto tarda cada persona. El camino de vuelta es el mostrador,
  que corrige el conteo en cualquier momento con `fijarInventarioDelDia`. Queda
  anotado en el código (`avanzar_estado`) y fijado por `test_un_pedido_sin_pagar_retiene_sus_unidades`.
- **Dos escrituras sin transacción común.** Si la compensación falla, queda una unidad
  retenida de más. Se eligió ese lado del fallo, y el mostrador lo corrige con un
  número.
- **El conteo es manual y diario.** Nadie lo pone a cero por la noche: el mostrador
  lo fija cada mañana, o lo deja en nulo y vende como antes.
- **El Catálogo gana su primera escritura por HTTP**, con sesión. Hasta aquí era de
  solo lectura hacia fuera.
- **La carta puede ir un sondeo por detrás.** Alguien puede ver «Quedan 1» y recibir
  el `409`; el mensaje dice por qué.

## Qué cambiaría esta decisión

- **Que los abandonos retenidos sean un problema real**, medido en el mostrador.
  Entonces se discutiría una caducidad, con su plazo justificado por datos.
- **Que haga falta saber por qué quedan dos y no tres.** Entonces el entero se
  convierte en el saldo de una tabla de movimientos.
- **Que la carta la miren a la vez muchas personas por producto escaso**, de modo que
  el sondeo deje de alcanzar y el `409` se vuelva frecuente.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| La columna | `backend/migraciones/017_inventario_diario.sql` |
| El descuento atómico y sus parejas | `backend/app/menu/repository.py` (`descontar_unidades`, `devolver_unidades`, `fijar_unidades`) |
| La interfaz pública del Catálogo | `backend/app/menu/service.py` (`reservar_unidades`, `liberar_unidades`, `fijar_unidades_del_dia`, `UnidadesInsuficientesError`) · `backend/app/menu/contracts.py` (`unidades_hoy`) |
| El endpoint del mostrador | `backend/app/menu/router.py` (`fijar_inventario_del_dia`) · `backend/app/menu/esquemas_api.py` (`InventarioDelDiaRequest`) |
| Reservar, compensar y devolver | `backend/app/pedidos/service.py` (`crear_pedido`, `avanzar_estado`) |
| El contrato | [`openapi.yaml`](../api/openapi.yaml) 6.1.0 · [`historial/openapi-6.1.0.yaml`](../api/historial/openapi-6.1.0.yaml) · [`consumidor-web.yaml`](../../contracts/consumidor-web.yaml) · [política §6](../api/politica-versionado.md#6-historial) |
| La carta | `sitio/app.js` (`quedanPocas`, `motivoParaNoAgregar`, `dibujarNotaDeTopes`) |
| Las pruebas | `backend/tests/test_inventario_diario.py` · `backend/tests/test_repositorios.py` (paridad de `descontar`/`devolver`/`fijar`) |
| Lo que esto revisa | [ADR-0014](0014-topes-del-pedido-y-demora-estimada.md) (los topes dicen cuánto cabe en un pedido; esto, cuánto hay) |
