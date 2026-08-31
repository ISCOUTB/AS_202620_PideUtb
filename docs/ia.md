
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
