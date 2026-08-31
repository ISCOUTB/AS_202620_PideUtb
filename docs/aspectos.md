# Aspectos del proyecto

## Usabilidad

El sistema debe ser fácil de utilizar tanto para los estudiantes como
para los establecimientos de comida del campus.

Para los estudiantes, el proceso de consultar los establecimientos,
revisar los menús y precios, realizar un pedido y presentar el código de
compra debe ser claro y sencillo.

Para los establecimientos, la visualización y gestión de los pedidos
también debe realizarse de manera organizada, evitando pasos
innecesarios.

La usabilidad es el atributo de calidad prioritario porque uno de los
objetivos principales del proyecto es reducir el tiempo que los
estudiantes deben dedicar a realizar y recoger sus compras.

### Escenarios relacionados

  ------------------------------------------------------------------------------------------------------------------------------------
  Escenario                                                                                        Relación con usabilidad
  ------------------------------------------------------------------------------------------------ -----------------------------------
  [ESC-01 --- Primer pedido de un estudiante                                                       Evalúa la facilidad de aprendizaje
  nuevo](../arc42.md#102-esc-01-----primer-pedido-de-un-estudiante-nuevo)                             y la claridad del flujo inicial.

  [ESC-02 --- Pedido de un estudiante recurrente en hora                                           Evalúa la eficiencia de uso durante
  pico](../arc42.md#103-esc-02-----pedido-de-un-estudiante-recurrente-en-hora-pico)                   una situación de alta demanda.

  [ESC-03 --- Gestión del estado de pedidos por el                                                 Evalúa la facilidad y rapidez de
  establecimiento](../arc42.md#104-esc-03-----gestión-del-estado-de-pedidos-por-el-establecimiento)   uso del panel del establecimiento.

  [ESC-05 --- Error en el proceso de pago](../arc42.md#106-esc-05-----error-en-el-proceso-de-pago)    Evalúa la claridad del manejo de
                                                                                                   errores y la posibilidad de
                                                                                                   reintentar sin perder el pedido.
  ------------------------------------------------------------------------------------------------------------------------------------

## Confiabilidad

La confiabilidad es importante porque los pedidos, pagos y códigos deben
mantenerse correctamente asociados para evitar errores durante la
entrega.

### Escenario relacionado

  ------------------------------------------------------------------------------------------------------------
  Escenario                                                                Relación con confiabilidad
  ------------------------------------------------------------------------ -----------------------------------
  [ESC-04 --- Verificación del código de                                   Busca garantizar que el código
  recogida](../arc42.md#105-esc-04-----verificación-del-código-de-recogida)   corresponda al pedido y no pueda
                                                                           reutilizarse después de una
                                                                           entrega.

  ------------------------------------------------------------------------------------------------------------

## Seguridad

La seguridad es importante para proteger la información del sistema y
evitar usos no autorizados de los pedidos y mecanismos de entrega.

### Escenario relacionado

  ------------------------------------------------------------------------------------------------------------
  Escenario                                                                Relación con seguridad
  ------------------------------------------------------------------------ -----------------------------------
  [ESC-04 --- Verificación del código de                                   La validación del código ayuda a
  recogida](../arc42.md#105-esc-04--verificación-del-código-de-recogida)   impedir la reutilización no
                                                                           autorizada de un pedido ya
                                                                           entregado.

  ------------------------------------------------------------------------------------------------------------

## Disponibilidad

La disponibilidad es importante porque PideUTB debe poder utilizarse
especialmente durante los horarios de mayor demanda.

### Escenario relacionado

  --------------------------------------------------------------------------------------------------------------------
  Escenario                                                                        Relación con disponibilidad
  -------------------------------------------------------------------------------- -----------------------------------
  [ESC-02 --- Pedido de un estudiante recurrente en hora                           Considera el funcionamiento del
  pico](../arc42.md#103-esc-02--pedido-de-un-estudiante-recurrente-en-hora-pico)   sistema durante una situación de
                                                                                   posible alta concurrencia.

  --------------------------------------------------------------------------------------------------------------------

## Rendimiento

El rendimiento es importante para evitar que la plataforma introduzca
nuevos tiempos de espera.

### Escenarios relacionados

  ------------------------------------------------------------------------------------------------------------------------------------
  Escenario                                                                                        Relación con rendimiento
  ------------------------------------------------------------------------------------------------ -----------------------------------
  [ESC-02 --- Pedido de un estudiante recurrente en hora                                           Establece un tiempo objetivo para
  pico](../arc42.md#103-esc-02--pedido-de-un-estudiante-recurrente-en-hora-pico)                   completar el proceso de pedido.

  [ESC-03 --- Gestión del estado de pedidos por el                                                 Establece un tiempo objetivo para
  establecimiento](../arc42.md#104-esc-03--gestión-del-estado-de-pedidos-por-el-establecimiento)   actualizar el estado de un pedido.

  [ESC-04 --- Verificación del código de                                                           Establece un tiempo objetivo para
  recogida](../arc42.md#105-esc-04--verificación-del-código-de-recogida)                           validar el código.
  ------------------------------------------------------------------------------------------------------------------------------------


## Tabla de aspectos (trazabilidad completa)

> Esta tabla conecta cada aspecto con un escenario concreto, la táctica
> arquitectónica usada para atenderlo y la prueba que verifica que
> efectivamente se cumple. **En esta entrega solo la fila de
> Usabilidad está completa hasta la columna "Prueba"**; las demás
> filas se irán completando en próximas entregas a medida que se
> implementen los módulos de los que dependen (`pagos`, `usuarios`).

| Aspecto | Escenario | Estímulo → Respuesta | Medida de respuesta | Táctica arquitectónica | Prueba |
|---|---|---|---|---|---|
| **Usabilidad** | [ESC-01](../arc42.md#102-esc-01-----primer-pedido-de-un-usuario-nuevo) — Primer pedido de un usuario nuevo | Usuario nuevo (estudiante o profesor) intenta consultar un establecimiento y crear su primer pedido → lo logra sin ayuda externa, con un único request mínimo (`establecimiento_id`, `item_id`, `cantidad`) | Menos de 3 minutos, sin errores de navegación (medida definida en arc42 §10.2) | Separación de responsabilidades por módulo: `menu.service` valida disponibilidad y precio, `pedidos.service` solo orquesta esa llamada y arma el pedido. Esto permite endpoints simples y mensajes de error específicos (`404` ítem no existe, `409` no disponible) en vez de errores genéricos que confundirían al usuario nuevo | `backend/tests/test_pedidos.py::test_crear_pedido_exitoso`, `::test_crear_pedido_item_no_encontrado` y `::test_crear_pedido_item_no_disponible` — verifican que el flujo completo responde `201` con los datos del pedido, y que un ítem inválido responde con un error claro y no un `500` |
| Confiabilidad | [ESC-04](../arc42.md#105-esc-04-----verificación-del-código-de-recogida) — Verificación del código de recogida | — | — | — | *Pendiente — depende del módulo `pagos` (próxima entrega)* |
| Seguridad | [ESC-04](../arc42.md#105-esc-04-----verificación-del-código-de-recogida) — Verificación del código de recogida | — | — | — | *Pendiente — depende del módulo `pagos`* |
| Disponibilidad | [ESC-02](../arc42.md#103-esc-02-----pedido-de-un-usuario-recurrente-en-hora-pico) — Pedido en hora pico | — | — | — | *Pendiente — requiere prueba de carga* |
| Rendimiento | ESC-02, ESC-03, ESC-04 | — | — | — | *Pendiente* |


