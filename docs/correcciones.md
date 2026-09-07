# Correcciones del equipo a la retroalimentación docente

Documento de respuesta punto por punto a las observaciones de las semanas 1 a 5.
Estados: ✅ corregido · 🟡 parcial · ⏳ pendiente (con el motivo).

## Semanas 1 y 2

| Observación | Estado | Evidencia |
|---|---|---|
| Repositorio público y en la organización | ✅ | Se mantiene público en `ISCOUTB/AS_202620_PideUtb` |
| Ficha del problema en Markdown, no en PDF | ✅ | [`ficha_problema.md`](../ficha_problema.md); el PDF se eliminó |
| Declarar las dos tensiones de calidad en la ficha | ✅ | [`ficha_problema.md` § Atributos de calidad y tensiones](../ficha_problema.md): T-1 usabilidad ⟷ seguridad, T-2 rendimiento ⟷ simplicidad |
| Tabla de ocho columnas en `docs/aspectos.md` (era solo texto) | ✅ | [`docs/aspectos.md`](aspectos.md): ID · Aspecto · Escenario · Medida · C4 · ADR · Código · Pruebas |
| Plantilla arc42 en `docs/arc42/` | ✅ | [`docs/arc42/arc42.md`](arc42/arc42.md) |
| Carpetas `docs/adr/` y `docs/c4/` | ✅ | [`docs/adr/`](adr/) y [`docs/c4/`](c4/) (la carpeta estaba como `docs/C4/`, se renombró a minúsculas) |
| Anclas de los enlaces en `docs/aspectos.md` | ✅ | Se reemplazaron las anclas autogeneradas —inconsistentes: convivían `#105-esc-04--…` y `#105-esc-04-----…`— por anclas HTML explícitas (`<a id="esc-01"></a>` … `esc-05`). Además, mover `arc42.md` había roto **todas** las rutas relativas del README, de `docs/aspectos.md` y de los tres archivos de C4; quedaron corregidas |
| Registrar en `docs/ia.md` qué se rechazó de la IA y por qué | ✅ | [`docs/ia.md` § Qué se rechazó y por qué](ia.md) |
| Repartir la contribución entre los integrantes | ⏳ | Depende del equipo, no de un cambio en el repositorio. Historial actual: `daniarriet` 23 commits, `Santiago Cuesta` 11, `ruddy2000utb-droid` 2 |

## Semana 3

| Observación | Estado | Evidencia |
|---|---|---|
| Ligar arc42 §4 a ESC-01/02/03 con tácticas por escenario | ✅ | [§4.3 motivación por escenario](arc42/arc42.md#seccion-4) reescrita con una fila por escenario priorizado y umbral, y nueva [§4.4 tácticas por escenario](arc42/arc42.md#tacticas-por-escenario) |
| Rehacer la matriz comparativa con filas por escenario | ✅ | [`docs/comparativa-arquitectura.md` § Matriz por escenario](comparativa-arquitectura.md): una fila por escenario, con qué mejora y qué empeora en cada estilo, y una fila de balance |
| Enlazar el ADR 0001 desde `docs/aspectos.md` y desde el escenario que lo motiva | ✅ | Columna ADR de la tabla de aspectos, y sección Trazabilidad del [ADR-0001](adr/0001-estilo-arquitectonico.md), que nombra ESC-01 como escenario motivador |
| Workflow en `.github/workflows/` que ejecute `pytest`, con run en verde | ✅ | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — `pytest` en Python 3.11 y 3.12, en cada push y pull request. **Run en verde:** [Actions run #3](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534) |
| Mover `arc42.md` a `docs/arc42/` y el C4 a `docs/c4/` | ✅ | Ver semanas 1 y 2 |

## Semana 4

| Observación | Estado | Evidencia |
|---|---|---|
| Diagramas C4 como código en `docs/c4/` | ✅ | [Nivel 1](c4/nivel1-contexto.md), [Nivel 2](c4/nivel2-contenedores.md), [Nivel 3](c4/nivel3-modulos.md), todos en Mermaid |
| Verificar que los contenedores coincidan con `backend/app` | ✅ | El nivel 3 lista `pedidos`, `menu`, `pagos` y `usuarios`, que son exactamente los paquetes existentes en `backend/app/` |
| Completar la tabla de aspectos con ID, C4, ADR, Código y Pruebas | ✅ | [`docs/aspectos.md`](aspectos.md) |
| Añadir al ADR la trazabilidad (commit que lo implementa y pruebas) | ✅ | [ADR-0001 § Trazabilidad](adr/0001-estilo-arquitectonico.md): commits `b5f0310` y `2e165bb`, archivos de código y las tres pruebas de `test_pedidos.py` |
| No versionar el entorno virtual `.venv-1` | ✅ | Ya no hay archivos de entorno virtual rastreados; `.gitignore` cubre `.venv/` y `.venv-*/` |
| Ejecutar las pruebas en CI y dejar el enlace al run en verde | ✅ | **Run en verde sobre `master`:** [Actions run #3](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534) — commit `ae52cca`, 5 pruebas en Python 3.11 y 3.12, conclusión `success` |
| Glosario y secciones 1-6, 9, 10 y 12 visibles en `docs/arc42/` | ✅ | Todas presentes en [`docs/arc42/arc42.md`](arc42/arc42.md) |

## Semana 5 · Primer corte

| Observación | Estado | Evidencia |
|---|---|---|
| Documentar la restricción asignada y su diagnóstico | 🟡 | [`docs/restriccion-s5.md`](restriccion-s5.md) §§ 1-2. El diagnóstico del punto de medición está hecho; **el enunciado de la restricción asignada debe transcribirlo el equipo**: no está registrado en ningún punto del repositorio y no se documenta una restricción supuesta |
| Medir una línea base | ✅ | [`docs/restriccion-s5.md` §3](restriccion-s5.md): 300 peticiones a `POST /pedidos` — p50 2,85 ms, **p95 3,32 ms**. Instrumento reproducible: `backend/scripts/medir_linea_base.py` |
| Cubrir el cambio con una prueba en CI | ✅ | `backend/tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral`, ejecutada en verde por el workflow ([run #3](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534)) |
| Registrar el ADR del reto | ⏳ | Será `docs/adr/0002-*.md`; depende de la restricción asignada |
| Implementar el cambio y contrastarlo con el umbral | ⏳ | [`docs/restriccion-s5.md`](restriccion-s5.md) §§ 5-6, con la tabla de contraste ya preparada |
| Completar la cadena de ocho columnas en `docs/aspectos.md` | ✅ | Completa de punta a punta para ESC-01; ESC-02 a ESC-05 tienen escenario, C4 y ADR, y quedan marcadas ⏳ hasta que existan los módulos `pagos` y `usuarios` |
| Organizar arc42 y C4 en las carpetas exigidas | ✅ | `docs/arc42/` y `docs/c4/` |
| Registrar el uso de IA de S5 | ✅ | [`docs/ia.md` § Uso de IA en la quinta entrega](ia.md), con la tabla de rechazos |
| Retirar `.venv-1/` del repositorio | ✅ | Ver semana 4 |
| Crear la etiqueta `corte-1` sobre el commit correcto | ⏳ | **Decisión del equipo.** El docente indicó crearla sobre el commit de la próxima entrega. No se creó sobre trabajo posterior al cierre porque etiquetarlo como si fuera la entrega del corte sería incorrecto |
| Documento de correcciones a la revisión preliminar | ✅ | Este documento |

## Evidencia de integración continua

El pipeline [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) ejecuta la
suite completa (`pytest`, 5 pruebas) en Python 3.11 y 3.12 en cada push y cada
pull request.

| Run | Rama | Commit | Evento | Resultado |
|---|---|---|---|---|
| [#3](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534) | `master` | `ae52cca` | push (merge de las correcciones) | ✅ success |
| [#4](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160449532) | `rama-santiago` | `61f31ec` | push | ✅ success |
| [#2](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160277327) | rama de correcciones | `61f31ec` | pull request | ✅ success |
| [#1](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160100344) | rama de correcciones | `61f31ec` | push | ✅ success |

El run de referencia para la entrega es el **#3**, porque corresponde al estado
de `master` después de integrar las correcciones. El historial completo está en
la [pestaña Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).

## Resumen

De las observaciones acumuladas, quedan tres pendientes y ninguna es un
cambio de archivos: transcribir la restricción asignada por el docente,
registrar el ADR del reto y ejecutar el cambio que responde a ella, y crear la
etiqueta `corte-1` sobre el commit de la próxima entrega. El reparto de
contribución depende de que cada integrante haga sus propios commits.
