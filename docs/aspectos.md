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
| **ESC-02** | Disponibilidad · Rendimiento | [Pedido de un usuario recurrente en hora pico](arc42/arc42.md#esc-02) | **< 2 min** en al menos el **90 %** de los intentos | [N2 — contenedores](c4/nivel2-contenedores.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md), [**ADR-0004**](adr/0004-plataforma-de-despliegue.md) → [**ADR-0008**](adr/0008-despliegue-en-el-servidor-del-laboratorio.md) *(el arranque en frío que consumía ~42 de los 120 s desapareció)* | `backend/app/pedidos/` (flujo base; falta reúso de datos del usuario); `GET /metricas` publica el p95 de `POST /v1/pedidos`, que es la parte del presupuesto que controla el servidor | `tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral` ✅ *(línea base, no prueba de carga)* · `tests/test_observabilidad.py::test_las_metricas_reportan_la_operacion_ligada_a_esc02` ✅ |
| **ESC-03** | Usabilidad · Rendimiento | [Gestión del estado de pedidos por el establecimiento](arc42/arc42.md#esc-03) | **≤ 10 s** y **≤ 3 interacciones**, sin recargar la página | [N3 — módulos](c4/nivel3-modulos.md) | [**ADR-0005**](adr/0005-maquina-de-estados-del-mostrador.md) *(transiciones como dato; el escenario que lo motiva)*, [ADR-0002](adr/0002-propiedad-datos-establecimiento.md) *(dueño del estado)*, [ADR-0007](adr/0007-autenticacion-del-panel.md) *(quién puede avanzarlo)*, [**ADR-0010**](adr/0010-notificar-al-panel-por-sondeo.md) *(cómo se entera el panel, y el margen que consume)* | `backend/app/pedidos/service.py` (`TRANSICIONES_DEL_MOSTRADOR`, `avanzar_estado`), `app/autenticacion.py` (`establecimiento_que_puede_ver`), `GET /v1/pedidos` y `POST /v1/pedidos/{id}/estado`, `sitio/panel.html` y `sitio/panel.js` — el mostrador entra con su sesión, ve **su** cola y la avanza sin recargar | `tests/test_panel_mostrador.py` — **21 pruebas** del panel, su máquina de estados y su autorización ✅ · `tests/test_propiedad_datos.py::test_establecimiento_se_deriva_del_item_y_no_del_cliente`, `::test_pedido_en_establecimiento_inactivo_se_rechaza` ✅ · **Medición por capas:** [`evidencia-s9.md` §1.3](evidencia-s9.md) — ~0,7 s en caliente ✅. El **~43 s en frío** que lo incumplía desapareció con [ADR-0008](adr/0008-despliegue-en-el-servidor-del-laboratorio.md): los contenedores del laboratorio no duermen. · **Medido y corregido (S14):** la cadena completa consumía **8 320 ms** y dejaba **1,68 s** para la persona, así que el escenario **se incumplía** en el peor caso. Se bajó el sondeo a 5 000 ms → **4,68 s de margen** ✅. `scripts/medir_esc03.py` rehace la medición y falla si deja de cumplirse; `tests/test_escenarios_de_calidad.py` fija el intervalo por los dos lados ✅. Detalle en [arc42 §10.7](arc42/arc42.md#evaluacion) |
| **ESC-04** | Confiabilidad · Seguridad | [Verificación del código de canje](arc42/arc42.md#esc-04) | Validación en **< 2 s**; rechazo del **100 %** de reutilizaciones | [N3 — módulos](c4/nivel3-modulos.md) | [ADR-0001](adr/0001-estilo-arquitectonico.md), [ADR-0003](adr/0003-estrategia-integracion.md), [**ADR-0007**](adr/0007-autenticacion-del-panel.md) *(sin sesión no se sabe quién entrega)* · **modelo de amenazas:** [arc42 §8.7](arc42/arc42.md#amenazas) *(S-1 a E-4; el canje es E-3)* | `backend/app/pedidos/service.py` (`confirmar_pago` y generación con `secrets`; `avanzar_estado` exige el código al pasar a `entregado`, comparado con `compare_digest`), `app/pagos/service.py` | `tests/test_panel_mostrador.py::test_entregar_sin_el_codigo_no_se_puede`, `::test_el_codigo_no_se_puede_reutilizar`, `::test_el_codigo_se_acepta_en_minusculas_pero_no_con_otro_valor` ✅ · `tests/test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo`, `::test_el_codigo_de_canje_no_cambia_entre_reintentos` ✅ |
| **ESC-05** | Usabilidad (manejo de errores) | [Error en el proceso de pago](arc42/arc42.md#esc-05) | Mensaje en **< 3 s**; pedido conservado en el **100 %** de los casos | [N2 — contenedores](c4/nivel2-contenedores.md) | [**ADR-0003**](adr/0003-estrategia-integracion.md) *(escenario que lo motiva)* | `backend/app/pagos/` completo, `app/eventos.py`, `GET /v1/pedidos/{id}` | `tests/test_pagos.py::test_un_pago_rechazado_conserva_el_pedido`, `::test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable`, `::test_un_suscriptor_que_falla_no_tumba_el_cobro` ✅ |
| **CON-01** | Evolucionabilidad *(nuevo en S7)* | El contrato de API es la fuente única de verdad y un cambio incompatible no puede llegar a producción sin avisar | **0** cambios incompatibles no detectados; **20** casos negativos que deben seguir fallando | [N2 — contenedores](c4/nivel2-contenedores.md) *(protocolo y formato por flecha)* | [ADR-0003](adr/0003-estrategia-integracion.md), [política de versionado](api/politica-versionado.md) | [`docs/api/openapi.yaml`](api/openapi.yaml), [`asyncapi.yaml`](api/asyncapi.yaml), `backend/scripts/comparar_contratos.py` | `tests/test_contrato_api.py`, `tests/test_compatibilidad_contrato.py`, `tests/test_expectativas_consumidor.py` ✅ · Spectral y oasdiff en el job `contrato` |

**Leyenda:** ✅ verificado en CI · ⏳ pendiente en la entrega actual.

Estado a la fecha (S10): la cadena está **completa de punta a punta para los
cinco escenarios y CON-01** (escenario → C4 → ADR → código → prueba en verde en
CI). Lo que cerró en S9 y S10 fue el panel del mostrador con su máquina de
estados (ESC-03) y la validación del código en el punto de entrega (ESC-04),
que necesitaba saber **quién** entrega y por eso esperaba a la autenticación
([ADR-0007](adr/0007-autenticacion-del-panel.md)).

**Y la excepción que había dejó de existir.** Hasta la semana 10, ESC-03 no se
cumplía con el servicio frío: el umbral son 10 s y el arranque en frío de la
plataforma anterior estaba medido en 42,4 s. La medición por capas de
[`evidencia-s9.md` §1.3](evidencia-s9.md) lo separó —~0,7 s en caliente, ~43 s
en frío— y esos dos números llevaban semanas en el repositorio, en documentos
distintos, sin que una medición de una sola capa obligara a ponerlos juntos.

El término que lo incumplía **desapareció por construcción** con
[ADR-0008](adr/0008-despliegue-en-el-servidor-del-laboratorio.md): los
contenedores del servidor del laboratorio no se duermen. Queda **remedir el
escenario entero en el entorno nuevo**, que es trabajo de S14: hasta entonces lo
honesto es decir que el obstáculo conocido ya no está, no que el escenario esté
verificado allí.

ESC-02 tiene línea base medida y protegida por una prueba de regresión, pero no
prueba de carga.

**Las cinco filas ya no tienen ninguna celda «Código» o «Pruebas» vacía, ni
ninguna marca ⏳.** Lo que cerró ESC-04 y ESC-05 fue implementar el contexto
Pagos, que era
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
| **T-1: Usabilidad vs. Seguridad** | ESC-01 (pedido en < 3 min, sin fricción) vs. ESC-04 (código no reutilizable, validación estricta) | Se privilegia la usabilidad en el flujo de compra y se concentra la validación estricta en el punto de entrega, no en cada paso del pedido. **Implementado así en S10:** el código se exige en la transición a `entregado` y en ninguna otra, de modo que las tres transiciones anteriores no piden nada. Y se compara sin distinguir mayúsculas y recortando espacios, porque el código se dicta en voz alta en un mostrador: la tolerancia es a la caja de las letras, no al valor |
| **T-2: Rendimiento/Disponibilidad vs. Simplicidad de construcción** | ESC-02 (hora pico, < 2 min en el 90 %) vs. el plazo y el tamaño del equipo (3 integrantes, sin presupuesto) | Monolito modular en un solo desplegable: se acepta menos margen de escalado independiente a cambio de entregar a tiempo, con módulos separados que permiten extraer un servicio después si ESC-02 lo exige |
