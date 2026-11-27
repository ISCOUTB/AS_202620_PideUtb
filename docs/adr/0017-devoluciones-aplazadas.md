# ADR 0017: Aplazar las devoluciones de dinero, y dejar escrito cómo se harían

## Estado

Aplazada — 27/11/2026. Se decide **no construir** la devolución ahora, y se fija
qué haría falta para construirla.

## Contexto

En la sustentación final del 25/11/2026 preguntaron cómo garantiza el sistema la
seguridad del pago: que el código no se repita, que no haya devoluciones indebidas y que
no se venda lo que no hay. Las tres respuestas están repartidas:

- **El código no se repite.** Se genera con `secrets` sobre un alfabeto de 31
  caracteres, la columna es `UNIQUE`, la confirmación del pago es idempotente dentro de
  un `UPDATE ... WHERE estado = 'pendiente_pago'` —dos avisos del mismo pago no generan
  dos códigos—, y `entregado` es un estado final, así que el segundo intento de canje
  no falla por el código sino porque ya no hay transición
  ([ADR-0005](0005-maquina-de-estados-del-mostrador.md), [arc42 §8.5](../arc42/arc42.md#idempotencia)).
- **No se vende lo que no hay.** Lo resuelve
  [ADR-0015](0015-inventario-diario-por-producto.md).
- **Las devoluciones.** Este ADR.

Hoy un pedido pagado puede pasar a `cancelado` desde el mostrador
([ADR-0005](0005-maquina-de-estados-del-mostrador.md)), y **el dinero no vuelve**. No
hay reembolso automático ni registro de que se deba uno. Es un hueco real, y fue
señalado.

## Por qué no se construye ahora

No es falta de tiempo; es que las tres piezas que una devolución necesita no existen
en este despliegue, y construir la cuarta sin las tres sería una pantalla que promete
algo que no ocurre:

1. **La pasarela está en sandbox.** Wompi en modo de pruebas no mueve dinero, así que un
   reembolso automático no se puede probar de verdad: la prueba pasaría y nadie
   sabría si el dinero vuelve. En producción, además, la devolución exige una cuenta
   de comercio real y credenciales de las que el proyecto no dispone.
2. **No hay cuentas de cliente** ([arc42 §8.8](../arc42/arc42.md#datos-personales)), y es
   una decisión. Sin cuenta no hay a quién acreditarle un saldo, así que la única
   devolución posible es a la pasarela, y eso devuelve al punto 1.
3. **No hay conciliación contable.** Una devolución es dinero que sale, y sale de una
   caja que lleva una persona. Sin un cierre diario contra el que cuadrar, un
   reembolso automático es una cifra que nadie revisa.

Lo que sí se decide, y es lo que la crítica pedía que quedara claro, es **cuál es la
regla hoy**: un pedido pagado que el mostrador cancela se devuelve **en caja, a mano, al
presentar el código de recogida**, igual que en cualquier cafetería. El código es la
prueba de pago también para esto.

## Cómo se haría, cuando se haga

Se deja el diseño para que la decisión futura sea construir y no pensar:

| Pieza | Qué |
|---|---|
| Un estado nuevo | `reembolso_pendiente`, al que se llega **solo** desde `cancelado` con pago confirmado. `cancelado` deja de ser final para los pagados: pasa a serlo `reembolsado`. Es un valor nuevo en un `enum` de respuesta, regla I-8: sube la MAYOR del contrato |
| El registro | Una tabla `reembolsos` en el contexto Pagos, con `pedido_id`, `importe_centavos`, `motivo`, `creado_en`, `resuelto_en` y quién lo resolvió. Pagos es su único escritor, como de los intentos |
| El disparador | La misma transición del mostrador: cancelar un pedido pagado crea el reembolso pendiente en la misma petición. Si la pasarela admite devolución por API, un suscriptor del canal lo pide; si no, queda pendiente para caja |
| La vista | Una columna más en el tablero del panel, plegada como los terminados, con el botón «Devuelto en caja» |
| Lo que lo vigila | Una prueba de que ningún pedido quede `cancelado` con pago confirmado y sin fila de reembolso: la misma forma que `conciliar()` en [arc42 §6.7](../arc42/arc42.md#fallos-parciales) |

Nada de esto es difícil. Lo que falta es lo de arriba: una pasarela real, y una caja
contra la que cuadrar.

## Qué cambiaría esta decisión

- **Que la pasarela pase a producción.** Es la condición necesaria; sin ella, una
  devolución automática no se puede comprobar.
- **Que el mostrador cancele pedidos pagados con alguna frecuencia.** Hoy no hay dato:
  la cola no registra motivos. Si los `cancelado` con pago confirmado pasaran de ser
  excepcionales, la devolución a mano dejaría de escalar.
- **Que aparezcan cuentas de cliente.** Entonces el saldo a favor sería una devolución
  posible sin pasar por la pasarela.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Por qué el código no se repite | [ADR-0005](0005-maquina-de-estados-del-mostrador.md) · [arc42 §8.5](../arc42/arc42.md#idempotencia) · `backend/app/pedidos/service.py`, `confirmar_pago` y `avanzar_estado` |
| La transición que deja el hueco | `TRANSICIONES_DEL_MOSTRADOR`, `pagado → cancelado` |
| La ventana entre pago y pedido, que una saga agravaría | [ADR-0009](0009-no-extraer-un-servicio.md) |
| Por qué no hay cuentas de cliente | [arc42 §8.8](../arc42/arc42.md#datos-personales) |
