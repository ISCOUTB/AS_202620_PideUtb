# Aspectos de arquitectura — PideUTB

Este documento es el **índice de trazabilidad** del proyecto: conecta cada
atributo de calidad con el escenario que lo hace verificable, el diagrama C4
donde se ve la estructura que lo soporta, el ADR que justifica esa estructura,
el código que la implementa y la prueba automatizada que la verifica.

- Escenarios completos (seis partes): [`arc42.md` §10](arc42/arc42.md#arbol-utilidad)
- Contextos delimitados y propiedad de datos: [`docs/ddd-contextos.md`](ddd-contextos.md)
- Violaciones detectadas y plan de corrección: [`docs/violaciones.md`](violaciones.md)
- Tácticas por escenario: [`arc42.md` §4.5](arc42/arc42.md#tacticas-por-escenario)
- Decisiones: [`docs/adr/`](adr/)
- Diagramas: [`docs/c4/`](c4/)

## Tabla de aspectos (8 columnas)

| ID | Aspecto de calidad | Escenario | Medida de respuesta (umbral) | C4 | ADR | Código | Pruebas |
|---|---|---|---|---|---|---|---|
| **ESC-01** | Usabilidad *(prioritario)* | [Primer pedido de un usuario nuevo](arc42/arc42.md#esc-01) | Flujo completo en **< 3 min**, sin errores de navegación | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md), [ADR-0002](adr/0002-propiedad-datos-establecimiento.md) | `backend/app/pedidos/router.py` (`POST /pedidos`), `pedidos/service.py`, `menu/service.py` | `tests/test_pedidos.py::test_crear_pedido_exitoso`, `::test_crear_pedido_item_no_encontrado`, `::test_crear_pedido_item_no_disponible` ✅ |
| **ESC-02** | Disponibilidad · Rendimiento | [Pedido de un usuario recurrente en hora pico](arc42/arc42.md#esc-02) | **< 2 min** en al menos el **90 %** de los intentos | [N2 — contenedores](c4/nivel2-contenedores.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md) | `backend/app/pedidos/` (flujo base; falta reúso de datos del usuario) | `tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral` ✅ *(línea base, no prueba de carga)* |
| **ESC-03** | Usabilidad · Rendimiento | [Gestión del estado de pedidos por el establecimiento](arc42/arc42.md#esc-03) | **≤ 10 s** y **≤ 3 interacciones**, sin recargar la página | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0002](adr/0002-propiedad-datos-establecimiento.md) | `backend/app/usuarios/service.py`, `pedidos/service.py` — el pedido ya se asigna al establecimiento correcto y solo si opera | `tests/test_propiedad_datos.py::test_establecimiento_se_deriva_del_item_y_no_del_cliente`, `::test_pedido_en_establecimiento_inactivo_se_rechaza` ✅ · panel ⏳ |
| **ESC-04** | Confiabilidad · Seguridad | [Verificación del código de canje](arc42/arc42.md#esc-04) | Validación en **< 2 s**; rechazo del **100 %** de reutilizaciones | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md), [ADR-0003](adr/0003-estrategia-integracion.md) | `backend/app/pedidos/service.py` (`confirmar_pago`, generación con `secrets`), `app/pagos/service.py` | `tests/test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo`, `::test_el_codigo_de_canje_no_cambia_entre_reintentos` ✅ · validación en el punto de entrega ⏳ |
| **ESC-05** | Usabilidad (manejo de errores) | [Error en el proceso de pago](arc42/arc42.md#esc-05) | Mensaje en **< 3 s**; pedido conservado en el **100 %** de los casos | [N2 — contenedores](c4/nivel2-contenedores.md) | [**ADR-0003**](adr/0003-estrategia-integracion.md) *(escenario que lo motiva)* | `backend/app/pagos/` completo, `app/eventos.py`, `GET /v1/pedidos/{id}` | `tests/test_pagos.py::test_un_pago_rechazado_conserva_el_pedido`, `::test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable`, `::test_un_suscriptor_que_falla_no_tumba_el_cobro` ✅ |
| **CON-01** | Evolucionabilidad *(nuevo en S7)* | El contrato de API es la fuente única de verdad y un cambio incompatible no puede llegar a producción sin avisar | **0** cambios incompatibles no detectados; **20** casos negativos que deben seguir fallando | [N2 — contenedores](c4/nivel2-contenedores.md) *(protocolo y formato por flecha)* | [ADR-0003](adr/0003-estrategia-integracion.md), [política de versionado](api/politica-versionado.md) | [`docs/api/openapi.yaml`](api/openapi.yaml), [`asyncapi.yaml`](api/asyncapi.yaml), `backend/scripts/comparar_contratos.py` | `tests/test_contrato_api.py`, `tests/test_compatibilidad_contrato.py`, `tests/test_expectativas_consumidor.py` ✅ · Spectral y oasdiff en el job `contrato` |

**Leyenda:** ✅ verificado en CI · ⏳ pendiente en la entrega actual.

Estado a la fecha (S7): la cadena está **completa de punta a punta para ESC-01,
ESC-03, ESC-05 y CON-01** (escenario → C4 → ADR → código → prueba en verde en
CI). De ESC-03 queda pendiente el panel del establecimiento y de ESC-04 la
validación del código en el punto de entrega; ambos son trabajo futuro, no
huecos de trazabilidad. ESC-02 tiene línea base medida y protegida por una
prueba de regresión, pero no prueba de carga.

**Las cinco filas ya no tienen ninguna celda «Código» o «Pruebas» vacía.** Lo
que cerró ESC-04 y ESC-05 fue implementar el contexto Pagos, que era
precisamente lo que las bloqueaba desde S5.

Las violaciones de propiedad de datos detectadas en la auditoría de modularidad
y su plan de corrección están en [`docs/violaciones.md`](violaciones.md).

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
