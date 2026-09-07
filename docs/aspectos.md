# Aspectos de arquitectura — PideUTB

Este documento es el **índice de trazabilidad** del proyecto: conecta cada
atributo de calidad con el escenario que lo hace verificable, el diagrama C4
donde se ve la estructura que lo soporta, el ADR que justifica esa estructura,
el código que la implementa y la prueba automatizada que la verifica.

- Escenarios completos (seis partes): [`arc42.md` §10](arc42/arc42.md#arbol-utilidad)
- Tácticas por escenario: [`arc42.md` §4.5](arc42/arc42.md#tacticas-por-escenario)
- Decisiones: [`docs/adr/`](adr/)
- Diagramas: [`docs/c4/`](c4/)

## Tabla de aspectos (8 columnas)

| ID | Aspecto de calidad | Escenario | Medida de respuesta (umbral) | C4 | ADR | Código | Pruebas |
|---|---|---|---|---|---|---|---|
| **ESC-01** | Usabilidad *(prioritario)* | [Primer pedido de un usuario nuevo](arc42/arc42.md#esc-01) | Flujo completo en **< 3 min**, sin errores de navegación | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | `backend/app/pedidos/router.py:9` (`POST /pedidos`), `backend/app/pedidos/service.py`, `backend/app/menu/service.py` | `backend/tests/test_pedidos.py::test_crear_pedido_exitoso`, `::test_crear_pedido_item_no_encontrado`, `::test_crear_pedido_item_no_disponible` ✅ |
| **ESC-02** | Disponibilidad · Rendimiento | [Pedido de un usuario recurrente en hora pico](arc42/arc42.md#esc-02) | **< 2 min** en al menos el **90 %** de los intentos | [N2 — contenedores](c4/nivel2-contenedores.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | `backend/app/pedidos/` (flujo base implementado; falta reúso de datos del usuario) | ⏳ Pendiente — requiere prueba de carga (S6) |
| **ESC-03** | Usabilidad · Rendimiento | [Gestión del estado de pedidos por el establecimiento](arc42/arc42.md#esc-03) | **≤ 10 s** y **≤ 3 interacciones**, sin recargar la página | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | ⏳ Pendiente — panel del establecimiento (S6) | ⏳ Pendiente |
| **ESC-04** | Confiabilidad · Seguridad | [Verificación del código de recogida](arc42/arc42.md#esc-04) | Validación en **< 2 s**; rechazo del **100 %** de reutilizaciones | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | ⏳ Pendiente — módulo `backend/app/pagos/` (vacío) | ⏳ Pendiente |
| **ESC-05** | Usabilidad (manejo de errores) | [Error en el proceso de pago](arc42/arc42.md#esc-05) | Mensaje en **< 3 s**; pedido conservado en el **100 %** de los casos | [N2 — contenedores](c4/nivel2-contenedores.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | ⏳ Pendiente — integración Wompi Sandbox (S6) | ⏳ Pendiente |

**Leyenda:** ✅ verificado en CI · ⏳ pendiente en la entrega actual.

Estado a la fecha: la cadena de trazabilidad está **completa de punta a punta
para ESC-01** (escenario → C4 → ADR → código → prueba en verde en CI). Las
demás filas tienen escenario, C4 y ADR, y quedan a la espera de los módulos
`pagos` y `usuarios`.

## Por qué estos atributos

### Usabilidad (prioritario)

El sistema debe ser fácil de usar tanto para los usuarios (estudiantes y
profesores) como para los establecimientos. Para el usuario, consultar
establecimientos, revisar menús y precios, hacer un pedido y presentar el
código debe ser claro y sencillo; para el establecimiento, la gestión de
pedidos debe evitar pasos innecesarios. Es el atributo prioritario porque el
objetivo central del proyecto es **reducir el tiempo** que se pierde haciendo
fila.

Escenarios: [ESC-01](arc42/arc42.md#esc-01) (facilidad de aprendizaje),
[ESC-02](arc42/arc42.md#esc-02) (eficiencia de uso en alta demanda),
[ESC-03](arc42/arc42.md#esc-03) (panel del establecimiento),
[ESC-05](arc42/arc42.md#esc-05) (claridad del manejo de errores).

### Confiabilidad

Pedidos, pagos y códigos deben mantenerse correctamente asociados para evitar
errores en la entrega. Escenario: [ESC-04](arc42/arc42.md#esc-04).

### Seguridad

Proteger la información del sistema y evitar usos no autorizados de los
pedidos y del mecanismo de entrega. La validación del código impide reutilizar
un pedido ya entregado. Escenario: [ESC-04](arc42/arc42.md#esc-04).

### Disponibilidad

PideUTB debe poder utilizarse especialmente en los horarios de mayor demanda.
Escenario: [ESC-02](arc42/arc42.md#esc-02).

### Rendimiento

La plataforma no debe introducir nuevos tiempos de espera. Escenarios:
[ESC-02](arc42/arc42.md#esc-02), [ESC-03](arc42/arc42.md#esc-03),
[ESC-04](arc42/arc42.md#esc-04).

## Tensiones de calidad

Las dos tensiones declaradas en la [ficha del problema](../ficha_problema.md)
y arbitradas en [ADR-0001](adr/0001-estilo-arquitectonico.md):

| Tensión | En conflicto | Cómo se resolvió |
|---|---|---|
| **T-1: Usabilidad vs. Seguridad** | ESC-01 (pedido en < 3 min, sin fricción) vs. ESC-04 (código no reutilizable, validación estricta) | Se privilegia la usabilidad en el flujo de compra y se concentra la validación estricta en el punto de entrega, no en cada paso del pedido |
| **T-2: Rendimiento/Disponibilidad vs. Simplicidad de construcción** | ESC-02 (hora pico, < 2 min en el 90 %) vs. el plazo y el tamaño del equipo (3 integrantes, sin presupuesto) | Monolito modular en un solo desplegable: se acepta menos margen de escalado independiente a cambio de entregar a tiempo, con módulos separados que permiten extraer un servicio después si ESC-02 lo exige |
