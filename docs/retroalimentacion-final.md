# Retroalimentación final: qué se dijo, qué se decidió y qué cambió

Entrega del 27/11/2026. Aplica la retroalimentación de la sustentación final
(25/11/2026) y de la revisión entre pares. Cada recomendación tiene su origen, su
clasificación, su justificación técnica cuando no se aceptó entera, y el enlace a lo
que cambió: código, pruebas, ADR, diagramas y la construcción en verde.

## 1. Matriz de retroalimentación

| # | Recomendación recibida | Origen | Clasificación | Qué se hizo | ADR | Cambios |
|---|---|---|---|---|---|---|
| R-1 | Mejorar el diseño del frente, sobre todo la vista del mostrador | Sustentación final, jurado | **Aceptada** | La cola del mostrador pasa a ser un tablero de tres columnas por estado —por preparar, en preparación, listos— con la cuenta de cada una, los pedidos sin pagar punteados y sin botones, y los terminados plegados. Misma paleta, mismas tipografías y misma máquina de estados. Se tomó la estructura de los mockups del equipo, no su paleta ni sus funciones | [ADR-0016](adr/0016-canje-por-qr-y-tablero-del-mostrador.md) | [PR #55](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/55) · `6b97384`, `2b49cc1` |
| R-2 | Que los llamados que cambian el sistema vayan por `POST` | Sustentación final, jurado | **Aceptada — ya se cumplía** | Toda escritura va por `POST` o `DELETE` desde la 1.0.0 del contrato; los `GET` solo leen. Lo nuevo es una prueba que lo fija: toda ruta `GET` tiene que estar en una lista cerrada de lecturas, y el sitio no puede pedir por `GET` nada que no sea una de ellas | — (regla ya escrita en [ADR-0005](adr/0005-maquina-de-estados-del-mostrador.md) y en la política de versionado) | [PR #56](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/56) · `149af3e` · `backend/tests/test_metodos_http.py` |
| R-3 | Seguridad del pago: que el código de recogida no se repita | Sustentación final, jurado | **Aceptada — ya se cumplía** | El código se genera con `secrets` sobre 31 caracteres, la columna es `UNIQUE`, la confirmación es idempotente dentro de un `UPDATE ... WHERE estado = 'pendiente_pago'` —dos avisos del mismo pago no generan dos códigos— y `entregado` es final: el segundo canje no falla por el código sino porque ya no hay transición. La evidencia está en las pruebas que ya corrían | [ADR-0005](adr/0005-maquina-de-estados-del-mostrador.md) · [ADR-0017 §Contexto](adr/0017-devoluciones-aplazadas.md) | `tests/test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo` · `tests/test_panel_mostrador.py::test_el_codigo_no_se_puede_reutilizar` |
| R-4 | Seguridad del pago: que no se venda lo que no hay (sin stock) | Sustentación final, jurado | **Aceptada** | Inventario diario por producto: el mostrador fija cuántas unidades hay hoy, la carta lo muestra («Quedan 3», «Agotado»), la API rechaza con `409` el pedido que no alcanza —todo o nada entre sus líneas—, reserva al crear el pedido y devuelve al cancelarlo. `NULL` sigue significando sin control, así que nada de lo que había cambia. Contrato **6.1.0**, cambio aditivo | [ADR-0015](adr/0015-inventario-diario-por-producto.md) | [PR #57](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/57) · `9d7ce5a` · [PR #58](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/58) · `1c40dbf` (la pantalla del panel) · migración `017_inventario_diario.sql` · `tests/test_inventario_diario.py` |
| R-5 | Seguridad del pago: devoluciones | Sustentación final, jurado | **Aplazada** | Ver §3. La regla hoy queda escrita: un pedido pagado que el mostrador cancela se devuelve en caja, a mano, contra el código. El diseño de la devolución automática queda en el ADR para construirse cuando exista una pasarela real y una caja contra la que cuadrar | [ADR-0017](adr/0017-devoluciones-aplazadas.md) | [PR #56](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/56) · `149af3e` |
| R-6 | Inventario en tiempo real entre la app y el mostrador | Propuesta del equipo en la sustentación, a raíz de R-4 | **Aceptada en parte** | Lo que de verdad hacía falta era el inventario (R-4). El «tiempo real» ya lo da el sondeo de 5 s del panel y la carta que se recarga al entrar: no se añadió un WebSocket ni un canal nuevo, porque [ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md) ya midió que el sondeo cumple el umbral y no hay un segundo consumidor que lo justifique | [ADR-0015 §Alternativas](adr/0015-inventario-diario-por-producto.md) | Los mismos de R-4 |
| R-7 | Que el mostrador escanee un QR en vez de teclear el código | Propuesta del equipo, recogida por el jurado | **Aceptada** | El billete del cliente lleva el código también como QR, dibujado en el navegador con un port del generador de Python que ya tenía el repositorio; una prueba exige que las dos copias dibujen la misma matriz. El panel lo lee con `BarcodeDetector`, sin bibliotecas: desde la barra, entrega en una interacción; desde el diálogo, rellena el código. Donde el navegador no lo tenga, se teclea. La regla del servidor no cambia | [ADR-0016](adr/0016-canje-por-qr-y-tablero-del-mostrador.md) | [PR #55](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/55) · `sitio/qr.js` · `tests/test_qr.py::test_el_qr_del_sitio_dibuja_la_misma_matriz_que_python` |
| R-8 | Revisión entre pares | Grupo par, revisión cruzada | **Sin recomendaciones de cambio** | La revisión fue favorable y no dejó observaciones que exigieran cambios. Se deja constancia para que la matriz esté completa | — | — |

## 2. Clasificación, en resumen

| Clasificación | Recomendaciones |
|---|---|
| Aceptadas y construidas en esta entrega | R-1, R-4, R-7 |
| Aceptadas que ya se cumplían, y ahora una prueba las fija | R-2, R-3 |
| Aceptadas en parte | R-6 |
| Aplazadas, con motivo técnico y diseño escrito | R-5 |
| Rechazadas | Ninguna |

## 3. Justificaciones

### R-5, aplazada: por qué no se construye la devolución ahora

No es falta de tiempo. Las tres piezas que una devolución necesita no existen en este
despliegue, y construir la cuarta sin las tres sería una pantalla que promete algo que
no ocurre:

1. **La pasarela está en sandbox.** Wompi en modo de pruebas no mueve dinero; un
   reembolso automático no se puede comprobar, y en producción exige una cuenta de
   comercio real y credenciales de las que el proyecto no dispone.
2. **No hay cuentas de cliente**, y es una decisión ([arc42 §8.8](arc42/arc42.md#datos-personales)).
   Sin cuenta no hay a quién acreditar un saldo; la única devolución posible es a la
   pasarela, y eso devuelve al punto 1.
3. **No hay conciliación contable.** Una devolución es dinero que sale de una caja que
   lleva una persona; sin un cierre contra el que cuadrar, un reembolso automático es
   una cifra que nadie revisa.

Lo que sí se decidió es la regla vigente —devolver en caja contra el código— y el
diseño completo de la devolución automática (estado `reembolso_pendiente`, tabla
`reembolsos` en Pagos, disparador en la cancelación, columna en el tablero y la
prueba que lo vigila), en [ADR-0017](adr/0017-devoluciones-aplazadas.md). Queda
anotado como deuda **D-05** en [arc42 §11.2](arc42/arc42.md#deuda-tecnica).

### R-6, aceptada en parte: por qué no hay «tiempo real» nuevo

Un WebSocket o un canal de eventos entre la carta y el mostrador habría sido un
mecanismo más para mantener, con sus modos de fallo propios, para una información
que ya viaja: el panel sondea cada 5 s ([ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md)
midió que cumple ESC-03) y la carta pide el catálogo al abrirse y antes de pagar. El
dato nuevo —`unidades_hoy`— entra por esas dos vías sin añadir ninguna. Si algún día
hubiera un segundo consumidor del inventario, el canal de eventos ya existe como
costura con contrato.

### R-2 y R-3, aceptadas que ya se cumplían: por qué igual hay cambios

Que algo se cumpla no basta si nada impide que deje de cumplirse. Para R-2 se añadió
`test_metodos_http.py`: una ruta `GET` nueva obliga a declararla como lectura, y el
sitio no puede inventarse una escritura por `GET`. Para R-3 la evidencia ya estaba en
las pruebas; lo que faltaba era tenerla reunida en un sitio, y está en el contexto de
ADR-0017.

## 4. Código y pruebas modificados

| Cambio | PR | Commits | Pruebas nuevas o tocadas |
|---|---|---|---|
| Tablero del mostrador, QR en el billete y lectura con cámara | [#55](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/55) | `6b97384`, `2b49cc1` | `test_qr.py` (paridad JS/Python); las de `test_escenarios_de_calidad.py` que inspeccionan el sitio siguen pasando sin cambios; los recorridos de navegador del mostrador pasan sin cambios |
| Prueba de métodos HTTP y ADR de devoluciones | [#56](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/56) | `149af3e` | `test_metodos_http.py` (5 pruebas) |
| Inventario diario por producto: API, migración, contrato 6.1.0 y carta | [#57](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/57) | `9d7ce5a` | `test_inventario_diario.py`, `test_migraciones.py` (huella de `017`), `test_contrato_api.py` y `test_compatibilidad_contrato.py` contra la 6.1.0, `test_expectativas_consumidor.py` |
| El mostrador fija el inventario desde el panel | [#58](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/58) | `1c40dbf` | Las de `test_escenarios_de_calidad.py` y `test_metodos_http.py` que inspeccionan `panel.js` |
| arc42, C4, aspectos, README y este informe | [#59](https://github.com/ISCOUTB/AS_202620_PideUtb/pull/59) | `4b52afa` y los que siguen en esa PR | `test_evidencia.py` (citas de línea del arc42, recalculadas) |

Pruebas del backend: **800** (eran 763 antes de esta entrega). Recorridos
con navegador: 68, sin cambios.

## 5. ADR

| ADR | Estado | Qué decide |
|---|---|---|
| [ADR-0015](adr/0015-inventario-diario-por-producto.md) | Aceptada, nueva | Inventario diario por producto: quién lo fija, cuándo se reserva y se libera, y la limitación de los pendientes de pago |
| [ADR-0016](adr/0016-canje-por-qr-y-tablero-del-mostrador.md) | Aceptada, nueva | QR en el billete, lectura con la cámara y tablero por estado |
| [ADR-0017](adr/0017-devoluciones-aplazadas.md) | **Aplazada**, nueva | Por qué no hay devolución automática, cuál es la regla hoy y cómo se haría |
| [ADR-0005](adr/0005-maquina-de-estados-del-mostrador.md) | Aceptada, sin cambios | Sigue siendo la regla del canje; ADR-0016 añade una forma de presentar el código, no de validarlo |
| [ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md) | Aceptada, sin cambios | Es la razón por la que R-6 no añadió un canal nuevo |

Ninguna decisión anterior queda *superseded*: las tres nuevas añaden, no reemplazan.
El índice completo está en [arc42 §9](arc42/arc42.md#seccion-9).

## 6. Diagramas y arc42

| Documento | Qué cambió |
|---|---|
| [arc42 §5.3](arc42/arc42.md#responsabilidad-modulos) | `menu` también escribe el inventario, por la misma regla de propiedad |
| [arc42 §6.2](arc42/arc42.md#runtime-crear-pedido) | La reserva de unidades dentro de crear un pedido, con su `409` |
| [arc42 §6.8](arc42/arc42.md#runtime-entregar) | Nuevo: entregar tecleando o leyendo el QR; la regla del servidor es la misma |
| [arc42 §9](arc42/arc42.md#seccion-9) | ADR-0015, 0016 y 0017 en el índice |
| [arc42 §10.5](arc42/arc42.md#esc-04) | El estímulo de ESC-04 tiene dos formas; la medida no cambia |
| [arc42 §11.2](arc42/arc42.md#deuda-tecnica) | D-05 (devoluciones) y D-06 (pendientes de pago retienen unidades) |
| [C4 nivel 2](c4/nivel2-contenedores.md) | El frontend dibuja y lee el QR; el personal fija el inventario y entrega escaneando |
| [C4 nivel 3](c4/nivel3-modulos.md) | Flecha `pedidos → menu` para `reservar_unidades` / `liberar_unidades` |
| [Tabla de aspectos](aspectos.md) | ESC-03 y ESC-04 enlazan a los ADR nuevos |

## 7. Evidencia de ausencia de regresiones

Construcción de `master` con todo el código de esta entrega fusionado (`b10213c`, tras la
PR #58): [run 46029364619](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/46029364619),
en verde. Las anteriores, una por fusión: [`cfb4e60`](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/46028592156)
tras #57 y [`4546d24`](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/46027730720)
tras #55. Producción sirve el contrato 6.1.0 desde la fusión de #57.

Las 16 comprobaciones de cada PR —pytest en dos versiones de Python, contrato,
dependencias, imagen del sitio, recorrido con navegador y SonarCloud— pasaron antes
de fusionar cada una. El Quality Gate de SonarCloud pidió dos cosas en la PR #55 (una
promesa sin manejar y un selector duplicado) y se corrigieron en `2b49cc1` antes de
fusionar.

## 8. Retrospectiva

### Qué funcionó

- **Atar cada decisión a una prueba.** La retroalimentación de hoy se aplicó sobre un
  sistema con más de 760 pruebas y ninguna se rompió sin que la construcción lo
  dijera. Cuando el inventario tocó el contrato, `test_contrato_api.py` obligó a
  escribir la 6.1.0 antes de que el código la implementara.
- **El contrato versionado.** La 6.1.0 entró como cambio aditivo y el consumidor
  declarado no tuvo que tocarse: `oasdiff` lo confirmó en CI.
- **Decir que no con números.** No extraer un servicio, no meter un WebSocket, no
  construir la devolución: cada «no» de esta entrega tiene un motivo que se puede
  comprobar, y eso es lo que el jurado aceptó como respuesta.

### Qué no funcionó

- **Las pruebas de contrato no ven la pantalla.** Los seis defectos de las semanas 15
  y 16 y la observación de hoy sobre el mostrador son del mismo tipo: todo verde, y la
  pantalla mal. Los recorridos de navegador llegaron tarde, y el diseño del mostrador
  nunca se miró con quien lo usa.
- **El catálogo prometía lo que no podía cumplir.** Un producto «disponible» sin
  unidades es una promesa, y en hora pico se rompe. Se vio en la sustentación, no antes.
- **Las citas de línea en la documentación.** Cada cambio en el arc42 rompe siete
  citas numéricas y hay que recalcularlas; hoy volvió a pasar. Son exactas, pero
  frágiles.

### Qué haríamos distinto

- Dibujar el mostrador con quien lo atiende en la semana 10, cuando apareció el panel,
  y no después de la sustentación.
- Poner el inventario en el modelo desde la primera carta: era una columna y una regla,
  y costó más explicar su ausencia que haberla tenido.
- Tener el despliegue local igual al de producción desde la primera semana (D-01): la
  mayoría de lo que falló en el semestre fue «la prueba y el entorno real no recorren
  el mismo camino».

### Una lección por integrante

Las tres salen de hechos del proyecto, y cada integrante firma la suya en el documento
de entrega.

- **Integrante que llevó el despliegue y las migraciones.** La caída del 18/10: una
  migración editada después de aplicada dejó la API en bucle de reinicio media hora.
  Lección: *lo que solo se comprueba en producción, falla en producción*. Las huellas
  de las migraciones viven en CI desde entonces, y hoy la `017` entró con la suya.
- **Integrante que llevó el frente y el mostrador.** El rediseño destapó seis defectos
  que 761 pruebas no veían, y la sustentación destapó uno más. Lección: *una pantalla
  se prueba con un navegador y con la persona que la usa, no con el contrato*. El
  tablero de hoy se dibujó primero y se escribió después.
- **Integrante que llevó pagos y pedidos.** ESC-03 se incumplía con 8 s de sondeo y
  nadie lo supo hasta medirlo; el inventario faltaba y nadie lo supo hasta que lo
  preguntaron. Lección: *una afirmación de calidad sin medida es una opinión*. Por eso
  la devolución no se construyó: no había forma de medir que funcionara.
