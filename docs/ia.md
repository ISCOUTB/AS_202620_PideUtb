
# Inteligencia Artificial

La inteligencia artificial será utilizada como una herramienta de apoyo durante el desarrollo del proyecto.

Los integrantes del equipo podrán utilizar herramientas de IA para consultar conceptos relacionados con programación e arquitectura de software, resolver dudas, obtener ideas para el diseño del sistema y recibir apoyo durante la revisión y corrección del código.

La información obtenida mediante estas herramientas será revisada y comprendida por los integrantes antes de incorporarla al proyecto. La IA será utilizada como apoyo al trabajo del equipo y no como sustituto de su desarrollo y toma de decisiones.

## Uso de IA en la segunda entrega

**Herramienta utilizada:** Claude (Anthropic).

Para esta entrega, Claude fue utilizado principalmente como apoyo en dos aspectos:

- **Organización de la documentación:** se usó Claude para estructurar y ordenar el contenido de los documentos del proyecto (como los aspectos de arquitectura), asegurando coherencia, claridad y una redacción adecuada conforme a lo trabajado por el equipo.
- **Generación de esquemas y mapas conceptuales:** se utilizó Claude como apoyo para diseñar y generar los esquemas y mapas conceptuales que representan la arquitectura y los componentes del sistema, facilitando su comprensión visual.

En ambos casos, el contenido generado fue revisado, ajustado y validado por los integrantes del equipo antes de ser incorporado al repositorio, garantizando que refleje las decisiones tomadas por el equipo.

## Uso de IA en la tercera entrega

**Herramienta utilizada:** Claude (Anthropic).

Para esta entrega, Claude fue utilizado como apoyo en los siguientes aspectos:

- **Comparación de estilos arquitectónicos:** se usó Claude para estructurar la matriz comparativa entre arquitectura por capas, hexagonal y monolito modular, a partir de criterios definidos junto con el equipo y del contexto real del proyecto (equipo, plazo, tecnologías).
- **Redacción del ADR y de la sección 4 de arc42:** se utilizó Claude como apoyo para redactar el registro de decisión arquitectónica (ADR 0001) y la sección de estrategia de solución, siguiendo la decisión tomada por el equipo a partir de la comparación anterior.
- **Construcción del esqueleto ejecutable:** se utilizó Claude como apoyo para generar la estructura inicial de paquetes del backend (organización por dominio), un endpoint de salud y una prueba automatizada base, verificando que el proyecto arranca con un solo comando y que la prueba se ejecuta en verde.

El contenido generado fue revisado y validado por los integrantes del equipo antes de ser incorporado al repositorio, en particular la decisión final de estilo arquitectónico, que corresponde a un criterio del equipo apoyado en el análisis comparativo generado.

## Uso de IA en la cuarta entrega

**Herramienta utilizada:** Claude (Anthropic).

Para esta entrega, Claude fue utilizado como apoyo en los siguientes aspectos:

- **Incremento de arc42:** se usó Claude para redactar las secciones 5 (vista de bloques), 6 (vista de tiempo de ejecución), 9 (decisiones de arquitectura) y el glosario inicial, a partir del contenido ya existente en las secciones 1 a 4 y 10, para mantener coherencia con las decisiones y escenarios ya documentados por el equipo.
- **Diagramas C4 nivel 2 y de secuencia:** se utilizó Claude para generar el diagrama de contenedores (C4 nivel 2) y el diagrama de secuencia del corte vertical implementado, ambos en formato Mermaid para que rendericen directamente en GitHub.
- **Construcción del corte vertical ejecutable:** se utilizó Claude como apoyo para implementar el flujo de creación de pedidos (`POST /pedidos`), incluyendo la comunicación entre los módulos `pedidos` y `menu` a través de la función pública `menu.service.obtener_item()`, y las pruebas automatizadas correspondientes.
- **Completar la tabla de trazabilidad de aspectos:** se usó Claude para conectar el escenario ESC-01 ya documentado con la implementación y la prueba concreta que lo verifica, completando la fila de Usabilidad en `docs/aspectos.md`.
- **Corrección del actor "Estudiante" a "Usuario":** a solicitud del equipo, se generalizó el actor en los diagramas C4 (nivel 1 y 2), en el diagrama de secuencia, en las secciones 1 y 3, en los escenarios ESC-01, ESC-02, ESC-04 y ESC-05, en el glosario y en `docs/aspectos.md`, para que el rol "Usuario" agrupe tanto a estudiantes como a profesores. Se verificó que los enlaces internos entre `arc42.md` y `docs/aspectos.md` (anclas a los títulos de ESC-01 y ESC-02) quedaran actualizados de forma consistente.
- **Materiales de apoyo para la entrega:** se utilizó Claude para generar el PDF de resumen ejecutivo de la entrega, el guion de sustentación oral y la guía de reparto de commits entre los integrantes del equipo.

El contenido generado fue revisado por el equipo antes de incorporarlo al repositorio. Las pruebas automatizadas se ejecutaron localmente (`pytest`) para confirmar que el corte vertical funciona antes de aceptarlo, y se validó que las nuevas secciones de arc42 no contradijeran las decisiones ya tomadas en el ADR-0001.

## Uso de IA en la quinta entrega (S5 — primer corte)

**Herramienta utilizada:** Claude (Anthropic), vía Claude Code sobre el repositorio.

### Qué se usó

- **Reorganización de la documentación:** mover `arc42.md` a `docs/arc42/` y
  renombrar `docs/C4/` a `docs/c4/`, corrigiendo todas las rutas relativas que
  el movimiento rompió (README, `docs/aspectos.md`, los tres archivos de C4).
- **Anclas estables:** sustituir las anclas autogeneradas de los títulos
  (`#102-esc-01-----primer-pedido...`, que eran inconsistentes y se rompían al
  editar el título) por anclas HTML explícitas `<a id="esc-01"></a>`.
- **Tabla de trazabilidad de 8 columnas** en `docs/aspectos.md` (ID, aspecto,
  escenario, medida, C4, ADR, código, pruebas).
- **Sección 4 de arc42:** reescritura de la motivación para ligarla a ESC-01,
  ESC-02 y ESC-03, y nueva subsección 4.4 con tácticas arquitectónicas por
  escenario.
- **Matriz comparativa por escenario** en `docs/comparativa-arquitectura.md`.
- **Pipeline de CI** (`.github/workflows/ci.yml`) que ejecuta `pytest` en
  Python 3.11 y 3.12.
- **Script de medición de línea base** (`backend/scripts/medir_linea_base.py`)
  y su prueba de regresión.
- **Registro de la evidencia de CI:** una vez ejecutado el workflow, se usó
  Claude para verificar los runs y añadir a `docs/correcciones.md` la sección
  "Evidencia de integración continua" con los cuatro runs y sus resultados.
- **Documento de correcciones para la revisión** (`CORRECCIONES.md`, en la raíz
  del repositorio): resumen dirigido a la nueva revisión docente con el mapa de
  rutas de cada documento exigido, lo corregido, lo pendiente y los comandos de
  verificación.
- **Corrección de los hallazgos de seguridad de SonarCloud** en el paso de
  instalación de dependencias del workflow: generación de `requirements.in` y
  del lock `requirements-ci.txt` con versiones exactas y hashes
  (`pip-compile --generate-hashes`), e instalación en CI con
  `--require-hashes --only-binary=:all:`.

### Qué se rechazó y por qué

Esta sección responde a la observación del docente: la IA propuso más de lo que
se incorporó. Lo descartado y su motivo:

| Propuesta de la IA | Decisión | Motivo del rechazo |
|---|---|---|
| Partir `arc42.md` en un archivo por sección dentro de `docs/arc42/` (`01-introduccion.md`, `02-restricciones.md`, …) | **Rechazada** | Habría roto todos los enlaces externos ya entregados y publicados en entregas anteriores, y el documento todavía es lo bastante corto para leerse de corrido. Se mantiene un único `arc42.md` dentro de la carpeta exigida |
| Añadir una novena columna "Táctica arquitectónica" a la tabla de aspectos | **Rechazada** | El formato pedido en el curso es de **ocho** columnas. La táctica se documenta en arc42 §4.4, enlazada desde el encabezado de la tabla |
| Rellenar las filas ESC-02 a ESC-05 de la tabla de aspectos con código y pruebas "previstos" | **Rechazada** | Los módulos `pagos` y `usuarios` están vacíos: escribir rutas de archivos que no existen sería trazabilidad falsa. Se marcan explícitamente como ⏳ pendientes |
| Fijar el umbral de la prueba de regresión en el p95 medido en local (3,32 ms) | **Rechazada** | Los runners compartidos de GitHub Actions tienen una varianza mucho mayor; ese umbral habría producido fallos intermitentes que enseñan al equipo a ignorar el CI. Se fijó en 50 ms, holgado pero suficiente para detectar una regresión de orden de magnitud |
| Presentar la medición de latencia en proceso como "prueba de carga" de ESC-02 | **Rechazada** | ESC-02 exige concurrencia real en hora pico. La medición actual es una línea base del corte vertical, no una prueba de carga, y así queda rotulada en `docs/restriccion-s5.md` |
| Redactar el diagnóstico de la restricción asignada de S5 a partir de una suposición | **Rechazada** | La restricción la asigna el docente y el equipo no la tiene registrada en el repositorio. Inventarla habría producido un documento no verificable. La sección queda marcada como pendiente de dato del equipo |
| Crear la etiqueta `corte-1` sobre un commit posterior al cierre | **Rechazada** | Etiquetar trabajo posterior al cierre como si fuera la entrega del corte sería incorrecto. La etiqueta se creará sobre el commit de la próxima entrega, como indicó el docente |
| Redactar `CORRECCIONES.md` afirmando que se corrigió **todo** lo observado | **Rechazada** | Cuatro puntos siguen abiertos (restricción asignada, ADR del reto, etiqueta `corte-1` y reparto de contribución). Un documento que los diera por cerrados sería desmentido por el propio repositorio en la revisión. Se declara explícitamente lo pendiente con su motivo |
| Completar las filas ESC-02 a ESC-05 de la tabla de aspectos con rutas de código "previstas" para que la tabla se viera completa | **Rechazada** | Ya descartado antes por el mismo motivo: los módulos `pagos` y `usuarios` están vacíos y sería trazabilidad falsa |
| Reemplazar `requirements.txt` por el lock con hashes, para tener un solo archivo de dependencias | **Rechazada** | El lock se resuelve para Linux y CPython 3.11/3.12; imponerlo como instalación local rompería el entorno de los integrantes que trabajan en Windows. Se mantiene `requirements.txt` para desarrollo y el lock se usa solo en CI |
| Atribuir el fallo del Quality Gate a los permisos del workflow sin leer el informe de SonarCloud | **Rechazada tras comprobarla** | Fue la primera hipótesis y resultó equivocada: al declarar `permissions` el gate siguió en C. Los hallazgos reales estaban en la instalación de dependencias. Se corrigió solo después de leer las reglas concretas en el informe |

Todo el contenido incorporado fue revisado por el equipo antes de aceptarlo, y
las pruebas se ejecutaron en verde (`pytest`, 5 pruebas) antes de subir los
cambios.
