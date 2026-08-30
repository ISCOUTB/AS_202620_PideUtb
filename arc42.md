# Documentación de Arquitectura --- PideUTB (arc42)

## 1. Introducción y objetivos

### 1.1 Descripción general

En la Universidad Tecnológica de Bolívar, los usuarios de la comunidad
académica (estudiantes y profesores) que desean comprar alimentos deben
acercarse físicamente a los establecimientos del campus para consultar
las opciones disponibles, realizar el pedido y esperar para recibirlo.
Durante los horarios de mayor demanda, este proceso puede generar filas
y tiempos de espera que reducen el tiempo disponible entre clases y
otras actividades académicas.

**PideUTB** es un sistema web que busca solucionar esta situación
permitiendo a los usuarios (estudiantes y profesores) consultar los
establecimientos del campus, revisar sus menús y precios, seleccionar
productos, realizar pedidos y efectuar el pago anticipado mediante una
pasarela de pagos. Una vez confirmado el pedido y el pago, el sistema
genera un código único que el usuario presenta al momento de recoger su
compra.

Los establecimientos contarán con un módulo para recibir y gestionar los
pedidos, administrar productos, precios y disponibilidad, y actualizar
el estado de cada pedido.

### 1.2 Objetivos del sistema

-   Reducir las filas para realizar pedidos de comida dentro del campus.
-   Disminuir el tiempo que los usuarios (estudiantes y profesores)
    dedican al proceso de compra y recogida.
-   Permitir que el usuario realice la mayor parte del proceso de
    compra desde la plataforma.
-   Organizar la recepción y gestión de pedidos por parte de los
    establecimientos.
-   Permitir la realización de pagos mediante Wompi en ambiente Sandbox
    durante el desarrollo académico.
-   Generar un código único que permita verificar el pedido antes de su
    entrega.
-   Mantener una arquitectura que permita evolucionar posteriormente
    desde Sandbox hacia pagos reales.

### 1.3 Interesados y sus intereses

  -----------------------------------------------------------------------
  Interesado                          Interés / expectativa
  ----------------------------------- -----------------------------------
  **Usuarios de la UTB (estudiantes   Realizar compras de forma rápida,
  y profesores)**                     sencilla y clara, consultar precios
                                      y productos y evitar filas.

  **Establecimientos del campus**     Recibir y gestionar pedidos de
                                      forma organizada, actualizar su
                                      información y verificar
                                      correctamente las entregas.

  **Equipo desarrollador**            Cumplir los objetivos académicos,
                                      desarrollar un sistema funcional y
                                      adquirir experiencia en el proceso
                                      de diseño e implementación.

  **Docente / evaluador**             Verificar que el proyecto cumpla
                                      los requisitos, la metodología y
                                      los entregables definidos para el
                                      curso.

  **Universidad Tecnológica de        Contar con una solución alineada
  Bolívar**                           con el entorno universitario y con
                                      posibilidad de evolución futura.
  -----------------------------------------------------------------------

### 1.4 Objetivos de calidad

El atributo de calidad prioritario es la **usabilidad**, porque PideUTB
busca reducir el tiempo y esfuerzo que los usuarios (estudiantes y
profesores) necesitan para comprar comida. Si realizar un pedido mediante la plataforma resulta
complicado o toma demasiado tiempo, el sistema no cumpliría
adecuadamente su propósito.

Además de la usabilidad, se consideran importantes la **confiabilidad**,
la **seguridad**, la **disponibilidad** y el **rendimiento**.

  -----------------------------------------------------------------------
  Prioridad               Atributo                Motivación
  ----------------------- ----------------------- -----------------------
  Muy alta                **Usabilidad**          El sistema debe ser
                                                  sencillo y eficiente
                                                  para que realmente
                                                  reduzca las filas y el
                                                  tiempo de compra.

  Alta                    **Confiabilidad**       Los pedidos, pagos y
                                                  códigos deben
                                                  mantenerse
                                                  correctamente asociados
                                                  para evitar errores
                                                  durante la entrega.

  Alta                    **Seguridad**           El acceso a la
                                                  información y la
                                                  validación de los
                                                  pedidos deben
                                                  protegerse frente a
                                                  usos no autorizados.

  Media-alta              **Disponibilidad**      El sistema debe estar
                                                  disponible
                                                  especialmente durante
                                                  los horarios de mayor
                                                  demanda.

  Media                   **Rendimiento**         Las operaciones
                                                  principales deben
                                                  responder rápidamente
                                                  para no introducir
                                                  nuevos tiempos de
                                                  espera.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 2. Restricciones de arquitectura

Las siguientes restricciones corresponden a decisiones tomadas por el
equipo y a condiciones del proyecto académico.

### 2.1 Restricciones técnicas

  -----------------------------------------------------------------------
  Restricción                         Justificación
  ----------------------------------- -----------------------------------
  **Backend con FastAPI y Python**    Se utilizará para desarrollar la
                                      API del sistema y facilitar la
                                      implementación del backend.

  **Base de datos Supabase basada en  Permite utilizar una base de datos
  PostgreSQL**                        relacional gestionada sin
                                      administrar infraestructura propia.

  **Aplicación web**                  El alcance inicial corresponde a
                                      una plataforma web y no a una
                                      aplicación móvil nativa.

  **Frontend basado en HTML, CSS y    Constituye la base de la interfaz
  JavaScript**                        web. Podrá complementarse con una
                                      librería o framework frontend si el
                                      equipo lo considera necesario.

  **Wompi en ambiente Sandbox**       Permite probar el flujo de pagos
                                      sin utilizar dinero real durante el
                                      desarrollo académico.

  **Despliegue previsto en Vercel**   Se utilizará como opción de
                                      despliegue del proyecto dentro de
                                      las posibilidades disponibles para
                                      el equipo.
  -----------------------------------------------------------------------

### 2.2 Restricciones organizativas

  -----------------------------------------------------------------------
  Restricción                         Justificación
  ----------------------------------- -----------------------------------
  **Equipo de tres integrantes**      El proyecto será desarrollado por
                                      Santiago José Cuesta Maza, Daniela
                                      Sofía Arrieta Guardo y Ruddy
                                      Rodríguez Romero.

  **Fecha límite: 22/11/2026**        Es la fecha establecida en la
                                      plataforma del curso y limita el
                                      alcance y tiempo disponible para el
                                      desarrollo.

  **Sin presupuesto para el           Se priorizarán herramientas y
  proyecto**                          servicios gratuitos o con ambientes
                                      de prueba.

  **Repositorio en la organización    Corresponde al espacio establecido
  ISCOUTB de GitHub**                 para el desarrollo y seguimiento
                                      del proyecto.

  **Documentación en español**        Es el idioma utilizado para la
                                      documentación y actividades del
                                      curso.

  **Rama principal `master`**         Es la convención establecida
                                      actualmente en el repositorio.
  -----------------------------------------------------------------------

### 2.3 Restricciones legales

Para esta etapa académica no se ha identificado una restricción legal
específica que determine una tecnología o una decisión concreta de
arquitectura. Sin embargo, el sistema deberá considerar las normas y
políticas aplicables al tratamiento y protección de los datos personales
cuando se avance hacia una implementación real.

------------------------------------------------------------------------

## 3. Contexto y alcance del sistema

### 3.1 Contexto de negocio

PideUTB interactúa principalmente con tres tipos de usuarios humanos y
con sistemas externos necesarios para su funcionamiento.

-   El **Usuario** (estudiante o profesor) consulta establecimientos y
    menús, selecciona productos, realiza pedidos, efectúa el pago y
    utiliza el código generado para recoger su compra.
-   El **Personal del establecimiento** administra productos, precios y
    disponibilidad, recibe los pedidos y actualiza su estado hasta la
    entrega.
-   El **Administrador** administra aspectos generales de la plataforma.
-   **Wompi** interviene como pasarela de pagos durante el desarrollo
    mediante su ambiente Sandbox.
-   **Supabase** proporciona los servicios de persistencia de datos y
    las capacidades de autenticación utilizadas por el sistema.

### 3.2 Diagrama de contexto (C4 --- Nivel 1)

El siguiente diagrama representa el sistema PideUTB, sus principales
usuarios y los sistemas externos con los que interactúa.

``` mermaid
C4Context
    title Diagrama de Contexto — PideUTB

    Person(usuario, "Usuario (estudiante o profesor)", "Consulta menús, realiza pedidos, paga y recoge su comida con un código")
    Person(establecimiento, "Personal del establecimiento", "Gestiona productos, precios y estado de los pedidos")
    Person(admin, "Administrador", "Administra aspectos generales de la plataforma")

    System(pideutb, "PideUTB", "Sistema web para realizar pedidos de comida dentro del campus")

    System_Ext(wompi, "Wompi (Sandbox)", "Pasarela de pagos utilizada para transacciones de prueba")
    System_Ext(supabase, "Supabase", "Servicios gestionados de base de datos y autenticación")

    Rel(usuario, pideutb, "Consulta menús, realiza pedidos, paga y recibe código")
    Rel(establecimiento, pideutb, "Gestiona productos y pedidos")
    Rel(admin, pideutb, "Administra la plataforma")
    Rel(pideutb, wompi, "Envía solicitudes de pago y recibe estados de transacción", "HTTPS/API")
    Rel(pideutb, supabase, "Consulta y almacena datos del sistema", "HTTPS/API")
```

### 3.3 Alcance y relaciones externas

El C4 de nivel 1 muestra el sistema desde una perspectiva externa. No
representa componentes internos como clases, módulos o tablas de la base
de datos.

Las principales interacciones externas son:

  -----------------------------------------------------------------------
  Interacción                         Descripción
  ----------------------------------- -----------------------------------
  **Usuario ↔ PideUTB**                Consulta establecimientos, revisa
                                      menús, realiza pedidos, paga y
                                      obtiene el código de recogida.

  **Establecimiento ↔ PideUTB**       Gestiona productos y pedidos y
                                      actualiza los estados
                                      correspondientes.

  **Administrador ↔ PideUTB**         Administra aspectos generales de la
                                      plataforma.

  **PideUTB ↔ Wompi**                 Se comunica con la pasarela para
                                      gestionar el proceso de pago en
                                      Sandbox.

  **PideUTB ↔ Supabase**              Almacena y consulta la información
                                      necesaria para el funcionamiento
                                      del sistema.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 4. Estrategia de solución

### 4.1 Decisiones tecnológicas de fondo

Las decisiones tecnológicas base ya fueron fijadas como restricciones en
la sección 2: FastAPI y Python para el backend, Supabase (PostgreSQL)
para persistencia y autenticación, Wompi en Sandbox para pagos, y un
frontend web con HTML/CSS/JavaScript. La estrategia de solución de esta
sección se centra en **cómo se organiza el código dentro de esas
restricciones**, es decir, en el estilo arquitectónico interno del
backend.

### 4.2 Estilo arquitectónico elegido

El equipo evaluó tres estilos arquitectónicos posibles para organizar el
backend: **arquitectura por capas**, **arquitectura hexagonal (puertos y
adaptadores)** y **monolito modular**. La comparación completa, con
criterios y puntajes, se documenta en
[`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) y
la decisión formal queda registrada en
[`docs/adr/0001-estilo-arquitectonico.md`](docs/adr/0001-estilo-arquitectonico.md).

Se eligió un **monolito modular**: un único desplegable backend
organizado internamente en módulos de dominio (pedidos, menú, pagos,
usuarios/autenticación), cada uno con sus propias capas internas
(rutas/API, lógica de aplicación, acceso a datos). Los módulos exponen
una interfaz clara entre sí y evitan el acceso directo al detalle interno
de otro módulo.

### 4.3 Motivación

  -----------------------------------------------------------------------
  Objetivo de calidad                 Cómo lo favorece el monolito modular
  ----------------------------------- -----------------------------------
  **Usabilidad** (entrega dentro del  Al no introducir la sobrecarga de
  plazo fijo, sin retrabajo de        puertos/adaptadores de hexagonal,
  arquitectura)                       el equipo puede dedicar más tiempo
                                       a construir el flujo de usuario en
                                       lugar de a la infraestructura
                                       arquitectónica.

  **Confiabilidad**                   Separar por dominios (pedidos,
                                       pagos, usuarios) reduce el riesgo
                                       de que un cambio en un módulo
                                       rompa la lógica de otro.

  **Curva de aprendizaje del equipo** Los tres integrantes son
  (equipo de 3 generalistas sin       generalistas full-stack sin
  roles fijos)                        experiencia previa reportada en
                                       hexagonal; el monolito modular es
                                       más cercano a la forma en que ya
                                       organizan features por carpetas.

  **Alineación con el tamaño del      PideUTB no tiene una lógica de
  proyecto**                          dominio lo suficientemente compleja
                                       como para justificar el
                                       desacoplamiento estricto que ofrece
                                       hexagonal.

  **Despliegue en Vercel**            Un único desplegable sin capas
                                       adicionales de indirección
                                       simplifica el empaquetado
                                       serverless.
  -----------------------------------------------------------------------

### 4.4 Consecuencias para la estructura del código

-   El backend se organiza por **paquetes de dominio** (por ejemplo:
    `pedidos/`, `menu/`, `pagos/`, `usuarios/`), y no por tipo técnico
    (no hay una carpeta única `controllers/` o `models/` para todo el
    sistema).
-   Cada módulo de dominio mantiene internamente su propia separación de
    responsabilidades (rutas, lógica de aplicación, acceso a datos), sin
    imponer la ceremonia completa de puertos y adaptadores.
-   La comunicación entre módulos se realiza a través de una interfaz
    explícita (funciones o clases de servicio expuestas), evitando que un
    módulo acceda directamente a las tablas o al almacenamiento interno
    de otro.
-   Esta decisión no es definitiva ni irreversible: si en una entrega
    posterior la complejidad del dominio lo justifica, algún módulo
    puntual podría evolucionar hacia un estilo más desacoplado (por
    ejemplo, aislar la integración con Wompi detrás de una interfaz tipo
    puerto/adaptador), sin necesidad de reescribir todo el sistema.
-   El esqueleto ejecutable de la sección de arranque del repositorio
    (ver README) ya refleja esta organización mediante paquetes vacíos
    correspondientes a cada módulo de dominio.

------------------------------------------------------------------------

## 5. Vista de bloques

### 5.1 Nivel 1 — Diagrama de contenedores (C4 — Nivel 2)

El diagrama de contexto (sección 3.2) mostró a PideUTB como una caja
negra. El siguiente diagrama abre esa caja y muestra sus piezas
desplegables: el frontend web, la API backend y los sistemas externos
de los que depende.

``` mermaid
C4Container
    title Diagrama de Contenedores — PideUTB

    Person(usuario, "Usuario (estudiante o profesor)")
    Person(establecimiento, "Personal del establecimiento")
    Person(admin, "Administrador")

    System_Boundary(pideutb, "PideUTB") {
        Container(frontend, "Frontend Web", "HTML, CSS, JavaScript", "Interfaz web consumida por los tres roles: consulta de menú, pedidos, gestión de estados.")
        Container(api, "API PideUTB", "FastAPI (Python) — monolito modular", "Expone endpoints REST agrupados por módulo de dominio (pedidos, menu, pagos, usuarios). Los módulos solo se comunican entre sí por funciones públicas de servicio (ver ADR-0001).")
    }

    System_Ext(supabase, "Supabase", "Persistencia (PostgreSQL) y autenticación.")
    System_Ext(wompi, "Wompi Sandbox", "Procesamiento de pagos de prueba.")

    Rel(usuario, frontend, "Usa", "HTTPS")
    Rel(establecimiento, frontend, "Usa", "HTTPS")
    Rel(admin, frontend, "Usa", "HTTPS")
    Rel(frontend, api, "Consume", "HTTPS/JSON")
    Rel(api, supabase, "Lee/escribe datos, valida identidad", "HTTPS/API")
    Rel(api, wompi, "Solicita y confirma cobros", "HTTPS/API")
```

**Nota de despliegue:** frontend y API se despliegan como servicios
separados en Vercel, pero la API sigue siendo un único contenedor
internamente (monolito modular) — no hay un contenedor por módulo de
dominio.

### 5.2 Nivel 2 — Módulos internos de la API (caja blanca)

El contenedor "API PideUTB" se descompone en los cuatro módulos de
dominio definidos en la estrategia de solución (sección 4). Cada uno
sigue la misma estructura interna:

```
modulo/
├── models.py       # entidades y esquemas Pydantic del módulo
├── router.py        # endpoints FastAPI (capa de entrada HTTP)
├── service.py        # lógica de negocio + INTERFAZ PÚBLICA del módulo
└── repository.py    # acceso a datos (Supabase)
```

``` mermaid
graph TD
    subgraph API["API PideUTB (FastAPI)"]
        M[menu]
        P[pedidos]
        PG[pagos]
        U[usuarios]
    end
    P -->|"llama a menu.service.obtener_item()"| M
    P -.->|"llamará a pagos.service (próx. entrega)"| PG
    P -.->|"validará usuario vía usuarios.service (pendiente)"| U

    style PG stroke-dasharray: 5 5
    style U stroke-dasharray: 5 5
```

**Regla de comunicación (ADR-0001):** un módulo solo puede invocar
funciones exportadas por el `service.py` de otro módulo. Está prohibido
importar `repository.py` o acceder a `models.py` de un módulo distinto
directamente.

### 5.3 Responsabilidad de cada módulo

  -----------------------------------------------------------------------------------------------------------------
  Módulo                     Responsabilidad                                          Estado en esta entrega
  --------------------------- --------------------------------------------------------- ---------------------------
  **menu**                    Consultar y administrar ítems del menú por                Implementado (lectura) —
                               establecimiento.                                          usado por el corte
                                                                                          vertical.

  **pedidos**                 Crear y gestionar pedidos, orquestando llamadas a          Implementado — corte
                               `menu` (y luego a `pagos`).                               vertical de esta entrega.

  **pagos**                   Procesar pagos vía Wompi Sandbox y generar el código       Pendiente — corte vertical
                               de canje.                                                 de la próxima entrega.

  **usuarios**                Autenticación y roles (usuario: estudiante o profesor /     Pendiente.
                               establecimiento / admin).
  -----------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 6. Vista de tiempo de ejecución (runtime)

### 6.1 Escenario: crear un pedido (corte vertical ejecutable de esta entrega)

Este es el flujo implementado y ejecutable en esta entrega (ver
[README — Corte vertical ejecutable](README.md#corte-vertical-ejecutable)).

``` mermaid
sequenceDiagram
    actor U as Usuario
    participant R as pedidos.router
    participant SP as pedidos.service
    participant SM as menu.service
    participant RM as menu.repository
    participant RP as pedidos.repository

    U->>R: POST /pedidos {establecimiento_id, item_id, cantidad}
    R->>SP: crear_pedido(datos)
    SP->>SM: obtener_item(item_id)
    SM->>RM: buscar_por_id(item_id)
    RM-->>SM: item (nombre, precio, disponible)
    SM-->>SP: item
    alt item no existe o no disponible
        SP-->>R: error 404 / 409
        R-->>U: respuesta de error
    else item válido
        SP->>SP: calcular total = precio * cantidad
        SP->>RP: guardar(pedido)
        RP-->>SP: pedido creado (id, estado=pendiente_pago)
        SP-->>R: pedido creado
        R-->>U: 201 Created + datos del pedido
    end
```

**Por qué este diagrama importa para la arquitectura:** muestra en
tiempo de ejecución la regla estática impuesta por el ADR-0001 —
`pedidos` nunca toca `menu.repository` directamente, solo pasa por
`menu.service`. Si en el futuro `menu` cambia su forma de almacenar
datos, `pedidos` no se entera. Este flujo cubre además el escenario
**ESC-01** (sección 10.2): un usuario nuevo (estudiante o profesor)
completa su primer pedido con un único request de tres campos.

------------------------------------------------------------------------

## 7. Vista de despliegue

*(Pendiente — se documentará cuando se configure el despliegue real en
Vercel, en una próxima entrega.)*

## 8. Conceptos transversales

*(Pendiente — se documentará a medida que surjan conceptos que
atraviesen varios módulos, por ejemplo el manejo uniforme de errores o
la validación de entrada.)*

------------------------------------------------------------------------

## 9. Decisiones de arquitectura

Las decisiones arquitectónicas relevantes se documentan como ADRs en
[`docs/adr/`](docs/adr/), siguiendo el formato estándar (contexto,
decisión, alternativas consideradas, consecuencias).

  ---------------------------------------------------------------------------------
  ID                                                    Título              Estado
  ------------------------------------------------------ ------------------- -------
  [ADR-0001](docs/adr/0001-estilo-arquitectonico.md)     Estilo               Aceptada
                                                          arquitectónico:
                                                          monolito modular
  ---------------------------------------------------------------------------------

*(Este índice se ampliará en cada entrega a medida que surjan nuevas
decisiones — por ejemplo, la forma de generar y validar el código de
canje, prevista para la siguiente entrega.)*

------------------------------------------------------------------------

## 10. Requisitos de calidad

Los requisitos de calidad se expresan mediante escenarios verificables.
Cada escenario contiene seis partes: **fuente, estímulo, artefacto,
entorno, respuesta y medida de respuesta**.

Los valores numéricos indicados en estos escenarios son **objetivos
iniciales de calidad**. Todavía no representan resultados
experimentales; posteriormente podrán comprobarse mediante pruebas del
sistema.

### 10.1 Árbol de utilidad

La prioridad combina el impacto esperado para el proyecto y el riesgo o
dificultad técnica de satisfacer el escenario.

``` text
PideUTB
│
├── Usabilidad — Prioridad muy alta
│   │
│   ├── Facilidad de aprendizaje
│   │   └── ESC-01 — Primer pedido de un usuario nuevo (A/M)
│   │
│   ├── Eficiencia de uso
│   │   ├── ESC-02 — Pedido de un usuario recurrente en hora pico (A/M)
│   │   └── ESC-03 — Gestión de estado por el establecimiento (A/B)
│   │
│   └── Manejo de errores
│       └── ESC-05 — Error en el proceso de pago (M/B)
│
├── Confiabilidad — Prioridad alta
│   └── ESC-04 — Verificación del código de recogida (A/M)
│
├── Seguridad — Prioridad alta
│   └── ESC-04 — Verificación del código de recogida (A/M)
│
├── Disponibilidad — Prioridad media-alta
│   └── ESC-02 — Operación durante hora pico (A/M)
│
└── Rendimiento — Prioridad media
    ├── ESC-02 — Tiempo del proceso de pedido (A/M)
    ├── ESC-03 — Actualización del estado (A/B)
    └── ESC-04 — Validación del código (A/M)
```

**Convención de prioridad de los escenarios:** `A/M` significa impacto
alto y riesgo técnico medio; `A/B`, impacto alto y riesgo bajo; `M/B`,
impacto medio y riesgo bajo.

### 10.2 ESC-01 --- Primer pedido de un usuario nuevo

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Usuario (estudiante o profesor) que
                                      utiliza PideUTB por primera vez.

  **Estímulo**                        Intenta consultar un
                                      establecimiento y realizar su
                                      primer pedido.

  **Artefacto**                       Módulo de usuario: catálogo y
                                      carrito.

  **Entorno**                         Horario normal de operación, sin
                                      capacitación previa.

  **Respuesta**                       El usuario logra buscar un
                                      establecimiento, seleccionar
                                      productos, confirmar el pedido y
                                      llegar al proceso de pago sin ayuda
                                      externa.

  **Medida de respuesta**             El flujo debe completarse en
                                      **menos de 3 minutos**, sin errores
                                      de navegación.
  -----------------------------------------------------------------------

### 10.3 ESC-02 --- Pedido de un usuario recurrente en hora pico

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Usuario (estudiante o profesor) que
                                      ya ha utilizado PideUTB
                                      anteriormente.

  **Estímulo**                        Desea realizar un pedido durante la
                                      hora de almuerzo.

  **Artefacto**                       Módulo de usuario: catálogo,
                                      carrito y proceso de pedido.

  **Entorno**                         Hora pico, con posible alta
                                      concurrencia de usuarios.

  **Respuesta**                       El usuario puede seleccionar sus
                                      productos, confirmar el pedido y
                                      avanzar hasta la confirmación del
                                      proceso de pago.

  **Medida de respuesta**             El proceso completo deberá tomar
                                      **menos de 2 minutos en al menos el
                                      90 % de los intentos**.
  -----------------------------------------------------------------------

### 10.4 ESC-03 --- Gestión del estado de pedidos por el establecimiento

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Personal de un establecimiento.

  **Estímulo**                        Recibe un nuevo pedido pagado.

  **Artefacto**                       Panel de gestión de pedidos del
                                      establecimiento.

  **Entorno**                         Horario de atención, con
                                      posibilidad de recibir varios
                                      pedidos simultáneamente.

  **Respuesta**                       El encargado visualiza el pedido y
                                      actualiza su estado entre las
                                      etapas correspondientes.

  **Medida de respuesta**             El cambio de estado deberá
                                      completarse en **máximo 10 segundos
                                      y sin requerir más de 3
                                      interacciones**, sin necesidad de
                                      recargar manualmente la página.
  -----------------------------------------------------------------------

### 10.5 ESC-04 --- Verificación del código de recogida

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Usuario (estudiante o profesor)
                                      que llega a recoger su pedido.

  **Estímulo**                        Presenta su código de compra al
                                      encargado del establecimiento.

  **Artefacto**                       Módulo de verificación del código y
                                      servicios del backend.

  **Entorno**                         Momento de la entrega, con un
                                      pedido previamente pagado y
                                      confirmado.

  **Respuesta**                       El sistema valida que el código
                                      corresponde al pedido y permite
                                      marcarlo como entregado, impidiendo
                                      su reutilización.

  **Medida de respuesta**             La validación deberá responder en
                                      **menos de 2 segundos** y rechazar
                                      el **100 % de los intentos de
                                      reutilización de un código ya
                                      canjeado**.
  -----------------------------------------------------------------------

### 10.6 ESC-05 --- Error en el proceso de pago

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Usuario (estudiante o profesor)
                                      que realiza el pago de un pedido.

  **Estímulo**                        La transacción con Wompi Sandbox
                                      falla o es rechazada.

  **Artefacto**                       Módulo de pago e integración con
                                      Wompi.

  **Entorno**                         Proceso de checkout, en cualquier
                                      horario de operación.

  **Respuesta**                       El sistema informa claramente que
                                      el pago no se completó y permite
                                      reintentarlo sin perder el pedido
                                      armado.

  **Medida de respuesta**             El mensaje de error deberá
                                      mostrarse en **menos de 3
                                      segundos** después del rechazo y el
                                      pedido/carrito deberá conservarse
                                      en el **100 % de los casos**.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 11. Riesgos y deuda técnica

*(Pendiente — se documentará a medida que se identifiquen riesgos
concretos durante la implementación de `pagos` y `usuarios`.)*

------------------------------------------------------------------------

## 12. Glosario (versión inicial)

  -----------------------------------------------------------------------------------------------------------
  Término                              Definición
  ------------------------------------- -----------------------------------------------------------------------
  **Usuario**                           Rol que agrupa a estudiantes y profesores de la UTB que usan PideUTB
                                         para comprar comida; ambos tienen el mismo comportamiento dentro del
                                         sistema (consultar, pedir, pagar, recoger con código).

  **Establecimiento**                   Negocio de comida dentro del campus que publica su menú en PideUTB.

  **Ítem de menú**                      Producto individual ofrecido por un establecimiento (nombre, precio,
                                         disponibilidad).

  **Pedido**                            Solicitud de compra creada por un usuario, compuesta por uno o más
                                         ítems de menú.

  **Código de canje**                   Código único generado tras el pago que el usuario presenta para
                                         recoger su pedido; se invalida tras usarse (ver ESC-04).

  **Monolito modular**                  Estilo arquitectónico donde el sistema es un único desplegable, pero
                                         internamente dividido en módulos que solo se comunican por interfaces
                                         públicas (ver ADR-0001).

  **Módulo**                            Paquete de dominio (`pedidos`, `menu`, `pagos`, `usuarios`) con su
                                         propia capa de router, servicio, repositorio y modelos.

  **Servicio público (`service.py`)**   Única puerta de entrada permitida entre módulos; expone las funciones
                                         que otros módulos pueden invocar.

  **Corte vertical**                    Implementación funcional de un flujo de negocio completo de punta a
                                         punta (HTTP → servicio → repositorio → datos), usada para validar que
                                         la arquitectura funciona en la práctica y no solo en el papel.

  **ADR (Architecture Decision          Documento que registra una decisión arquitectónica, su contexto,
  Record)**                             alternativas consideradas y consecuencias.

  **Wompi Sandbox**                     Entorno de pruebas de la pasarela de pagos Wompi, usado para simular
                                         cobros sin dinero real.
  -----------------------------------------------------------------------------------------------------------
