# Documentación de Arquitectura --- PideUTB (arc42)

## 1. Introducción y objetivos

### 1.1 Descripción general

En la Universidad Tecnológica de Bolívar, los estudiantes que desean
comprar alimentos deben acercarse físicamente a los establecimientos del
campus para consultar las opciones disponibles, realizar el pedido y
esperar para recibirlo. Durante los horarios de mayor demanda, este
proceso puede generar filas y tiempos de espera que reducen el tiempo
disponible entre clases y otras actividades académicas.

**PideUTB** es un sistema web que busca solucionar esta situación
permitiendo a los estudiantes consultar los establecimientos del campus,
revisar sus menús y precios, seleccionar productos, realizar pedidos y
efectuar el pago anticipado mediante una pasarela de pagos. Una vez
confirmado el pedido y el pago, el sistema genera un código único que el
estudiante presenta al momento de recoger su compra.

Los establecimientos contarán con un módulo para recibir y gestionar los
pedidos, administrar productos, precios y disponibilidad, y actualizar
el estado de cada pedido.

### 1.2 Objetivos del sistema

-   Reducir las filas para realizar pedidos de comida dentro del campus.
-   Disminuir el tiempo que los estudiantes dedican al proceso de compra
    y recogida.
-   Permitir que el estudiante realice la mayor parte del proceso de
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
  **Estudiantes de la UTB**           Realizar compras de forma rápida,
                                      sencilla y clara, consultar precios
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
busca reducir el tiempo y esfuerzo que los estudiantes necesitan para
comprar comida. Si realizar un pedido mediante la plataforma resulta
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

-   El **Estudiante** consulta establecimientos y menús, selecciona
    productos, realiza pedidos, efectúa el pago y utiliza el código
    generado para recoger su compra.
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

    Person(estudiante, "Estudiante", "Consulta menús, realiza pedidos, paga y recoge su comida con un código")
    Person(establecimiento, "Personal del establecimiento", "Gestiona productos, precios y estado de los pedidos")
    Person(admin, "Administrador", "Administra aspectos generales de la plataforma")

    System(pideutb, "PideUTB", "Sistema web para realizar pedidos de comida dentro del campus")

    System_Ext(wompi, "Wompi (Sandbox)", "Pasarela de pagos utilizada para transacciones de prueba")
    System_Ext(supabase, "Supabase", "Servicios gestionados de base de datos y autenticación")

    Rel(estudiante, pideutb, "Consulta menús, realiza pedidos, paga y recibe código")
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
  **Estudiante ↔ PideUTB**            Consulta establecimientos, revisa
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
│   │   └── ESC-01 — Primer pedido de un estudiante nuevo (A/M)
│   │
│   ├── Eficiencia de uso
│   │   ├── ESC-02 — Pedido de un estudiante recurrente en hora pico (A/M)
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

### 10.2 ESC-01 --- Primer pedido de un estudiante nuevo

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Estudiante que utiliza PideUTB por
                                      primera vez.

  **Estímulo**                        Intenta consultar un
                                      establecimiento y realizar su
                                      primer pedido.

  **Artefacto**                       Módulo de estudiante: catálogo y
                                      carrito.

  **Entorno**                         Horario normal de operación, sin
                                      capacitación previa.

  **Respuesta**                       El estudiante logra buscar un
                                      establecimiento, seleccionar
                                      productos, confirmar el pedido y
                                      llegar al proceso de pago sin ayuda
                                      externa.

  **Medida de respuesta**             El flujo debe completarse en
                                      **menos de 3 minutos**, sin errores
                                      de navegación.
  -----------------------------------------------------------------------

### 10.3 ESC-02 --- Pedido de un estudiante recurrente en hora pico

  -----------------------------------------------------------------------
  Parte                               Descripción
  ----------------------------------- -----------------------------------
  **Fuente**                          Estudiante que ya ha utilizado
                                      PideUTB anteriormente.

  **Estímulo**                        Desea realizar un pedido durante la
                                      hora de almuerzo.

  **Artefacto**                       Módulo de estudiante: catálogo,
                                      carrito y proceso de pedido.

  **Entorno**                         Hora pico, con posible alta
                                      concurrencia de usuarios.

  **Respuesta**                       El estudiante puede seleccionar sus
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
  **Fuente**                          Estudiante que llega a recoger su
                                      pedido.

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
  **Fuente**                          Estudiante que realiza el pago de
                                      un pedido.

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
