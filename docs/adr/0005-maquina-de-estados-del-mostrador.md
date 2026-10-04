# ADR 0005: Declarar las transiciones del mostrador como dato y excluir el pago de ellas

## Estado

Aceptada — 04/10/2026

## Contexto

El panel del mostrador (`sitio/panel.html`) permite al establecimiento avanzar
sus pedidos: empezar a preparar, marcar listo, entregar, cancelar. Se construyó
**con apoyo de IA** en la semana 8, y es la porción que la semana 9 presenta con
su cadena completa.

### Lo que hace difícil la decisión

**No hay autenticación.** Llega en una entrega posterior, y un sitio estático no
puede guardar un secreto: cualquier clave en `panel.js` se lee con F12. Eso
descarta el control de acceso como mecanismo de protección, y obliga a que la
seguridad venga de **qué transiciones existen**, no de quién las pide.

### El escenario que fuerza la decisión

<a id="escenario-motivador"></a>

**[ESC-03 — Gestión del estado de pedidos por el establecimiento](../arc42/arc42.md#esc-03)**,
cuya medida de respuesta es: *≤ 10 segundos y ≤ 3 interacciones, sin recargar la
página*.

Ese umbral empuja hacia menos pasos, y esa presión es justamente la que hay que
resistir en un punto concreto: el pago.

## Alternativas consideradas

### A — Validar las transiciones con condicionales en el servicio

Una cadena de `if` que comprueba el estado actual antes de cada cambio. Es lo
que propuso primero la herramienta.

**Descartada.** La regla queda repartida en varias ramas y no se puede leer de
un vistazo ni probar entera. Más importante: una regla que vive en el flujo de
control se amplía sin que nadie lo note, porque añadir un `elif` no parece un
cambio de política.

### B — Permitir cualquier transición y registrar la anterior

Guardar el historial y dejar que el mostrador corrija errores libremente.

**Descartada.** Si `pagado` fuera alcanzable desde el panel, cualquiera con un
navegador marcaría su pedido como pagado y retiraría comida sin pagarla. Sin
autenticación, «permitir y auditar» significa permitir.

### C — Máquina de estados declarada como dato, sin el pago dentro

Un diccionario que dice, por cada estado, a cuáles puede pasar.

## Decisión

**Se declara `TRANSICIONES_DEL_MOSTRADOR` como un dato**, en
[`app/pedidos/service.py`](../../backend/app/pedidos/service.py):

| Desde | Hacia |
|---|---|
| `pagado` | `en_preparacion`, `cancelado` |
| `en_preparacion` | `listo_para_recoger`, `cancelado` |
| `listo_para_recoger` | `entregado` |

**Lo que no está en esa tabla es la decisión**, y hay dos ausencias
deliberadas:

1. **`pendiente_pago` no es origen de ninguna transición.** El mostrador **no
   puede marcar un pedido como pagado**. Esa transición solo la dispara el
   webhook firmado de la pasarela ([ADR-0003](0003-estrategia-integracion.md)).
2. **`entregado` y `cancelado` son finales.** Volver atrás desde ellos es un
   error de registro, no una operación del negocio, y permitirlo haría imposible
   contar cuántos pedidos se sirvieron.

### La regla, escrita además en el contrato

El esquema de la petición usa `EstadoSolicitable` —un `enum` de cuatro valores—
y no `EstadoPedido` completo. Así la prohibición de marcar como pagado queda
**legible en `openapi.yaml` sin ejecutar nada**, y los dos modos de fallo se
separan por código:

- **`422`** — «ese estado no es algo que puedas pedir». El caso de `pagado`.
- **`409`** — «es pedible, pero no desde donde está el pedido», con el estado
  actual en el mensaje, porque quien atiende suele tener la pantalla
  desactualizada.

### De dónde salió el enum aparte

No de un criterio de diseño previo: **de una prueba de mutación**.

La primera versión usaba `EstadoPedido` en la petición. La prueba
`test_la_evolucion_compatible_no_se_bloquea[se quita un valor de un enum de
respuesta]` empezó a fallar, porque reutilizar el mismo `enum` en las dos
direcciones lo volvía bidireccional: quitarle un valor pasaba a ser incompatible
por la regla **I-7** además de por la I-8, y perdía la evolucionabilidad que la
política le reconoce a un `enum` de respuesta.

Separar `EstadoSolicitable` resolvió el problema de contrato y, de paso, puso la
regla de seguridad por escrito donde los consumidores la leen. **La mejora de
seguridad fue consecuencia, no intención.**

## Consecuencias

### Lo que mejora

- La regla se lee de un vistazo y se prueba entera.
- El panel solo ofrece los botones que el servidor va a aceptar. Un botón que
  siempre da error enseña a desconfiar de la pantalla.
- La validación vive en el servicio, no en el router: una regla de negocio en la
  capa HTTP solo protege a quien entra por HTTP.

### Lo que no resuelve

- **Cualquiera con el enlace puede mover los pedidos de cualquier
  establecimiento** ([V-10](../violaciones.md#v-10)). La máquina de estados
  acota el daño; no lo elimina. El panel lo avisa en su propia pantalla.
- Un establecimiento puede cancelar el pedido de otro. Solo la autenticación lo
  arregla.

### Cómo se sabrá si fue un error

Si el mostrador necesita con frecuencia una transición que la tabla no permite
—revertir una entrega mal marcada, por ejemplo—, la tabla está demasiado
cerrada y habrá que añadir esa transición **con su justificación**, no con un
`elif`.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Escenario | [ESC-03](../arc42/arc42.md#esc-03) · fila en [`aspectos.md`](../aspectos.md) |
| La máquina de estados | `app/pedidos/service.py` · `TRANSICIONES_DEL_MOSTRADOR` |
| El enum de la petición | `app/pedidos/contracts.py` · `EstadoSolicitable` |
| El contrato | [`openapi.yaml`](../api/openapi.yaml) · `POST /v1/pedidos/{pedido_id}/estado` |
| La interfaz | `sitio/panel.html`, `sitio/panel.js` |
| Pruebas | [`test_panel_mostrador.py`](../../backend/tests/test_panel_mostrador.py) — 15 casos |
| La prueba que sostiene la decisión | `::test_el_mostrador_no_puede_marcar_un_pedido_como_pagado` |
| Lo que no resuelve | [V-10](../violaciones.md#v-10) |
| Integración asíncrona que la condiciona | [ADR-0003](0003-estrategia-integracion.md) |
