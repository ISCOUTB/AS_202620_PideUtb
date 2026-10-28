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

  **Presupuesto cero y sin tarjeta de El equipo no dispone de
  crédito**                           financiación ni de una tarjeta con
                                      la que registrarse. No es «bajo
                                      coste»: es cero, y sin medio de
                                      pago. Es la primera restricción que
                                      se aplica al elegir cualquier
                                      servicio, porque descarta de
                                      entrada todo plan que pida tarjeta
                                      aunque su capa gratuita sea
                                      suficiente. Condiciona el
                                      despliegue (ADR-0004), el motor de
                                      base de datos y los límites de
                                      operación con los que conviven los
                                      escenarios de la sección 10.

  **Base de datos relacional         La restricción es el **motor**, no el
  PostgreSQL**                        proveedor. Desde S11 corre en un
                                      contenedor del propio despliegue
                                      (ADR-0008); antes fue gestionada en
                                      Supabase. El código no distingue:
                                      habla PostgreSQL por una cadena de
                                      conexión.

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

  **Despliegue en un contenedor      Desde S11, el servidor del
  con proceso persistente**           laboratorio (ADR-0008); antes,
                                      Render, y antes la previsión
                                      inicial era Vercel. Lo que no ha
                                      cambiado en ninguno de los tres
                                      saltos es la forma: un proceso
                                      persistente y no una función sin
                                      servidor. El motivo decisivo fue el
                                      manejo de conexiones a la base de
                                      datos: una función sin servidor
                                      abre una conexión nueva en cada
                                      arranque en frío, y el tráfico del
                                      sistema es una ráfaga de dos horas.
                                      La comparación completa de las dos
                                      alternativas está en
                                      docs/comparacion-despliegue.md; la
                                      decisión, en ADR-0004.

  **Infraestructura declarada con     Lo que se puede crear con la API
  Terraform**                         del proveedor se declara en infra/
                                      y no se configura a mano. La
                                      excepción está documentada: el plan
                                      gratuito de servicios web de Render
                                      no lo soporta su proveedor de
                                      Terraform, así que la API se crea
                                      manualmente y eso queda anotado en
                                      infra/README.md en lugar de
                                      simularse.
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
-   **No hay más sistemas externos.** La persistencia y la autenticación
    son propias: PostgreSQL corre como contenedor del mismo despliegue
    ([ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md))
    y el mecanismo de sesiones vive en el módulo `usuarios`
    ([ADR-0007](../adr/0007-autenticacion-del-panel.md)).

    Conviene decir qué decía esto antes, porque es una lección y no un
    detalle: hasta la semana 10 esta sección y el diagrama C4 afirmaban
    que **Supabase proveía la autenticación**. Era falso, y del peor
    modo — describía una protección que no existía mientras el panel no
    exigía nada. Hasta la semana 11, Supabase sí proveyó la
    persistencia; desde ADR-0008 ni eso.

<a id="c4-contexto"></a>

### 3.2 Diagrama de contexto (C4 --- Nivel 1)

El diagrama representa el sistema PideUTB, sus principales usuarios y los sistemas externos con los que interactúa. Se documenta como código Mermaid en [`docs/c4/nivel1-contexto.md`](../c4/nivel1-contexto.md), junto con su leyenda de colores.

<a id="alcance-externo"></a>

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

  **(ninguna más)**                   Desde S11 la base de datos es un
                                      contenedor del propio despliegue y
                                      no una interfaz externa. Wompi es
                                      el único sistema que no
                                      controlamos.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

<a id="seccion-4"></a>

## 4. Estrategia de solución

### 4.1 Decisiones tecnológicas de fondo

Las decisiones tecnológicas base ya fueron fijadas como restricciones en
la sección 2: FastAPI y Python para el backend, PostgreSQL para
persistencia, Wompi en Sandbox para pagos, y un
frontend web con HTML/CSS/JavaScript. La estrategia de solución de esta
sección se centra en **cómo se organiza el código dentro de esas
restricciones**, es decir, en el estilo arquitectónico interno del
backend.

### 4.2 Estilo arquitectónico elegido

El equipo evaluó tres estilos arquitectónicos posibles para organizar el
backend: **arquitectura por capas**, **arquitectura hexagonal (puertos y
adaptadores)** y **monolito modular**. La comparación completa, con
criterios y puntajes, se documenta en
[`docs/comparativa-arquitectura.md`](../comparativa-arquitectura.md) y
la decisión formal queda registrada en
[`docs/adr/0001-estilo-arquitectonico.md`](../adr/0001-estilo-arquitectonico.md).

Se eligió un **monolito modular**: un único desplegable backend
organizado internamente en módulos de dominio (pedidos, menú, pagos,
usuarios), cada uno con sus propias capas internas
(rutas/API, lógica de aplicación, acceso a datos). Los módulos exponen
una interfaz clara entre sí y evitan el acceso directo al detalle interno
de otro módulo.

### 4.3 Motivación: cómo el estilo elegido atiende los escenarios priorizados

La motivación no se expresa a nivel de atributos genéricos sino sobre los tres
escenarios de mayor prioridad del [árbol de utilidad](#arbol-utilidad)
(ESC-01, ESC-02 y ESC-03), que son los que la arquitectura debe hacer posibles.

| Escenario priorizado | Umbral a satisfacer | Cómo lo favorece el monolito modular | Qué se sacrifica |
|---|---|---|---|
| [**ESC-01**](#esc-01) — Primer pedido de un usuario nuevo (A/M) | < 3 min, sin errores de navegación | Sin la indirección de puertos/adaptadores, el equipo dedica el tiempo al flujo de usuario. Los módulos separados permiten devolver errores específicos (`404`, `409`) en vez de un `500` genérico que confundiría a un usuario nuevo | Menor aislamiento de la lógica frente al framework |
| [**ESC-02**](#esc-02) — Pedido en hora pico (A/M) | < 2 min en el 90 % de los intentos | Un único desplegable elimina latencia de red entre servicios: la llamada `pedidos → menu` es una llamada en proceso, no un salto HTTP | No se puede escalar `pedidos` de forma independiente; si el umbral falla habrá que extraer el módulo |
| [**ESC-03**](#esc-03) — Gestión del estado por el establecimiento (A/B) | ≤ 10 s y ≤ 3 interacciones | El módulo `pedidos` es dueño único del estado del pedido, así que la transición ocurre en un solo punto sin coordinación distribuida ni consistencia eventual | El panel comparte despliegue con el resto de la API |

Los escenarios de menor prioridad ([ESC-04](#esc-04), [ESC-05](#esc-05))
dependen del módulo `pagos`, **implementado en S7**; la decisión los contempló
desde el principio al mantener `pagos` como módulo aislable (ver 4.4).

<a id="tacticas-por-escenario"></a>

### 4.4 Tácticas arquitectónicas por escenario

| Escenario | Táctica (clasificación ADD/SAiP) | Realización concreta en PideUTB | Estado |
|---|---|---|---|
| [ESC-01](#esc-01) | *Usabilidad* — separar la interfaz de usuario del modelo; soportar la iniciativa del usuario con mensajes de error específicos | `menu.service.obtener_item()` valida existencia y disponibilidad y devuelve `404`/`409` diferenciados; `pedidos.service` solo orquesta y arma el pedido | Implementada y verificada en CI |
| [ESC-02](#esc-02) | *Rendimiento* — reducir la sobrecarga computacional y controlar la demanda de recursos | Comunicación intra-proceso entre módulos (sin salto de red); acceso a datos concentrado en `repository.py` para poder introducir caché de menú sin tocar la lógica de negocio | Base implementada; caché pendiente |
| [ESC-03](#esc-03) | *Modificabilidad/Rendimiento* — encapsular y mantener un único dueño de los datos | El estado del pedido solo se transiciona dentro de `pedidos.service`; ningún otro módulo escribe esa tabla | Implementada (S9) y verificada en CI. **El umbral de 10 s no se cumple con el servicio frío**: ver [`aspectos.md`](../aspectos.md) |
| [ESC-04](#esc-04) | *Seguridad* — verificar la integridad y limitar el acceso; *Confiabilidad* — detectar la reutilización | Código de un solo uso generado con `secrets` al confirmar el pago, y **exigido en la transición a `entregado`**, comparado con `compare_digest`. La reutilización se rechaza sin código propio que la detecte: `entregado` es un estado final, así que el segundo intento falla por la transición | Implementada (S10) y verificada en CI |
| [ESC-05](#esc-05) | *Disponibilidad* — detección de fallos y reintento sin pérdida de estado | El pedido se persiste antes de invocar la pasarela, de modo que un rechazo de Wompi no destruye el carrito | Implementada (S7) y verificada en CI |

La trazabilidad de estas tácticas hasta el código y las pruebas está en
[`docs/aspectos.md`](../aspectos.md).

> **Sobre la columna «Estado».** Tres de estas filas decían «pendiente» de cosas
> implementadas desde S7, S9 y S10. Una tabla de estado que nadie vuelve a tocar
> no se queda neutral: afirma que falta algo que está hecho, y hace dudar del
> resto del documento. Al revisarla aparecieron las dos cosas que ahora dice de
> ESC-03 y ESC-04, y también el ❌ del arranque en frío, que ninguna de las dos
> versiones anteriores mencionaba.

### 4.5 Consecuencias para la estructura del código

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

<a id="c4-contenedores"></a>

### 5.1 Nivel 1 — Diagrama de contenedores (C4 — Nivel 2)

El diagrama de contexto (sección 3.2) mostró a PideUTB como una caja negra. El diagrama de contenedores abre esa caja y muestra sus piezas desplegables: el frontend web, la API backend y los sistemas externos de los que depende. Se documenta como código Mermaid en [`docs/c4/nivel2-contenedores.md`](../c4/nivel2-contenedores.md).

<a id="c4-modulos"></a>

### 5.2 Nivel 2 — Módulos internos de la API (caja blanca)

El contenedor "API PideUTB" se descompone en los cuatro módulos de dominio definidos en la estrategia de solución (sección 4). Cada uno sigue la misma estructura interna (`models.py`, `router.py`, `service.py`, `repository.py`). El diagrama de módulos y la regla de comunicación entre ellos (ADR-0001) se documentan en [`docs/c4/nivel3-modulos.md`](../c4/nivel3-modulos.md).


<a id="responsabilidad-modulos"></a>

### 5.3 Responsabilidad de cada módulo

  -----------------------------------------------------------------------------------------------------------------
  Módulo                     Responsabilidad                                          Estado en esta entrega
  --------------------------- --------------------------------------------------------- ---------------------------
  **menu**                    Consultar y administrar ítems del menú por                Implementado (lectura) —
                               establecimiento.                                          usado por el corte
                                                                                          vertical.

  **pedidos**                 Crear y gestionar pedidos, orquestando llamadas a          Implementado — corte
                               `menu` (y luego a `pagos`).                               vertical de esta entrega.

  **pagos**                   Abrir el cobro en la pasarela y recibir su confirmación   Implementado — corte
                               asíncrona. Dueño de `IntentoPago`.                        vertical de S7.

  **usuarios**                Cuentas y establecimientos. Dueño de                      Implementado. La
                               `Establecimiento`, `Usuario` y `Sesion`.                   autenticación entró en
                               Autenticación y roles.                                     S10 (ADR-0007).
  -----------------------------------------------------------------------------------------------------------------

> **El código de canje pertenece a `pedidos`, no a `pagos`.** Es un atributo del
> `Pedido` y su ciclo de vida es el del pedido, no el del cobro. Si `pagos` lo
> escribiera habría dos escritores de `Pedido`, que es la violación que ADR-0002
> cerró. `pagos` **solicita** la transición; `pedidos` la ejecuta. Ver
> [`ddd-contextos.md` §3](../ddd-contextos.md).

------------------------------------------------------------------------

## 6. Vista de tiempo de ejecución (runtime)

La vista de bloques (sección 5) muestra qué piezas existen. Esta muestra **qué
pasa entre ellas cuando el sistema está funcionando**: quién llama a quién, con
qué protocolo y formato, si hay alguien esperando el resultado, y qué ocurre
cuando el otro lado no responde.

Esta entrega la amplía porque aparece el primer interlocutor que el equipo no
controla —la pasarela de pagos— y con él la primera interacción **asíncrona**
del sistema. La decisión, sus alternativas descartadas y su análisis de
acoplamiento temporal están en
[ADR-0003](../adr/0003-estrategia-integracion.md).

<a id="runtime-flujos"></a>

### 6.1 Resumen de los flujos y sus fronteras

Cada fila es una frontera del sistema. La última columna es la pregunta que
decide si una integración debe ser síncrona o asíncrona: *si apago el otro lado,
¿qué le pasa al usuario?*

| # | Flujo | Protocolo | Formato | Modo | Contrato | Si el otro lado no responde |
|---|---|---|---|---|---|---|
| 1 | Frontend Web → API | HTTPS | JSON (REST) | Síncrono | [`openapi.yaml`](../api/openapi.yaml) | El usuario no puede operar. Aceptable: sin API no hay producto |
| 2 | Entre contextos, dentro de la API | Llamada en proceso | Tipos de `contracts` | Síncrono | `menu.contracts`, `pedidos.contracts`, `pagos.contracts` | No puede ocurrir: mismo proceso |
| 3 | API → Base de datos | TCP (red interna) | PostgreSQL sobre un pool reutilizado | Síncrono | `app/base_de_datos.py`, `app/*/repository.py` | La operación falla y se responde error explícito; `/health` devuelve `503`. Incluye no poder iniciar sesión |
| 4 | API → Wompi (**iniciar** cobro) | HTTPS | JSON | Síncrono | API externa de la pasarela | Error inmediato; el pedido se conserva y se puede reintentar |
| 5 | Wompi → API (**confirmar** cobro) | HTTPS | JSON firmado (webhook) | **Asíncrono** | [`asyncapi.yaml`](../api/asyncapi.yaml) · `eventos-de-pago` | El pedido queda en `pendiente_pago`, consultable |
| 6 | API → Panel del establecimiento | Bus en proceso | JSON | **Asíncrono** | [`asyncapi.yaml`](../api/asyncapi.yaml) · `pedidos-pagados` | El cobro se completa igual; el panel se entera al reconectar |

Las mismas etiquetas aparecen sobre cada flecha del
[diagrama C4 de nivel 2](../c4/nivel2-contenedores.md), de modo que la
estructura y la ejecución cuentan la misma historia.

<a id="runtime-crear-pedido"></a>

### 6.2 Crear un pedido — síncrono, y enteramente dentro del proceso

Corte vertical ejecutable del sistema (ver
[README — Corte vertical ejecutable](../../README.md#corte-vertical-ejecutable)).
Cubre el escenario [ESC-01](#esc-01): un usuario nuevo completa su primer pedido
con un único request de dos campos.

``` mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend Web
    participant R as pedidos.router
    participant SP as pedidos.service
    participant SM as menu.service
    participant SU as usuarios.service
    participant RP as pedidos.repository

    U->>F: elige un ítem y una cantidad
    F->>R: POST /v1/pedidos {item_id, cantidad} · HTTPS/JSON
    R->>SP: crear_pedido(item_id, cantidad)

    SP->>SM: obtener_item(item_id)
    SM-->>SP: ItemDisponible {nombre, precio_centavos, establecimiento_id}

    alt el ítem no existe
        SP-->>R: ItemNoEncontradoError
        R-->>F: 404 {detail}
    else el ítem no está disponible
        SP-->>R: ItemNoDisponibleError
        R-->>F: 409 {detail}
    else ítem válido
        SP->>SU: establecimiento_esta_activo(item.establecimiento_id)
        SU-->>SP: true / false
        alt el establecimiento no está operando
            SP-->>R: EstablecimientoInactivoError
            R-->>F: 409 {detail}
        else el establecimiento opera
            SP->>SP: total_centavos = precio_unitario_centavos x cantidad
            SP->>RP: guardar(pedido, estado = pendiente_pago)
            RP-->>SP: Pedido
            SP-->>R: PedidoPublicado
            R-->>F: 201 Created · PedidoResponse
        end
    end
```

**Qué muestra este diagrama que no se ve en el código.** Tres decisiones de
arquitectura ocurriendo a la vez:

1. **`pedidos` nunca toca `menu.repository`.** Pasa por `menu.service`, que es
   la regla estática de [ADR-0001](../adr/0001-estilo-arquitectonico.md). Si
   Catálogo cambia su forma de almacenar datos, Pedidos no se entera.
2. **El cliente no dice a qué establecimiento va el pedido.** Se deriva del
   ítem, porque aceptarlo del cliente permitía asignar un pedido a un punto que
   no vende ese producto ([V-01](../violaciones.md#v-01)).
3. **Quién decide si el establecimiento opera es `usuarios`**, su único escritor
   ([ADR-0002](../adr/0002-propiedad-datos-establecimiento.md)). Pedidos
   pregunta en lugar de guardar una copia que envejecería.

Todo ocurre dentro del mismo proceso, así que el acoplamiento temporal entre
estos módulos es total — y **gratuito**: si el proceso está vivo, los tres lo
están. Es lo que deja de ser cierto en el flujo siguiente.

<a id="runtime-pagar-pedido"></a>

### 6.3 Pagar un pedido — el flujo que cruza la frontera asíncrona

Es el flujo que motiva [ADR-0003](../adr/0003-estrategia-integracion.md) y cubre
[ESC-05](#esc-05). Tiene **dos fases separadas por un hueco temporal que puede
durar minutos**, y esa separación es el punto entero del diseño.

``` mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend Web
    participant PR as pagos.router
    participant PS as pagos.service
    participant DS as pedidos.service
    participant BUS as bus de eventos
    participant PANEL as Panel del establecimiento
    participant W as Wompi Sandbox

    rect rgb(235, 245, 255)
    Note over U,W: Fase 1 — SÍNCRONA · el usuario está esperando
    U->>F: pulsa «Pagar»
    F->>PR: POST /v1/pagos/intentos {pedido_id, metodo} · HTTPS/JSON
    PR->>PS: iniciar_intento(pedido_id, metodo)
    PS->>DS: obtener_pedido(pedido_id)
    DS-->>PS: PedidoPublicado (pendiente_pago)
    PS-->>PR: IntentoPago {referencia_pago, url_checkout, pendiente}
    PR-->>F: 201 Created
    F->>U: redirige a url_checkout
    end

    Note over U,W: El usuario sale de PideUTB. Del lado del servidor NO queda nadie esperando.
    U->>W: completa el pago (puede durar minutos)

    rect rgb(255, 245, 235)
    Note over W,PANEL: Fase 2 — ASÍNCRONA · la pasarela avisa cuando puede
    W->>PR: POST /v1/pagos/eventos + X-Firma-Evento · HTTPS/JSON firmado
    PR->>PS: firma_valida(cuerpo_en_crudo, firma)

    alt firma ausente o inválida
        PR-->>W: 401 {detail}
    else firma válida
        PR->>PS: procesar_evento(referencia_pago, estado_pago)
        PS->>DS: confirmar_pago(pedido_id)

        alt el pedido ya estaba pagado (reintento de la pasarela)
            DS-->>PS: (pedido, duplicado = true)
        else primera confirmación
            DS->>DS: estado = pagado · genera codigo_canje
            DS->>BUS: publicar «pedido.pagado»
            BUS-)PANEL: pedido.pagado {pedido_id, establecimiento_id, codigo_canje}
            DS-->>PS: (pedido, duplicado = false)
        end

        PS-->>PR: (pedido, duplicado)
        PR-->>W: 202 Accepted {recibido, pedido_id, estado, duplicado}
    end
    end
```

**Por qué el diagrama tiene esta forma y no otra:**

- **`201` en la fase 1, no el resultado del cobro.** Cuando la API responde, el
  pago todavía no ha ocurrido. Prometer el resultado obligaría a esperar a la
  pasarela dentro de la petición, que es la alternativa que ADR-0003 descarta.
- **`202 Accepted` y no `200` en la fase 2.** PideUTB acusa recibo del evento;
  no afirma que todo el efecto de negocio haya concluido. Es la diferencia entre
  «me llegó» y «ya está todo hecho», y sostenerla permite que el manejador
  termine rápido y no provoque reintentos innecesarios.
- **La rama `duplicado = true` no es un caso de error.** Es el camino normal
  cuando la pasarela reintenta, y reintenta siempre que no recibe un `2xx` a
  tiempo. Sin esa rama, un reintento generaría un segundo código de canje y el
  usuario tendría en pantalla uno que ya no sirve — rompiendo
  [ESC-04](#esc-04).
- **La flecha hacia el panel es punteada y sin retorno.** El publicador no sabe
  si hay suscriptores ni si tuvieron éxito. Si el panel está caído, el cobro ya
  ocurrió y sigue siendo válido: esperar su confirmación recrearía el
  acoplamiento temporal que la decisión evita, y encima escondido.
- **La firma se verifica sobre el cuerpo en crudo.** Un webhook es un endpoint
  público capaz de marcar pedidos como pagados; en la fase 1 el interlocutor era
  nuestro propio frontend, en la fase 2 es Internet.

<a id="runtime-consultar-estado"></a>

### 6.4 Consultar el estado — cómo se entera el usuario

Esta consulta **existe por culpa de la asincronía**. En una integración síncrona
no haría falta: el resultado vendría en la misma respuesta. Es el precio
concreto que se paga por desacoplar, y ADR-0003 lo declara como tal.

``` mermaid
sequenceDiagram
    actor U as Usuario
    participant F as Frontend Web
    participant R as pedidos.router

    U->>F: vuelve de la pasarela
    F->>R: GET /v1/pedidos/{pedido_id} · HTTPS/JSON

    alt el evento ya llegó
        R-->>F: 200 {estado: pagado, codigo_canje: "7KQ2ZP"}
        F->>U: muestra el código de canje
    else el evento todavía no llegó
        R-->>F: 200 {estado: pendiente_pago, codigo_canje: null}
        F->>U: «esperando confirmación»
        F->>R: reintenta la consulta
    end
```

`codigo_canje` se declara **siempre presente y anulable** en lugar de opcional:
el consumidor encuentra siempre la clave y solo comprueba si vale `null`, en vez
de distinguir entre «ausente» y «vacío». La decisión está en
[`openapi.yaml`](../api/openapi.yaml) y la razón en
[la política de versionado](../api/politica-versionado.md).

<a id="runtime-modos-de-fallo"></a>

### 6.5 Modos de fallo

Un diagrama de secuencia enseña el camino feliz. Esta tabla enseña los otros,
que son los que deciden si la arquitectura sirve. Cada fila tiene una prueba
automatizada detrás.

| Fallo | Qué hace el sistema | Qué ve el usuario | Prueba |
|---|---|---|---|
| El ítem no existe o no está disponible | Rechaza antes de crear nada | `404` / `409` con mensaje concreto | `test_pedidos.py` |
| El establecimiento no está operando | Rechaza el pedido | `409` con el motivo | `test_propiedad_datos.py::test_pedido_en_establecimiento_inactivo_se_rechaza` |
| La pasarela rechaza el cobro | Registra el rechazo, no toca el pedido | Error claro; **el pedido se conserva** y puede reintentar con otro método | `test_pagos.py::test_un_pago_rechazado_conserva_el_pedido` |
| **El evento de confirmación nunca llega** | Nada. El pedido se queda en `pendiente_pago` | Estado real y consultable, no una pantalla colgada | `test_pagos.py::test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable` |
| El evento llega **repetido** | Lo detecta y no lo reaplica; responde `202` con `duplicado: true` | Nada: el código de canje no cambia | `test_pagos.py::test_el_codigo_de_canje_no_cambia_entre_reintentos` |
| Los eventos llegan **desordenados** | Decide por el estado que traen, no por la marca de tiempo | Nada | `test_pagos.py::test_el_mismo_evento_repetido_no_genera_un_segundo_codigo` |
| Llega un evento **sin firma válida** | Lo rechaza sin tocar el pedido | Nada: no es un usuario | `test_pagos.py::test_un_evento_sin_firma_valida_se_rechaza` |
| Llega un evento con **referencia desconocida** | `404`: la referencia la generamos nosotros, una que no conocemos es falsa | Nada | `test_pagos.py::test_un_evento_con_referencia_desconocida_responde_404` |
| **El panel del establecimiento está caído** | El cobro se completa igual; el evento se pierde para ese suscriptor | Su código de canje, con normalidad | `test_pagos.py::test_un_suscriptor_que_falla_no_tumba_el_cobro` |

El cuarto es el que define la arquitectura: **un evento que no llega deja el
pedido en `pendiente_pago`, que es un estado honesto.** No se afirma que esté
pagado ni que haya fallado. Es la degradación aceptada a cambio del
desacoplamiento, y es preferible a un estado desconocido porque se puede
consultar y se puede reintentar.

<a id="fallos-parciales"></a>

### 6.7 Fallos parciales de las integraciones

§6.5 lista los fallos **del otro extremo**: la pasarela rechaza, el evento no
llega, llega repetido. El sistema los ve como respuestas y decide.

Esta sección lista los otros: los que ocurren **a mitad de una operación
nuestra**, cuando una parte se escribió y la otra no. No los causa nadie de
fuera; los causa que el sistema esté hecho de piezas que pueden fallar por
separado.

La diferencia práctica, y es la que importa: **estos no se ven desde fuera**.
Nadie recibe un error. El pedido queda pagado, el cliente se lleva su comida, y
la contabilidad dice otra cosa. Por eso la columna que vale no es «qué ve el
usuario» sino **qué lo hace visible**.

#### Las fronteras que de verdad existen

Antes de analizar fallos conviene decir qué se puede romper, porque el inventario
corriente está mal:

| Frontera | ¿Cruza la red? | Estado |
|---|---|---|
| Navegador → sitio | Sí | HTTPS por el proxy del laboratorio |
| Navegador → API | Sí | Otro origen: depende de CORS |
| API → base de datos | **No.** Contenedor vecino, ~1 ms | Desde [ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md) |
| Pasarela → API (webhook) | Sí, **entrante** | Al-menos-una-vez, firmado |
| **API → pasarela** | **No existe** | Ver abajo |

**La llamada saliente a la pasarela no existe.** `pagos.service.iniciar_intento`
guarda una fila y construye una URL con una constante; nada contacta a Wompi. El
usuario va a esa URL con su navegador, y la pasarela vuelve por el webhook.

Eso tiene una consecuencia directa sobre lo que S11 pide: **no hay ninguna
integración saliente a la que aplicar reintentos con backoff**. Implementarlos
exigiría primero inventar la llamada. Queda dicho aquí porque la alternativa
—una sección sobre backoff que no se aplica a nada— sería peor que su ausencia.

#### La tabla

| # | Fallo parcial | Qué queda roto | Mitigación | Qué lo hace visible |
|---|---|---|---|---|
| 1 | **Corte entre las dos escrituras de `procesar_evento`** | Pedido `pagado` con su código; intento todavía `pendiente` | El orden **falla hacia el cliente**, y el reintento de la pasarela lo cierra | `pagos.service.conciliar()` · `test_fallos_parciales.py` (4 casos) |
| 2 | El evento en proceso se pierde tras el commit | Un suscriptor no se entera del pago | Se publica **después** de persistir: lo peor es no enterarse, no un hecho falso | `test_el_evento_se_publica_despues_de_persistir` |
| 3 | Un suscriptor revienta | Nada: el cobro ya ocurrió | Aislamiento en `eventos.publicar` | `test_un_suscriptor_que_revienta_no_arrastra_a_los_demas` |
| 4 | La base de datos no responde | Ninguna operación funciona, **ni ingresar al panel** | `/health` devuelve `503` y la plataforma marca el contenedor enfermo | `test_health.py` · panel del laboratorio |
| 5 | El contenedor de la API se reinicia a media petición | Esa petición se pierde; el estado está en la base, no en memoria | Sin estado en proceso desde [V-09](../violaciones.md) | `test_repositorios.py` — las mismas aserciones contra ambas implementaciones |
| 6 | **Se pierde el volumen de datos** | Todo: pedidos, pagos y cuentas | Migraciones y semilla al arrancar; la cuenta inicial se siembra | `test_autenticacion.py::test_el_guion_de_alta_funciona_de_principio_a_fin` |
| 7 | **El proxy no enruta hacia un contenedor** | El servicio corre y responde `404` desde fuera | La plataforma solo enruta hacia contenedores sanos | §7.5, y el chequeo de salud de cada servicio |
| 8 | Despliegue mientras hay tráfico | Peticiones en vuelo cortadas | `depends_on: service_healthy` y arranque con migraciones antes de escuchar | `deploy/compose.lab.yaml` |
| 9 | **Un proxy que no controlamos rechaza al cliente del webhook** | El aviso de pago nunca llega al servidor | Ninguna nuestra: el filtro está delante. El pedido queda en `pendiente_pago`, que es consultable | Medido en [§7.2](#despliegue-topologia): `Python-urllib` recibe `403` antes de entrar |

#### El número 9 no se puede mitigar, solo saber

Los ocho primeros son fallos del sistema, y cada uno tiene algo que hacer. El
noveno no: **ocurre antes de que la petición exista para nosotros**.

Cloudflare rechaza con `403` a los clientes que identifica como automatismos.
Medido con una sola petición —no es cuestión de ritmo— un cliente que se
anuncie como `Python-urllib/3.13` recibe `403` tanto en `GET /health` como en
`POST /v1/pagos/eventos`, mientras que `python-requests`, `Go-http-client` y un
navegador entran y reciben el `401` que les corresponde por firma inválida.

**La consecuencia es la que importa.** Si la pasarela —o cualquier integrador
futuro— usara un cliente con un agente filtrado, sus avisos de pago no llegarían
nunca, y desde aquí sería **indistinguible** de «el evento no llegó»: el pedido
quedaría en `pendiente_pago`, correctamente, y nadie sabría por qué.

La mitigación de ese estado ya existe (§6.5, fila cuarta) y es la razón por la
que esto no es una catástrofe: el pedido se queda en un estado honesto y
consultable, no en uno desconocido. Pero la **causa** era invisible, y un modo de
fallo cuya causa no se puede nombrar no se puede diagnosticar.

Queda aquí por eso: no para arreglarlo —no está a nuestro alcance— sino para que
la próxima vez que un pago «no llegue» exista esta fila que mirar.

#### El número 1, en detalle

Es el único que no se arregla con una decisión ya tomada, así que se explica
entero.

```python
pedido, ya_estaba_pagado = pedidos_service.confirmar_pago(intento.pedido_id)
repository.guardar(intento.model_copy(update={"estado_pago": APROBADO}))
```

Cada `repository` abre su propia conexión y **confirma al salir**: son dos
transacciones, no una. Entre ellas hay una ventana.

**El orden está elegido.** Un corte deja a quien pagó con su código en la mano y
a nosotros con la contabilidad desactualizada. Al revés —marcar el intento
primero— dejaría a quien pagó **sin código**, que es el fallo que sí se nota y
el que no se repara solo. Fallar hacia el cliente es la decisión.

**Se cierra solo, casi siempre.** La pasarela entrega al-menos-una-vez: si no
recibe `2xx`, reintenta, y el reintento rehace las dos escrituras —
`confirmar_pago` es idempotente y el intento sí llega a marcarse. La ventana es
transitoria *mientras el otro extremo reintente*. Si se rinde, queda abierta.

**Las cuatro opciones que se evaluaron:**

| Opción | Por qué no |
|---|---|
| Una sola transacción compartida | Exige que Pagos pase su conexión a Pedidos. Rompe [ADR-0001](../adr/0001-estilo-arquitectonico.md) en la capa de datos, que es donde más cuesta revertirlo |
| Invertir el orden | Cambia de sitio el daño y lo empeora: el cliente se queda sin código |
| Una saga con compensación | **No aplica.** Una saga coordina escrituras en sistemas distintos, donde no hay transacción común. Aquí las dos van a la misma base: no falta un coordinador, falta una transacción |
| Un *outbox* | Resuelve la pérdida de mensajes, que es el fallo 2, no este |

**Lo que se hizo:** conservar la frontera entre contextos y **hacer la ventana
visible**. `pagos.service.conciliar()` devuelve las referencias cuyo pedido está
pagado y cuyo intento sigue pendiente. En un sistema sano la lista está vacía, y
hay una prueba que lo comprueba — sin ella, una conciliación rota devolvería
siempre vacío y pasaría por un sistema impecable.

Un desajuste que nadie puede enumerar es indistinguible de no tenerlo.

#### Por qué no hay outbox

El canal `pedidos-pagados` está declarado en
[`asyncapi.yaml`](../api/asyncapi.yaml), se publica desde `pedidos.service` y
**no tiene ningún suscriptor en producción**. Los únicos `suscribir()` del
repositorio están en las pruebas.

Un mecanismo para no perder mensajes que nadie recibe resolvería un problema que
no se tiene. La decisión queda atada a una prueba —
`test_el_evento_se_pierde_si_no_hay_nadie_escuchando`— que **falla el día que
aparezca un suscriptor**, y obliga entonces a revisar esto en vez de heredarlo.

#### La frontera que las pruebas no cubren

Hay una novena fila que no está en la tabla porque no es una integración del
sistema, sino de su despliegue: **la configuración**.

La puesta en marcha en el servidor del laboratorio encontró **cinco defectos que
las 282 pruebas no podían ver** — CORS sin `Authorization`, `log_format` en el
contexto equivocado de nginx, `add_header` sin heredar, `wget --tries` en un
chequeo de Alpine, y un guion que reventaba tras escribir. Ninguno en código;
todos en los archivos que unen las piezas.

El patrón es el mismo en los cinco: **la prueba y el entorno real no recorren el
mismo camino**. `TestClient` no hace *preflight*, pytest no arranca nginx, y
nadie ejecutaba el guion. Está en [§7.6](#despliegue-deuda) con su mitigación.

### 6.6 Deuda conocida de esta vista

- El canal `pedidos-pagados` se entrega **en proceso** y no sobrevive a un
  reinicio: un suscriptor caído pierde los eventos de ese intervalo. Con un
  broker real esto se resuelve con persistencia del canal; el contrato ya está
  escrito para que ese cambio sea sustituir el transporte y no renegociar la
  integración.
- El registro de idempotencia vive en memoria, igual que el resto del estado
  ([V-09](../violaciones.md#v-09)). Con más de una instancia desplegada, dos
  réplicas podrían procesar el mismo evento. Es la misma deuda que bloquea el
  despliegue real y se cierra con el mismo trabajo.

------------------------------------------------------------------------

<a id="7-vista-de-despliegue"></a>
<a id="seccion-7"></a>

## 7. Vista de despliegue

La vista de bloques (sección 5) dice qué piezas existen y la de tiempo de
ejecución (sección 6) qué pasa entre ellas. Esta dice **dónde corre cada una,
quién la crea y qué se rompe cuando el entorno falla** — que es distinto de lo
que se rompe cuando falla el código.

La decisión de plataforma está en
[ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md), que
reemplaza a [ADR-0004](../adr/0004-plataforma-de-despliegue.md) en la elección
de proveedor —no en su razonamiento de fondo, que sigue vigente: un contenedor
con proceso persistente y no una función sin servidor.

> **Esta vista describe el despliegue del 18/10/2026 en adelante.** Hasta
> entonces el sistema corría en Render con PostgreSQL gestionado en Supabase, y
> los dossiers de las semanas 8 y 9 describen aquello. No se reescriben: eran
> ciertos cuando se escribieron, y una vista de despliegue que borra su historia
> pierde el único sitio donde consta por qué se cambió.

<a id="despliegue-piezas"></a>

### 7.1 Las piezas desplegables

| # | Pieza | Dónde corre | Cómo se crea | Qué pasa si se cae |
|---|---|---|---|---|
| 1 | **Sitio** (`sitio/`) | Contenedor `web`, nginx sin privilegios en el puerto 8080 | [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml) | Nadie puede entrar. La API sigue atendiendo el webhook, así que los pagos en curso se confirman igual |
| 2 | **API** (`backend/`) | Contenedor `api`, uvicorn en el 8000 | idem | El sitio no puede pedir nada. Los webhooks de la pasarela se pierden salvo que ella reintente |
| 3 | **Base de datos** | Contenedor `db`, PostgreSQL 16 sobre un volumen con nombre | idem | La API responde `503` en `/health` y queda marcada enferma. **Y no se puede ni ingresar al panel**: las credenciales viven ahí |
| 4 | **Protección de rama** | GitHub | Terraform, [`infra/github.tf`](../../infra/github.tf) | Se podría fusionar a `master` sin pipeline en verde |
| 5 | **Pipeline** | GitHub Actions | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | No hay despliegue nuevo; lo desplegado sigue funcionando |

Las tres primeras son **un solo desplegable**: un `docker compose` que la
plataforma levanta entero. Eso cambia una cosa respecto del despliegue anterior
y conviene decirla: **la base de datos ya no sobrevive al sistema**. Antes era un
proyecto gestionado aparte, con su propio ciclo de vida; ahora es un contenedor
vecino cuyo volumen depende del mismo despliegue (§7.3).

No hay pieza de **trabajos programados**: el sistema no tiene ninguno. Se hace
constar porque una casilla vacía sin explicación se lee como un olvido.

Tampoco hay pieza de **archivos**: no se suben imágenes ni documentos.

<a id="despliegue-topologia"></a>

### 7.2 Topología y protocolos

```
  Navegador del usuario
        │  HTTPS
        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Cloudflare  ·  *.iscoutb.dev                               │
  │  **Proxy, no solo DNS**: termina TLS y filtra automatismos  │
  └───────────────────────────┬─────────────────────────────────┘
                              │
  ┌───────────────────────────▼─────────────────────────────────┐
  │  VM Oracle Cloud · compartida entre 23 equipos              │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │  Traefik  ·  certificado comodín *.iscoutb.dev        │  │
  │  └───┬───────────────────────────────────┬───────────────┘  │
  │      │ pideutb.iscoutb.dev               │ api-pideutb…     │
  │      ▼                                   ▼                  │
  │  ┌──────────┐                   ┌──────────────────┐        │
  │  │ web      │                   │ api              │◄───────┼──┐
  │  │ nginx    │                   │ uvicorn  :8000   │        │  │
  │  │ :8080    │                   └────────┬─────────┘        │  │
  │  │  64 MB   │                            │  PostgreSQL      │  │
  │  └──────────┘                            ▼  (pool, ~1 ms)   │  │
  │       192 MB ─────────────────► ┌──────────────────┐        │  │
  │                                 │ db · volumen     │        │  │
  │                                 │ pgdata · 160 MB  │        │  │
  │                                 └──────────────────┘        │  │
  │             red aislada del equipo · 512 MB en total        │  │
  └─────────────────────────────────────────────────────────────┘  │
                                                                   │
  ┌──────────────────────────────┐   HTTPS · JSON + HMAC           │
  │  Pasarela Wompi (Sandbox)    │   ASÍNCRONO, entrante ──────────┘
  └──────────────────────────────┘
```

Tres cosas que esta vista hace visibles y las anteriores no:

- **La flecha del webhook entra desde fuera.** La API tiene que ser alcanzable
  públicamente por un tercero, no solo por nuestro sitio. Eso descarta cualquier
  despliegue detrás de una red privada y obliga a que `/v1/pagos/eventos` se
  autentique por firma HMAC y no por origen
  ([ADR-0003](../adr/0003-estrategia-integracion.md)).
- **La base de datos no tiene ninguna flecha desde fuera.** El contenedor `db`
  no publica puertos: solo lo alcanza la API por la red interna del equipo. Es
  lo que la hace inalcanzable desde Internet, y también lo que obliga a sembrar
  la primera cuenta del panel desde el arranque
  ([ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md)).
- **Hay un filtro de automatismos delante de todo, y no es nuestro.**
  Cloudflare no solo resuelve el nombre: **procesa el tráfico**. Las respuestas
  llevan sus cabeceras (`Server: cloudflare`, `cf-cache-status`), y rechaza
  ciertos clientes antes de que lleguen al servidor. Medido:

  | Cliente | `GET /health` | `POST /v1/pagos/eventos` |
  |---|---|---|
  | `Python-urllib/3.13` | **403** | **403** |
  | `python-requests/2.31.0` | 200 | 401 |
  | `Go-http-client/2.0` | 200 | 401 |
  | navegador | 200 | 401 |

  No es por ritmo: **una sola petición** con ese agente basta. Está en esta
  vista porque tiene una consecuencia que ningún diagrama anterior dejaba ver:
  el webhook es la única ruta por la que **un tercero tiene que alcanzarnos**, y
  hay un filtro en medio que no controlamos ni configuramos. Ver el fallo 9 de
  [§6.7](#fallos-parciales).

  *(La documentación de la plataforma describe este registro como «DNS only».
  Lo medido dice que el tráfico sí pasa por el proxy. Se consigna lo observado,
  no para contradecir a nadie sino porque el análisis de fallos depende de cuál
  de las dos cosas sea cierta.)*

- **Sitio y API siguen siendo dos orígenes distintos**, ahora dos subdominios.
  Por eso hace falta CORS (`app/main.py`), con la lista de orígenes por variable
  de entorno y nunca `*`. Se intentó unificarlos bajo un solo host para eliminar
  esa necesidad; la plataforma no lo admite (ADR-0008 §3).

<a id="despliegue-entorno"></a>

### 7.3 Lo que impone el entorno

Restricciones que **ya cambiaron el código o la operación**. Son propiedades del
despliegue, no del diseño, y quien lea solo las secciones 5 y 6 no las vería:

| Restricción del entorno | Qué obligó a hacer | Dónde está |
|---|---|---|
| **512 MB para todo el equipo** | Repartir el presupuesto pieza por pieza: api 192 · db 160 · web 64, y dejar 96 sin asignar a propósito | [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml) |
| **Sin copia de seguridad garantizada de los volúmenes** | La semilla deja de ser un adorno y pasa a ser el procedimiento de recuperación. Y la primera cuenta se siembra al arrancar, porque un despliegue limpio no deja a nadie dentro | `migraciones/002_datos_semilla.sql`, `scripts/sembrar_usuario_inicial.py` |
| **La base no es alcanzable desde fuera** | `crear_usuario.py` no sirve contra producción: el alta inicial va por variables de entorno | `scripts/sembrar_usuario_inicial.py` |
| **El disco del contenedor es efímero** | Los logs van a salida estándar, nunca a un archivo | `app/observabilidad.py` |
| **Las migraciones tienen que correr solas** | El arranque aplica el esquema antes de escuchar, y si falla el contenedor no arranca | `backend/entrypoint.sh` |
| La plataforma enruta según el chequeo de salud | `/health` sondea dependencias de verdad y devuelve `503` | `app/salud.py` |
| 2 compilaciones simultáneas para 23 equipos | Un despliegue puede quedar en cola; se despliega con margen | §7.6 |

**Lo que dejó de imponer el entorno.** El despliegue anterior dormía el servicio
tras 15 minutos sin tráfico y tardaba **42,4 s** en volver, lo que incumplía
[ESC-03](#esc-03). Aquí los contenedores no duermen. Esa fila desapareció de
esta tabla, y con ella el único escenario que el sistema no cumplía.

La pantalla de aviso de arranque en frío sigue en `sitio/index.html`: ya no hace
falta, pero tampoco molesta, y quitarla sería trabajo sin beneficio mientras el
código pueda volver a desplegarse en un plan que sí duerma.

<a id="despliegue-limites-iac"></a>

### 7.4 Qué está declarado y qué no

**El sistema entero está en un archivo**:
[`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml), con un `Dockerfile`
por pieza. Eso es un cambio respecto del despliegue anterior, donde cuatro de
cinco piezas estaban en Terraform y la API se creaba a mano porque el proveedor
no sabía gestionar el plan gratuito.

Lo que **sigue** en Terraform es la protección de rama de GitHub
([`infra/github.tf`](../../infra/github.tf)), que no depende de dónde corra el
sistema.

Lo que **ya no se usa** son `infra/render.tf` e `infra/supabase.tf`. Se
conservan porque son la evidencia de la semana 8 y el historial de una decisión
real, pero describen infraestructura que este proyecto ya no tiene: ver la
advertencia en [`infra/README.md`](../../infra/README.md) antes de ejecutar
nada ahí.

**Los secretos no están declarados en ninguna parte**, y eso es deliberado. El
estado de Terraform guarda en claro todo lo que gestiona, y un compose
versionado se lee en GitHub. Los valores viven en el panel de la plataforma y
llegan por variable de entorno; el compose solo los referencia con `${...}`. Es
la lección de [V-11](../violaciones.md#v-11) convertida en estructura.

<a id="despliegue-observabilidad"></a>

### 7.5 Cómo se sabe que está vivo

| Señal | Dónde se consulta | Qué responde |
|---|---|---|
| `GET /health` | `https://api-pideutb.iscoutb.dev/health`, y la plataforma cada 30 s | Si cada dependencia sondeada responde. `503` si alguna no |
| `GET /metricas` | `https://api-pideutb.iscoutb.dev/metricas` | p50, p95 y máximo por operación, sobre la ventana de peticiones recientes |
| Logs JSON | Panel de la plataforma, por contenedor | Una línea por petición con `request_id`, `status` y `duration_ms` |
| Estado de los contenedores | Panel de la plataforma | `healthy` / `unhealthy` por contenedor |

Los tres primeros tienen el mismo límite declarado: **miden un proceso**. La
ventana de latencias se reinicia con el servicio y no se comparte entre
réplicas. Es suficiente para responder «¿cómo va ahora mismo?» y no pretende ser
un sistema de métricas.

El cuarto es nuevo en esta vista y se gana su fila por un motivo concreto: **la
plataforma no enruta tráfico hacia un contenedor que no esté sano**. Un
contenedor que corre perfectamente pero cuyo chequeo falla queda invisible para
el proxy, y lo que se ve desde fuera es un `404` —no un `502`—, que no sugiere
en absoluto que el problema sea la salud. Ocurrió, y costó una tarde (§7.6).

<a id="despliegue-deuda"></a>

### 7.6 Deuda conocida de esta vista

| # | Qué falta | Consecuencia |
|---|---|---|
| 1 | **Los volúmenes no se respaldan** | Perder el volumen borra pedidos, pagos y cuentas. Se recupera el esquema y la semilla al arrancar; lo demás no vuelve |
| 2 | **La configuración del despliegue no se puede probar antes de desplegar** | No hay Docker en la máquina de desarrollo, así que `docker compose up` no es una opción y los fallos de configuración solo aparecen en el servidor. Ver abajo |
| 3 | No hay entorno de pruebas separado | El entorno `development` del panel existe y está vacío: se despliega contra el mismo entorno que se demuestra |
| 4 | No hay alerta automática | El `503` lo ve la plataforma, pero nadie recibe aviso: hay que mirar |
| 5 | Un cambio de dominio exige recrear el contenedor | `Deploy` no basta si la definición del servicio no cambió; hace falta `Rebuild`. Se olvida, y el síntoma es un `404` que parece un problema de enrutado |
| 6 | **Una migración aplicada es inmutable, comentarios incluidos** | Su huella vive **solo en la base de producción**, así que editarla pasa todas las pruebas y tumba el contenedor en el siguiente despliegue. Ocurrió el 18/10/2026: media hora de API caída por corregir un comentario. Mitigado en CI desde entonces — ver abajo |

**La deuda número 2 merece su propio párrafo**, porque es la que más costó. El
despliegue de la semana 11 se encontró **cinco defectos que las 282 pruebas no
podían ver**, todos en configuración y ninguno en código:

| Defecto | Síntoma | Por qué las pruebas no lo veían |
|---|---|---|
| CORS sin `Authorization` ni `DELETE` | Panel roto en el navegador | `TestClient` no hace *preflight* |
| `log_format` dentro de `server` en nginx | El contenedor reiniciaba en bucle | Configuración de nginx, no código |
| `add_header` sin heredar en el panel | `X-Frame-Options` ausente, sin síntoma | idem |
| `wget --tries` en un healthcheck de Alpine | `404` de Traefik con nginx sano | idem |
| `crear_usuario.py` reventaba tras crear la cuenta | Traceback engañoso | Nadie lo ejecutaba en CI |

**La mitigación es barata y conocida**: instalar Docker en la máquina de
desarrollo. Los cinco se habrían visto en treinta segundos con un
`docker compose --env-file deploy/.env -f deploy/compose.lab.yaml up --build`,
que es exactamente lo que el servidor ejecuta.

Que no esté hecho es una decisión pendiente, no un olvido: está aquí para que se
decida, no para que se herede.

#### La deuda 6 costó una caída, y la lección no es la obvia

El 18/10/2026, al reconciliar la documentación con la plataforma real, se
corrigió un comentario de `001_esquema_inicial.sql`: el que justificaba el punto
débil del rollback con las copias automáticas de Supabase, que ya no se usa.

Un comentario. Las 323 pruebas pasaron, el Quality Gate pasó, el PR se fusionó —
y el contenedor de la API entró en bucle de reinicio:

```
ERROR: '001_esquema_inicial.sql' ya se aplicó pero su contenido cambió.
```

`scripts/migrar.py` guarda un `sha256` de cada migración aplicada y se niega a
arrancar si el archivo cambió. **Es una buena guardia y funcionó.** El problema
es dónde: la huella existe solo en la base de datos de producción, así que la
comprobación únicamente podía fallar allí. Todas las rutas de la API devolvieron
el `404` de Traefik durante media hora, mientras el sitio seguía en pie — lo que
hacía el síntoma más confuso todavía.

Tres cosas que esto deja:

- **La guardia tenía que estar en CI, y ahora lo está.** Las huellas se fijan en
  `backend/tests/test_migraciones.py`, comprobado contra el cambio exacto que
  provocó la caída. La detección pasa de producción al `push`.
- **Una prueba puede pedir el cambio que rompe el sistema.** La regla de la S13
  que vigila menciones a la plataforma abandonada incluía `backend/migraciones`
  entre sus ámbitos: exigía justamente esa corrección. Ya no los incluye, y el
  motivo está escrito donde se podría volver a añadir.
- **Aquí la documentación se queda inexacta a propósito.** El comentario sobre
  Supabase de esa migración no se puede corregir sin romper el arranque, así que
  es el único sitio del repositorio donde una afirmación vieja tiene que
  permanecer. La corrección vive en esta sección y en
  [ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md).

#### El caso espejo, encontrado en la S14

El patrón de la deuda 2 es «la prueba y la realidad no recorren el mismo
camino». Verificando la S14 apareció su reflejo, que es igual de incómodo: **la
prueba y la terminal de quien la ejecuta recorrían el mismo camino cuando no
debían.**

Con `PIDEUTB_DATABASE_URL` definida en el entorno —lo normal mientras se
desarrolla contra una base real— **ocho casos fallaban**. No por un defecto del
código: sus fixtures aíslan cada caso vaciando el almacenamiento en memoria, y
con esa variable puesta la aplicación usa PostgreSQL, de modo que la limpieza no
limpiaba nada y el estado se filtraba de un caso al siguiente.

Es el peor tipo de prueba intermitente, porque el síntoma **viaja con la persona
y no con el repositorio**: quien tuviera la variable exportada veía ocho fallos
en tres archivos sin relación aparente, y quien no, ninguno.

`backend/tests/conftest.py` retira la variable **al importarse**, antes de que
cualquier módulo de prueba importe la aplicación. Se hace así y no con un
fixture porque un fixture dependería del orden en que pytest los instancia, y
equivocarse ahí tiene un modo de fallo peor que el problema: las pruebas de
PostgreSQL correrían contra memoria y **pasarían**, sin probar lo que dicen
probar. `backend/tests/test_aislamiento.py` vigila las dos mitades.

<a id="seccion-8"></a>
<a id="lenguaje-ubicuo"></a>

## 8. Conceptos transversales

### 8.1 Lenguaje ubicuo

El vocabulario del dominio se audita periódicamente contra el código y contra
esta misma documentación, para detectar términos que significan cosas distintas
según quién los use. El detalle de la auditoría, con la tabla completa de
términos ambiguos y su resolución, está en
[`docs/ddd-contextos.md` §1](../ddd-contextos.md).

Dos aclaraciones vigentes desde la semana 6, ambas surgidas de contradicciones
reales encontradas dentro de la documentación del equipo:

- **«Usuario»** se reserva para estudiante o profesor, como ya decía el
  [glosario](#glosario). El concepto más amplio —cualquier cuenta autenticada,
  incluidos el establecimiento y el administrador— se llama **«Cuenta»**, y es
  la responsabilidad del módulo `usuarios` descrita en
  [§5.3](#responsabilidad-modulos).
- **«Carrito»** es sinónimo de «pedido en estado `pendiente_pago`», no una
  entidad separada. No existe ni existirá un modelo `Carrito` mientras el pedido
  se cree con un único ítem confirmado.

Los términos del dominio, con el lugar del código donde vive cada uno:

| Término | Significado | Dónde vive en el código |
|---|---|---|
| **Cuenta** | Cualquier actor autenticado: usuario, establecimiento o admin | `usuarios` |
| **Usuario** | Estudiante o profesor que compra | `usuarios` (pendiente) |
| **Establecimiento** | Punto de venta del campus; es un tipo de Cuenta | `usuarios.models.Establecimiento` |
| **Ítem de menú** | Producto que un establecimiento ofrece, con precio y disponibilidad del día | `menu.models.ItemMenu` |
| **Pedido** | Solicitud de compra de un ítem, con el importe congelado | `pedidos.models.Pedido` |
| **Carrito** | Sinónimo de pedido en estado `pendiente_pago` | — (no es una entidad) |
| **Instantánea** | Copia de un dato del catálogo congelada al comprar, que no se revalúa | `Pedido.nombre_item`, `precio_unitario`, `total` |
| **Código de canje** | Credencial de un solo uso que acredita un pedido pagado | `pagos` (pendiente) |

### 8.2 Contextos delimitados y propiedad de datos

El sistema se organiza en cuatro **contextos delimitados** —Catálogo, Pedidos,
Pagos y Cuentas— que coinciden uno a uno con los módulos de dominio de
`backend/app/`. La auditoría no encontró ningún límite que exigiera un módulo
adicional. El mapa completo, con el patrón de cada relación
(customer/supplier y anticorruption layer) y la justificación de cada frontera,
está en [`docs/ddd-contextos.md` §2](../ddd-contextos.md).

La regla transversal que los sostiene: **cada dato tiene exactamente un módulo
que lo escribe; los demás lo leen o lo solicitan**. La tabla de propiedad de
datos está en el mismo documento §3.

La única brecha detectada —los datos de `Establecimiento`, sin dueño hasta esta
entrega— se resolvió en
[ADR-0002](../adr/0002-propiedad-datos-establecimiento.md): el módulo `usuarios`
es su único escritor, modelándolo como un tercer tipo de cuenta.

Ningún módulo importa el `repository` ni los `models` de otro: solo su `service`
y su `contracts`. Esto no es una convención confiada a la disciplina del
equipo —`backend/tests/test_modularidad.py` la verifica en cada push y falla la
construcción si alguien la rompe.

### 8.3 Lenguaje publicado en las fronteras

Las funciones públicas de un contexto responden con tipos de su módulo
`contracts`, nunca con sus entidades internas. Así el modelo interno puede
evolucionar sin arrastrar a los consumidores, y ningún tipo de un contexto
aparece dentro de otro.

Para los sistemas externos la protección es más fuerte: la integración con Wompi
se traducirá mediante una **anticorruption layer**, porque su modelo es ajeno y
puede cambiar sin previo aviso. Entre contextos internos no se usa, porque su
coste de mantenimiento no se justifica cuando ambos lados los escribe el mismo
equipo.

### 8.4 Manejo de errores

Cada contexto expresa sus fallos con excepciones propias de dominio
(`ItemNoEncontradoError`, `ItemNoDisponibleError`,
`EstablecimientoInactivoError`). El `router` es el único que las traduce a
códigos HTTP, de modo que la lógica de negocio no conoce el protocolo:

| Situación | Excepción de dominio | HTTP |
|---|---|---|
| El ítem no existe | `ItemNoEncontradoError` | `404` |
| El ítem no está disponible | `ItemNoDisponibleError` | `409` |
| El establecimiento no opera | `EstablecimientoInactivoError` | `409` |
| Datos de entrada inválidos | *(validación de Pydantic)* | `422` |

Un error específico en lugar de un `500` genérico es lo que permite que un
usuario nuevo entienda qué pasó y corrija sin ayuda, que es la medida de
[ESC-01](#esc-01).

------------------------------------------------------------------------

<a id="idempotencia"></a>

### 8.5 Idempotencia

Es un concepto transversal y no un detalle de `pagos` porque **lo impone el
contrato, no la implementación**: `asyncapi.yaml` declara que el canal de la
pasarela entrega **al-menos-una-vez**, y una entrega al-menos-una-vez
convierte «el mismo aviso llegará repetido» en una certeza, no en un riesgo.

Un sistema que no lo asume genera dos códigos de canje para un pedido, o dos
cobros para una compra.

#### Los tres mecanismos, y qué garantiza cada uno

| # | Dónde | Clave de idempotencia | Mecanismo | Qué pasa al repetir |
|---|---|---|---|---|
| 1 | `pedidos.confirmar_pago` | `pedido_id` | `UPDATE ... WHERE estado = 'pendiente_pago'` | La segunda no encuentra fila; devuelve `ya_estaba_pagado = True` |
| 2 | `pagos.procesar_evento` | `referencia_pago` | La referencia la generamos nosotros y se busca antes de actuar | Responde `202` con `duplicado: true` |
| 3 | `pagos.iniciar_intento` | `pedido_id` | Devuelve el intento pendiente existente en vez de abrir otro | El usuario vuelve al mismo `url_checkout` |

#### El primero es el que sostiene a los otros dos

```python
confirmado = repository.marcar_pagado(pedido_id, _generar_codigo_canje())
if confirmado is None:
    return _publicar(repository.buscar_por_id(pedido_id)), True
```

La condición **viaja dentro del `UPDATE`**, no en un `if` previo. La diferencia
no es de estilo:

Con leer–decidir–escribir, dos avisos del mismo pago que lleguen a la vez a dos
trabajadores distintos **ven los dos «pendiente»** y los dos generan código. El
resultado son dos códigos válidos para un pedido, y el segundo sobrescribe al
primero — de modo que el cliente que ya vio el suyo en pantalla se queda con uno
que no sirve.

Con la condición dentro del `UPDATE`, PostgreSQL serializa: la segunda
actualización no encuentra fila que cumplir y devuelve `None`. **La base de
datos es el árbitro**, y no hace falta coordinación entre procesos.

Está probado en las dos implementaciones del repositorio
(`test_marcar_pagado_dos_veces_devuelve_none_la_segunda`), lo que importa porque
la de memoria podría cumplirlo por casualidad y la de PostgreSQL es la que corre
en producción.

#### Lo que *no* es idempotente, a propósito

`pedidos.avanzar_estado` **no lo es**: repetir una transición devuelve `409`.

Es deliberado. Esa operación la dispara una persona pulsando un botón, no un
sistema reintentando, y en ese contexto el `409` es información útil — significa
«otra persona ya movió este pedido», que es justo lo que quien atiende necesita
saber. Hacerla idempotente convertiría un aviso útil en silencio.

La regla general que se sigue: **idempotente donde la entrega es
al-menos-una-vez; explícito donde hay alguien mirando.**

#### Por qué no hay saga

Una saga coordina una secuencia de escrituras en **sistemas distintos**, donde
no existe una transacción común, y compensa las ya hechas cuando una falla.

En este sistema no hay tal cosa. Las escrituras de un cobro van todas a la misma
base de datos: `pedidos` y `pagos_intentos` son dos tablas del mismo PostgreSQL.
Cuando una secuencia queda a medias —y
[§6.7](#fallos-parciales) documenta que puede— **no falta un coordinador: falta
una transacción**. Llamarlo saga sería ponerle un nombre grande a un problema
local, y además uno que sugiere una solución desproporcionada.

Lo que haría falta una saga es que algún contexto se extrajera a un servicio
propio con su propia base. Esa decisión está evaluada y descartada en
[ADR-0009](../adr/0009-no-extraer-un-servicio.md), que incluye lo que costaría
—entre otras cosas, exactamente esto— si algún día se toma.

---

<a id="consistencia"></a>

### 8.6 Consistencia por operación

#### Lo primero: dónde NO hay consistencia eventual

El sistema tiene **una sola base de datos, sin réplicas de lectura**. Todas las
escrituras y todas las lecturas van al mismo PostgreSQL, por el mismo pool.

De ahí se sigue algo que conviene decir antes de la tabla, porque es la respuesta
a la mitad de las preguntas: **las diez operaciones de dominio son fuertemente
consistentes**. Una lectura posterior a una escritura confirmada ve esa escritura,
siempre, sin ventanas. No hay réplica que alcanzar ni caché que invalidar.

Las otras dos del contrato —`/health` y `/metricas`— no leen la base en absoluto,
y la segunda por eso no tiene garantía que dar: se explica más abajo, porque es
menos trivial de lo que parece.

Eso no es una virtud del diseño: es una consecuencia del tamaño del sistema, y
vale mientras lo siga siendo. Lo que lo cambiaría está al final de la sección.

#### La tabla

| Operación | Garantía | Concurrencia | Notas |
|---|---|---|---|
| `GET /v1/menu/items/{id}` | **Fuerte** | — | Lectura directa |
| `GET /v1/menu/establecimientos/{id}/items` | **Fuerte** | — | Orden estable fijado en el repositorio, no por el almacenamiento |
| `POST /v1/pedidos` | **Fuerte**, atómica | El identificador lo asigna la secuencia de la base | El precio se congela en el pedido: una subida posterior no reescribe lo ya pedido |
| `GET /v1/pedidos/{id}` | **Fuerte** · lee-lo-que-escribiste | — | Lo que el cliente ve desfasado es por el sondeo, no por el almacén (abajo) |
| `GET /v1/pedidos` | **Fuerte** | — | Filtrada por el establecimiento de la sesión |
| `POST /v1/pedidos/{id}/estado` | **Fuerte**, atómica | `UPDATE ... WHERE estado = <el esperado>` | **No idempotente a propósito**: repetir da `409`, que es información útil para quien atiende |
| `POST /v1/pagos/intentos` | **Fuerte** · **idempotente por pedido** | Restricción única: un solo intento pendiente por pedido | Pulsar «Pagar» dos veces devuelve el mismo intento |
| `POST /v1/pagos/eventos` | **Al-menos-una-vez** entrante · **idempotente por referencia** | `UPDATE ... WHERE estado = 'pendiente_pago'` | La única operación con entrega repetida garantizada. Ver [§8.5](#idempotencia) |
| `POST` / `DELETE /v1/sesiones` | **Fuerte** | El cierre borra **una** sesión, no todas las del usuario | — |
| `GET /health` | **Fuerte** · del proceso | — | No consulta la base: responde si *este* proceso vive |
| `GET /metricas` | **Ni fuerte ni eventual: no es estado compartido** | — | La única del contrato que no sale de la base (abajo) |

Dos filas merecen ampliarse, y son las dos que menos lo parecen.

#### `GET /metricas` no tiene garantía de consistencia, y no es un descuido

Las otras once operaciones responden en función de lo que hay en PostgreSQL. Esta
no: los percentiles los acumula **una ventana en la memoria del proceso** que
atiende la petición. De ahí se siguen tres cosas que conviene decir, porque
afectan a cómo se usan los números de esta misma sección:

- **Se pierden al reiniciar.** Un despliegue pone el contador a cero. Las cifras
  medidas aquí valen para la ventana en que se tomaron, y por eso se anotan con
  su `n` y su fecha en vez de como constantes del sistema.
- **No son agregables.** Hoy hay un solo proceso, así que la pregunta no se
  plantea; el día que hubiera dos, cada uno respondería lo suyo y `p50` dejaría
  de significar «el p50 del sistema» sin que nada avisara.
- **Por eso mismo sirven para lo que se usan aquí**: comparar el tiempo de
  servidor con la ida y vuelta vista desde fuera. Para eso basta un proceso.

Es la única operación del sistema donde «¿a qué instancia pregunté?» cambiaría la
respuesta. Hoy no hay dos instancias, pero el día que las haya este endpoint es
lo primero que miente — y mentiría en silencio.

#### El desfase que el usuario percibe no está en los datos

El panel del mostrador refresca su cola **cada 8 segundos**, y la pantalla del
cliente consulta su pedido **cada 3** mientras espera el pago.

Eso significa que lo que una persona ve puede estar hasta 8 segundos
desactualizado. Es fácil llamar a eso «consistencia eventual» y sería **falso**:
el almacén responde el dato correcto en cada consulta. Lo que está desfasado es
**la última vez que alguien preguntó**.

La distinción no es académica, porque las dos cosas se arreglan en sitios
distintos:

| | Dónde vive | Cómo se reduce |
|---|---|---|
| Desfase de sondeo | `sitio/panel.js`, `sitio/config.js` | Bajar el intervalo, o empujar desde el servidor |
| Consistencia eventual | El almacenamiento | No se puede «bajar»: se diseña alrededor |

Hoy el sistema **no tiene** lo segundo. Confundirlos llevaría a resolver con
arquitectura un problema que es un número en un archivo de configuración.

#### Estrategia de caché: no hay, y el motivo es un número

La pregunta no es si una caché *ayudaría* —casi siempre ayuda algo— sino
**cuánto**, comparado con lo que cuesta.

Medido contra el despliegue el 18/10/2026, sobre `GET /v1/menu/establecimientos/1/items`:

| | |
|---|---|
| Ida y vuelta completa, desde fuera | **328 ms** (p50, n=12; mín. 281, máx. 775) |
| De eso, tiempo de servidor (`/metricas`) | **1,79 ms** (p50, n=26) |
| Proporción | **0,55 %** |

Una caché de aplicación optimiza el tiempo de servidor. Aunque fuera perfecta
—cero milisegundos— llevaría la experiencia de 328 ms a 326. **Eso no se percibe,
y de hecho no se distingue del ruido**: la propia medición varía entre 281 y 775
ms. Los otros 326 ms son red, TLS y el proxy, y ninguna caché nuestra los toca.

Y lo que costaría sí es real: **invalidación**. Una carta cacheada que no se
invalida al cambiar un precio muestra precios viejos, y un pedido creado contra
un precio viejo es una discrepancia con dinero de por medio. Se estaría
cambiando un problema que no existe por uno que sí.

**La operación más lenta del sistema es `POST /v1/sesiones`, con 37,15 ms de p50**
(n=24, p95 48,74), y es lenta por diseño: es scrypt derivando la contraseña
([ADR-0007](../adr/0007-autenticacion-del-panel.md)). Cachear eso sería desarmar
la defensa que hace caro probar contraseñas — es el único sitio del sistema donde
**tardar es la función**, no un costo.

*(Ese 37 ms dejó al descubierto otra cosa, que no es de esta semana pero se
anota donde se encontró: ADR-0007 eligió el parámetro de coste midiendo **100 ms
en el portátil de desarrollo**, y el servidor hace la misma derivación en unos
35. La defensa en producción vale, medida, bastante menos de lo que el ADR
sugiere. Se trata en [§11](#riesgos), con los números.)*

**Decisión: ninguna caché de aplicación.** Lo que sí hay es lo que no cuesta
nada:

- `config.js` se sirve con `no-cache`: lleva la dirección de la API y un
  navegador que lo guarde seguiría llamando a donde la API ya no está.
- El resto de estáticos los cachea el navegador con las cabeceras por defecto de
  nginx, que es suficiente para tres archivos.

**Qué cambiaría esta decisión**, y es comprobable sin discutirlo: que el tiempo
de servidor deje de ser el 0,5 %. `GET /metricas` publica el p50 y el p95 por
operación, así que basta compararlo con la ida y vuelta medida desde fuera. El
día que el servidor sea una fracción apreciable, la caché pasa a tener algo que
optimizar.

#### Qué cambiaría la fila de arriba del todo

La consistencia fuerte de todas las operaciones depende de que haya **una sola
base sin réplicas**. Dejaría de ser cierta si:

- Se añadiera una réplica de lectura para repartir carga. Ahí aparecería el
  desfase de replicación, y las lecturas tendrían que elegir entre fresca y
  barata.
- Se extrajera un contexto a un servicio con base propia — evaluado y descartado
  en [ADR-0009](../adr/0009-no-extraer-un-servicio.md), precisamente porque
  convertiría una transacción local en una saga.
- Se añadiera una caché, que es una réplica con otro nombre.

Las tres están hoy descartadas con su motivo, y las tres tienen el mismo
síntoma: lo que hoy se puede afirmar en una línea pasaría a necesitar una
tabla por operación.

---

<a id="amenazas"></a>

### 8.7 Modelo de amenazas (STRIDE)

#### Por qué STRIDE y no una lista de riesgos

Una lista de riesgos contiene lo que se nos ocurrió. STRIDE obliga a hacer
**seis preguntas a cada elemento**, y el valor está en las que se contestan
«esto no lo habíamos pensado». De las dieciocho filas de abajo, tres salieron
así, y una de ellas es la más grave del sistema.

El inventario de elementos y fronteras es el de [§7.2](#despliegue-topologia).
Lo que importa para este análisis es que hay **tres fronteras de confianza** y
no cuatro:

| Frontera | Quién está al otro lado | Qué la protege |
|---|---|---|
| Navegador → API | Cualquiera en Internet | CORS, sesiones, autorización por establecimiento |
| Pasarela → API (webhook) | Un tercero, por una ruta pública | Firma HMAC, y falla en cerrado sin secreto |
| Panel de Dokploy → contenedores | Quien tenga esa cuenta | Nada nuestro: es la plataforma |
| ~~API → base de datos~~ | — | **Dejó de cruzar la red** con ADR-0008 |

La cuarta se tachó esta semana 11 y conviene recordarlo aquí: mientras la base
estuvo en Supabase, cada consulta salía a Internet. Hoy es un contenedor vecino
en una red privada, y eso **elimina** una clase entera de amenazas en lugar de
mitigarla.

#### S — Suplantación de identidad

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| S-1 | Alguien se hace pasar por la pasarela y marca pedidos como pagados | Firma HMAC sobre el cuerpo. **Sin secreto la API se niega a arrancar la verificación**, no la salta ([V-11](../violaciones.md#v-11)) | `test_un_evento_sin_firma_valida_se_rechaza` · `test_una_firma_hecha_con_otro_secreto_no_sirve` · `test_firmar_se_niega_en_vez_de_usar_una_cadena_vacia` |
| S-2 | Alguien se hace pasar por personal del mostrador | Token de sesión de 32 bytes de `secrets`, guardado **hasheado**: una fuga de la tabla no da acceso | `test_el_token_se_guarda_hasheado_y_no_en_claro` · `test_un_token_inventado_no_abre_nada` · `test_dos_tokens_seguidos_no_se_repiten` |
| S-3 | Reutilizar un evento válido capturado | No hay marca de tiempo ni nonce en la firma, así que **se puede repetir**. No importa: el efecto es idempotente por referencia, y el segundo intento no genera un segundo código | `test_el_mismo_evento_repetido_no_genera_un_segundo_codigo` |
| S-4 | Una sesión caducada o de un usuario dado de baja sigue sirviendo | La consulta de sesión exige `expira_en > now()` **y** `u.activo` en la misma cláusula | `test_una_sesion_caducada_no_sirve` · `test_un_usuario_desactivado_no_puede_entrar` |

S-3 es la fila que se contesta «no está mitigado y no hace falta». Vale
escribirla porque la respuesta no es evidente: lo que hace inofensiva la
repetición no es una defensa contra repetición, es la idempotencia que se
construyó por otro motivo ([§8.5](#idempotencia)).

#### T — Manipulación de datos

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| T-1 | El cliente manipula el precio de lo que pide | El precio **no viaja en la petición**: se lee del catálogo y se congela en el pedido ([V-06](../violaciones.md#v-06)) | `test_el_pedido_conserva_el_precio_aunque_cambie_el_catalogo` |
| T-2 | El cliente elige a qué establecimiento va su pedido | Se deriva del ítem, no del cuerpo ([V-01](../violaciones.md#v-01)) | `test_establecimiento_se_deriva_del_item_y_no_del_cliente` |
| T-3 | El mostrador marca un pedido como pagado sin cobro | `confirmar_pago` **no está expuesta**: la única vía es el webhook firmado | `test_el_mostrador_no_puede_marcar_un_pedido_como_pagado` |
| T-4 | Inyección de SQL | Todos los valores viajan como parámetros. Las dos consultas con `f-string` interpolan `_COLUMNAS`, que es una **constante literal del módulo**, nunca entrada | Revisado en la S13; no hay concatenación de entrada |
| T-5 | Una dependencia alterada en el camino | `--require-hashes --only-binary=:all:` en la imagen y en CI | Job `dependencias` del pipeline |
| T-6 | Escucha o alteración entre la API y la base | Red privada de contenedores, sin publicar puertos. **No hay TLS**, y no se añade: dejó de cruzar Internet | `deploy/compose.lab.yaml` — solo `expose`, nunca `ports` |

#### R — Repudio

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| R-1 | **Nadie puede decir qué persona avanzó un pedido** | **Ninguna.** `avanzar_estado` recibe `establecimiento_id`, no el usuario: el sistema sabe *qué mostrador* movió un pedido, no *quién* | — |

Es una de las tres que aparecieron por preguntar. Y es relevante, no formal: el
`codigo_canje` **da derecho a comida**, y la transición a `entregado` es el
momento en que ese derecho se consume. Si un pedido aparece entregado y el
cliente dice que no lo recogió, hoy no hay forma de saber quién lo marcó.

No se corrige esta semana. Añadir el usuario a la transición toca la firma de
`avanzar_estado`, el repositorio, el esquema y el contrato, y es un cambio de
modelo de datos, no un endurecimiento. Queda como [R-08](#riesgos) con su coste.

#### I — Revelación de información

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| I-1 | Enumerar los pedidos de otro establecimiento | **`404`, no `403`**: un `403` confirmaría que el pedido existe. En la cola sí es `403`, porque ahí no hay nada que enumerar | `test_avanzar_el_pedido_de_otro_establecimiento_da_404` · `test_el_personal_que_pide_otro_recibe_403` |
| I-2 | Averiguar qué correos tienen cuenta | Un solo `401` para correo inexistente y contraseña errada, **y derivación contra un hash de descarte** para que los tiempos no hablen | `test_una_contrasena_incorrecta_y_un_correo_desconocido_dan_el_mismo_error` |
| I-3 | Otro origen lee respuestas del panel | CORS con lista explícita, sin comodín y sin credenciales automáticas | `test_un_origen_cualquiera_no_recibe_permiso` · `test_no_hay_comodin_de_origen` · `test_no_se_permiten_credenciales_automaticas` |
| I-4 | El código de canje o una contraseña acaban en los registros | Nada sensible se registra. El guion de alta **no imprime** la contraseña | `test_el_sembrado_no_imprime_la_contrasena` · revisado en la S13: ningún `_LOG` toca código, token ni secreto |
| I-5 | El secreto de la pasarela en el repositorio | Guardia automática en CI, además de la rotación de [V-11](../violaciones.md#v-11) | `test_el_secreto_no_aparece_en_el_codigo_fuente` · `test_el_guardia_de_secretos_detecta_lo_que_dice_detectar` |
| I-6 | El token de sesión en `sessionStorage` lo lee un XSS | Aceptado y documentado en [V-12](../violaciones.md#v-12). Acotado: el panel no renderiza HTML de terceros, y la sesión muere al cerrar la pestaña | — |
| I-7 | **`GET /metricas` es público** | **Ninguna.** Publica p50, p95, máximo y número de muestras por operación a quien lo pida | — |

I-7 es la segunda que apareció por preguntar. Lo que revela es modesto —el
inventario de operaciones ya está en `openapi.yaml`, que es público a propósito—
pero el **volumen de tráfico** no estaba publicado en ninguna parte, y es
información del negocio: cuántos pedidos se hacen y a qué horas.

No se cierra todavía porque cerrarlo tiene un coste concreto: `/metricas` es la
fuente de las mediciones de [§8.6](#consistencia) y del seguimiento de ESC-02, y
hoy se consulta sin credenciales desde fuera. Ponerle sesión significa decidir
quién la tiene. Queda como [R-09](#riesgos).

#### D — Denegación de servicio

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| DoS-1 | **Agotar la CPU pidiendo iniciar sesión** | **Ninguna nuestra.** Ver abajo: es la más grave del modelo | — |
| DoS-2 | Agotar el pool de conexiones | `TIMEOUT_POOL_S = 5`: la petición se rinde en vez de encolarse para alguien que ya se fue | `base_de_datos.py` |
| DoS-3 | Saturar la base con conexiones | `max_connections=30` contra un pool que abre 5 como máximo | `deploy/compose.lab.yaml` |
| DoS-4 | Tumbar un contenedor | `restart: unless-stopped` en los tres, y chequeos de salud que impiden enrutar a uno que no responde | `deploy/compose.lab.yaml` |

##### DoS-1, en detalle: dos defensas que se estorban

Es la tercera que apareció por preguntar, y la única del modelo que calificaría
como grave. Sale de juntar tres hechos que, por separado, son decisiones
correctas:

1. **`POST /v1/sesiones` es caro a propósito.** Deriva scrypt, y eso cuesta unos
   35 ms de CPU en producción. Es la defensa de [ADR-0007](../adr/0007-autenticacion-del-panel.md)
   contra probar contraseñas en serie.
2. **No hay límite de intentos.** Declarado en ese mismo ADR: hacerlo bien exige
   almacenamiento compartido entre instancias.
3. **El contenedor tiene 0,5 CPU de tope** ([ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md)).

La aritmética:

```
0,5 CPU  =  500 ms de CPU por segundo de reloj
          ÷ 35 ms por derivación
          ≈ 14 peticiones por segundo saturan el contenedor
```

Catorce. Y lo que lo convierte de molestia en amenaza es el detalle que ninguna
de las tres decisiones anticipó: **el atacante no necesita una cuenta.** La
defensa contra ataques de tiempo (I-2) deriva contra un hash de descarte cuando
el correo no existe, así que un correo inventado cuesta **lo mismo** que uno
real.

Dicho de otro modo: para proteger los tiempos de respuesta se hizo que cualquiera
pueda obligar al servidor a trabajar. Las dos defensas son correctas por separado
y se estorban juntas.

**Lo que hoy lo contiene es algo que no es nuestro, y que la semana 11 anotó como
un problema.** Cloudflare rechaza con `403` a los clientes que identifica como
automatismos (fallo 9 de [§6.7](#fallos-parciales)): un ataque con el cliente
HTTP por defecto de un guion no llega. Eso no es una mitigación —no la
controlamos, no la configuramos y un atacante que ponga un `User-Agent` de
navegador la pasa— pero explica por qué el riesgo es real y no ha ocurrido.

La corrección está en la S14, porque **tiene un número que medir antes**: un
límite de intentos por IP en memoria del proceso funcionaría hoy, con una sola
instancia, y dejaría de funcionar en silencio con dos — exactamente el modo de
fallo de R-03. Elegir entre eso y subir el coste de scrypt (que empeora DoS-1 en
vez de mejorarlo) exige medir las dos cosas.

#### E — Elevación de privilegios

| # | Amenaza | Mitigación | Verificada por |
|---|---|---|---|
| E-1 | Quien pueda escribir una variable de entorno se crea una cuenta | El sembrado actúa **solo con la tabla vacía**: en un sistema en marcha no hace nada | `test_el_sembrado_no_toca_un_sistema_que_ya_tiene_cuentas` · `test_el_sembrado_sin_variables_no_hace_nada` |
| E-2 | Personal de un establecimiento opera sobre otro | El establecimiento sale **de la sesión**, no del parámetro | `test_el_establecimiento_sale_de_la_sesion_y_no_del_parametro` · `test_el_personal_opera_sobre_el_suyo_lo_pida_o_no` |
| E-3 | Entregar un pedido sin presentar el código | `avanzar_estado` exige el código para pasar a `entregado`, comparado con `compare_digest` | `test_entregar_sin_el_codigo_no_se_puede` · `test_el_codigo_no_se_puede_reutilizar` |
| E-4 | Los dos roles pueden lo mismo | Cierto hoy, y **declarado** en vez de descubierto | `test_hoy_los_dos_roles_pueden_operar_el_panel` |

#### Priorización

Ordenadas por lo que de verdad pasaría, no por la categoría:

| Prioridad | Amenaza | Por qué ahí | Dónde se trata |
|---|---|---|---|
| **1** | DoS-1 · agotar la CPU con inicios de sesión | 14 peticiones por segundo tumban el servicio, sin cuenta y sin credenciales. Lo contiene un proxy ajeno | [R-07](#riesgos), S14 |
| **2** | R-1 · no se sabe quién entregó un pedido | Afecta a lo único que vale dinero: el canje. No es explotable, es **no auditable** | [R-08](#riesgos) |
| **3** | I-7 · `/metricas` público | Revela volumen de negocio. Bajo impacto, corrección con coste | [R-09](#riesgos) |
| **4** | I-6 · token en `sessionStorage` | Ya evaluado y aceptado con su acotación | [V-12](../violaciones.md#v-12) |
| **5** | S-3 · repetición de eventos | Mitigado de hecho por la idempotencia | — |

Lo que **no** está en esta lista también es resultado: de las dieciocho filas,
catorce tienen una mitigación con una prueba que la verifica. No porque se haya
trabajado en seguridad esta semana, sino porque las violaciones V-01 a V-12 de
las semanas anteriores eran, casi todas, amenazas de este modelo encontradas de
una en una.

---

<a id="datos-personales"></a>

### 8.8 Datos personales y retención

#### Lo que el sistema guarda de una persona

La respuesta es más corta de lo que suele ser, y es una propiedad de la
arquitectura y no una casualidad:

| Tabla | Dato personal | Forma |
|---|---|---|
| `usuarios` | `correo` del personal | En claro. Es el identificador de acceso |
| `usuarios` | Contraseña | **Nunca**: solo su derivación scrypt con sal propia |
| `sesiones` | Token | **Nunca**: solo su hash |
| `pedidos` | — | **Nada.** Ni nombre, ni teléfono, ni correo, ni identificador de dispositivo |

La fila que importa es la última. **Un cliente de PideUTB no es un registro: es
quien tiene un código de canje.** Pide sin cuenta, sin dejar datos y sin que el
sistema pueda relacionar dos de sus pedidos entre sí.

Eso no se decidió como política de privacidad; salió de
[ADR-0002](../adr/0002-propiedad-datos-establecimiento.md) y del alcance del
producto. Pero el efecto es que la minimización de datos no hay que
implementarla: **el dato que no se recoge no se puede filtrar, ni hay que
borrarlo, ni hay que explicar quién lo ve.**

La contrapartida, y conviene decirla: el `codigo_canje` pasa a ser un
**portador** —quien lo tenga come— así que su manejo es el control relevante.
Por eso se genera con `secrets`, es único en la tabla, y se exige al entregar.

#### Retención

| Dato | Cuánto vive | Quién lo limpia |
|---|---|---|
| `sesiones` vigentes | 8 horas (`HORAS_DE_SESION`), para cubrir un turno | Caducan solas; la consulta de sesión las descarta |
| `sesiones` caducadas | **Para siempre** | `borrar_sesiones_caducadas()` existe y **no la llama nadie** |
| `pedidos` | **Para siempre** | Nadie |
| `usuarios` | Hasta que se desactiven | Nadie; `activo = false` en vez de borrado |

Las dos filas de «para siempre» son honestas y no urgentes, por el motivo de
arriba: lo que se acumula no contiene datos de clientes. Una sesión caducada es
un hash inútil —`buscar_usuario_de_sesion` la descarta por `expira_en`— así que
es **higiene y no seguridad**, y su función lo dice en el propio docstring en vez
de dar a entender que alguien la ejecuta.

Los pedidos acumulados son, de hecho, el registro contable del sistema: borrarlos
sería perder la auditoría del dinero. Lo que falta no es borrado sino una
política escrita de cuánto conservar, y eso depende de un requisito que nadie ha
dado.

---

<a id="secretos"></a>

### 8.9 Gestión de secretos

#### Los cuatro que existen

| Secreto | Dónde vive | Quién lo ve |
|---|---|---|
| `PIDEUTB_SECRETO_PASARELA` | Entorno del panel de Dokploy | Quien tenga esa cuenta |
| `POSTGRES_PASSWORD` · `PIDEUTB_DATABASE_URL` | Ídem | Ídem |
| `PIDEUTB_USUARIO_INICIAL_CONTRASENA` | Ídem | Ídem |
| `SONAR_TOKEN` | Secretos de GitHub Actions | Quien administre el repositorio |

Ninguno está en el repositorio, y eso lo comprueba una prueba en cada push
(`test_el_secreto_no_aparece_en_el_codigo_fuente`) que a su vez tiene su propia
prueba de que sabe detectar lo que dice detectar. La historia de por qué existe
esa guardia está en [V-11](../violaciones.md#v-11): el secreto de la pasarela
**estuvo** escrito en el código.

#### Las dos propiedades que se eligieron, y valen más que la lista

**Fallar en cerrado.** Sin `PIDEUTB_SECRETO_PASARELA` la API no verifica firmas
con una cadena vacía: se niega a firmar. La diferencia es que un despliegue mal
configurado **no arranca aceptando cualquier evento**, que es el modo de fallo
que convierte un olvido en una brecha.

**Derivar y no cifrar.** Ni las contraseñas ni los tokens se guardan de forma
reversible. Cifrar implica poder descifrar, y nadie necesita recuperar una
contraseña original: solo comprobar si la que llega produce la misma derivación.
Una fuga de `usuarios` o de `sesiones` no da acceso a nada.

#### Lo que falta, y es concreto

**La contraseña inicial se queda en el panel.** `PIDEUTB_USUARIO_INICIAL_CONTRASENA`
cumple su función una sola vez —el primer arranque con la tabla vacía— y después
sigue ahí, en claro, legible para cualquiera que entre al panel. El diseño del
sembrado ya acota el daño (E-1: con la tabla poblada no hace nada), pero una
contraseña que sigue siendo válida y visible mucho después de usarse es una
credencial olvidada.

Lo correcto es cambiarla desde el panel y vaciar la variable. Y ahí aparece lo
otro:

**No hay forma de restablecer una contraseña.** Comprobado en la S13: no existe
ruta en el contrato ni guion que lo haga. `crear_usuario.py` crea cuentas y
necesita acceso a la base, que **el despliegue no concede** —la base no publica
puertos y el panel no da terminal—. Así que:

- Cambiar la contraseña inicial hoy **no se puede** sin recrear el despliegue.
- Una contraseña perdida deja el panel inaccesible por el mismo motivo.

Las dos cosas son la misma carencia, y es la que hace que la primera no se pueda
arreglar. Quedan como [R-10](#riesgos) y la deuda D-04 de la misma sección.

---

## 9. Decisiones de arquitectura

Las decisiones arquitectónicas relevantes se documentan como ADRs en
[`docs/adr/`](../adr/), siguiendo el formato estándar (contexto,
decisión, alternativas consideradas, consecuencias).

El título de cada ADR **enuncia la decisión tomada, no el tema tratado**. Un
título como «Estrategia de integración» obliga a abrir el documento para saber
qué se decidió; uno que dice qué se decidió permite leer el índice y entender la
arquitectura sin abrir nada.

| ID | Decisión | Escenario que la motiva | Estado |
|---|---|---|---|
| [ADR-0001](../adr/0001-estilo-arquitectonico.md) | Adoptar un monolito modular en el que un módulo solo invoca la interfaz pública de otro | [ESC-01](#esc-01) | Aceptada |
| [ADR-0002](../adr/0002-propiedad-datos-establecimiento.md) | Hacer del contexto Cuentas el único escritor de `Establecimiento` y comunicar los contextos por lenguaje publicado | [ESC-03](#esc-03) | Aceptada |
| [ADR-0003](../adr/0003-estrategia-integracion.md) | Confirmar el pago de forma asíncrona por webhook y mantener síncrono el resto de la API | [ESC-05](#esc-05) | Aceptada |
| [ADR-0004](../adr/0004-plataforma-de-despliegue.md) | Desplegar la API en un contenedor con proceso persistente, y no en funciones sin servidor | [ESC-02](#esc-02) | Aceptada |
| [ADR-0005](../adr/0005-maquina-de-estados-del-mostrador.md) | Declarar las transiciones del mostrador como dato y excluir el pago de ellas | [ESC-03](#esc-03) | Aceptada |
| [ADR-0006](../adr/0006-componente-generativo.md) | No incorporar un componente generativo, y dejar escrito qué lo cambiaría | [ESC-02](#esc-02) | Aceptada |
| [ADR-0007](../adr/0007-autenticacion-del-panel.md) | Autenticar el panel con sesiones propias en lugar de Supabase Auth | [ESC-04](#esc-04) | Aceptada |
| [ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md) | Desplegar en el servidor del laboratorio, con la base de datos dentro del despliegue y la API en un host aparte | [ESC-03](#esc-03) | Aceptada — reemplaza a ADR-0004 |
| [ADR-0009](../adr/0009-no-extraer-un-servicio.md) | No extraer ningún módulo a un servicio independiente, y dejar escrito qué lo cambiaría | [ESC-02](#esc-02) | Aceptada |
| [ADR-0010](../adr/0010-notificar-al-panel-por-sondeo.md) | Notificar al panel por sondeo, y conservar el canal de eventos como costura sin suscriptores | [ESC-03](#esc-03) | Aceptada — revisa ADR-0003 con evidencia de producción |

*(Este índice se amplía en cada entrega a medida que surgen nuevas
decisiones. Dos de las de arriba **revisan** a otras en vez de añadirse: ADR-0008
reemplaza la plataforma que eligió ADR-0004, y ADR-0010 revisa ADR-0003 a la luz
de lo que el sistema desplegado hace de verdad. Una decisión revisada no se
borra: se deja con su razonamiento y se anota qué premisa dejó de ser cierta.)*

------------------------------------------------------------------------

## 10. Requisitos de calidad

Los requisitos de calidad se expresan mediante escenarios verificables.
Cada escenario contiene seis partes: **fuente, estímulo, artefacto,
entorno, respuesta y medida de respuesta**.

Los valores numéricos indicados en estos escenarios son **objetivos
iniciales de calidad**. Todavía no representan resultados
experimentales; posteriormente podrán comprobarse mediante pruebas del
sistema.

<a id="arbol-utilidad"></a>

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

<a id="esc-01"></a>

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

<a id="esc-02"></a>

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

<a id="esc-03"></a>

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

<a id="esc-04"></a>

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

<a id="esc-05"></a>

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

<a id="evaluacion"></a>

### 10.7 Evaluación contra los umbrales

Los cinco escenarios de arriba declaran una medida de respuesta. Esta sección
dice **cuál se cumple y cuál no**, con el número y el método, porque un umbral
que nadie comprueba es una aspiración con formato de requisito.

#### Cómo se midió, y qué parte de cada número viene de dónde

Ninguna de las cifras sale de un solo sitio, y conviene decirlo antes de la
tabla porque explica sus límites:

| Tramo | De dónde sale | Cuándo |
|---|---|---|
| **Red** | `curl` contra `api-pideutb.iscoutb.dev`, **conexión reutilizada** | 18/10/2026, n=14 |
| **Servidor** | En proceso contra PostgreSQL, en el portátil de desarrollo | 18/10/2026, n=50 |
| **Sondeo** | `MS_ENTRE_REFRESCOS` de `sitio/panel.js` | Constante |
| **Persona** | No se mide: se **reserva** | — |

Tres advertencias sobre eso, en orden de importancia:

**La red se midió desde un solo sitio.** 150,8 ms de p50 con la conexión ya
abierta, desde la máquina de desarrollo. Quien use el sistema en el campus verá
otra cifra. Lo que no cambia con la ubicación es que de esos 150,8 ms el
servidor solo pone 1,7: el resto es trayecto.

**El servidor se midió en el portátil, que es más lento que producción.**
Calibrado con la única operación de la que hay muestras en los dos sitios:

| | `GET /v1/menu/.../items`, p50 |
|---|---|
| Portátil de desarrollo | **7,56 ms** |
| Contenedor de producción (`/metricas`) | **1,68 ms** |
| | **El portátil es 4,5× más lento** |

Así que los números de servidor de la tabla son una **cota superior**: en
producción son menores. Eso hace la evaluación conservadora, que es la
dirección correcta para equivocarse.

*(Este factor explica además el riesgo [R-02](#riesgos). Los parámetros de
scrypt se eligieron midiendo 100 ms en el portátil, y producción deriva en unos
35: un factor de 2,9. Dos operaciones independientes coinciden en que el
contenedor es entre 3 y 4,5 veces más rápido que la máquina donde se decidió.
No era un error de medición.)*

**Se mide el peor caso, no la mediana.** Las medidas de respuesta dicen «máximo»
y «en menos de», que son techos. Un p50 que cumple y un máximo que no es un
escenario incumplido.

#### La tabla

| Escenario | Umbral | Lo que controla el sistema | Medido | Veredicto |
|---|---|---|---|---|
| [ESC-01](#esc-01) | < 3 min, sin errores de navegación | `POST /v1/pedidos` | **11,67 ms** p95 + 151 de red ≈ **163 ms** | **Cumple.** Usa el 0,09 % del presupuesto; el resto es tiempo de la persona decidiendo |
| [ESC-02](#esc-02) | < 2 min en ≥ 90 % de los intentos | Ídem | ≈ **163 ms** | **Cumple.** 0,14 % del presupuesto |
| [ESC-03](#esc-03) | ≤ 10 s, ≤ 3 interacciones, sin recargar | Sondeo + cola + transición | **5 320 ms** en el peor caso → **4,68 s** para la persona | **Cumple tras bajar el sondeo.** Con 8 000 ms dependía de una reacción de **menos de 1,68 s**: ver abajo |
| [ESC-04](#esc-04) | < 2 s de validación · 100 % de reutilizaciones rechazadas | `POST /{id}/estado` con código | **9,94 ms** p95 + 151 ≈ **161 ms** | **Cumple.** 8 % del umbral. El 100 % no es una latencia: lo garantiza la máquina de estados, porque `entregado` es final |
| [ESC-05](#esc-05) | Mensaje claro < 3 s · pedido conservado 100 % | `POST /v1/pagos/intentos` | ≈ **164 ms** | **Cumple.** El 100 % de conservación es estructural: el pedido se persiste **antes** de empezar el cobro |

Cuatro de los cinco cumplen con dos o tres órdenes de magnitud de holgura, y eso
no es un elogio: significa que **el servidor no es el cuello de botella de
ninguno de ellos**, igual que [§8.6](#consistencia) concluyó para la caché. Lo
que consume esos presupuestos son las personas y la red.

El quinto es el único donde el sistema decide, y era el que fallaba.

#### ESC-03: el único que no se cumplía, y por qué no se veía

El reloj de ESC-03 arranca **en el pago**, no cuando el encargado mira: el
estímulo es *recibir un pedido pagado* y la respuesta incluye *visualizarlo*.
Eso pone el intervalo de sondeo dentro del plazo, y con él la cadena completa:

| Tramo | Con 8 000 ms | Con 5 000 ms |
|---|---|---|
| [1] Espera al siguiente sondeo *(peor caso)* | 8 000,0 ms | **5 000,0 ms** |
| [2+4] Red, dos idas y vueltas | 301,6 ms | 301,6 ms |
| [2+4] Servidor, p95 de las dos operaciones | 18,7 ms | 18,9 ms |
| **Consumido sin contar a la persona** | **8 320,3 ms** | **5 320,5 ms** |
| **Queda para que la persona vea y pulse** | **1,68 s** | **4,68 s** |

Con 8 000 ms el escenario **se cumplía solo si la persona reaccionaba en menos
de 1,68 s**, y eso es la afirmación exacta: no es que fallara siempre, es que su
cumplimiento dependía de una reacción de menos de dos segundos a un pedido que
aparece mientras se cocina. Para un mostrador en hora pico eso no es una reserva
razonable, y en el peor caso —el pago ocurre un milisegundo después de un
sondeo— el umbral se pasaba.

Lo importante es que se pasaba **sin que nada fallara**: el pedido simplemente
aparecía tarde, que es el tipo de defecto que no produce un error sino una
queja.

Se bajó a **5 000 ms**, reservando 4 s para la persona y dejando 0,68 de
holgura. El costo son 12 sondeos por minuto en vez de 7,5: a ~8 ms de servidor
cada uno, **46 segundos de CPU por turno de 8 horas y panel abierto**, contra
los 0,5 CPU del contenedor. Y el panel ya deja de sondear cuando su pestaña está
oculta, así que ese es el peor caso y no el normal.

`backend/scripts/medir_esc03.py` rehace esta medición y **devuelve código de
error si el escenario no se cumple**, así que la evaluación se puede repetir en
vez de citarse. `backend/tests/test_escenarios_de_calidad.py` fija el intervalo
por los dos lados: no puede subir y romper el umbral, ni bajar sin motivo y
multiplicar peticiones.

#### Lo que esta evaluación no cubre

Se dice porque la diferencia entre medir y suponer es justamente el punto de
esta sección:

- **No es una prueba de carga.** Todo se midió sin concurrencia. El riesgo
  [R-07](#riesgos) —14 peticiones por segundo saturan el contenedor— es
  aritmética sobre una medición de una sola petición, no una medición bajo
  carga.
- **La latencia de red es de un punto de observación.** Falta medirla desde el
  campus, que es donde estarán los usuarios.
- **ESC-01 y ESC-02 se evalúan solo en su parte de servidor.** Los umbrales de
  3 y 2 minutos son dominados por la persona, y medir eso exige usuarios reales,
  no un `curl`.
- **ESC-04 se midió sin el código de canje real** en la transición: la latencia
  de `compare_digest` sobre una cadena corta es despreciable, pero la cifra
  viene de la transición `pagado → en_preparacion`.

------------------------------------------------------------------------

<a id="riesgos"></a>

## 11. Riesgos y deuda técnica

Esta sección estuvo vacía hasta la S12, y conviene decir por qué se llena ahora
y no antes: **los riesgos que vale la pena anotar son los que se pueden medir.**
Una lista escrita al empezar habría contenido lo que se temía; esta contiene lo
que se comprobó, con el número al lado y, donde existe, la prueba que avisa si
cambia.

La columna «cómo se detecta» es la que decide si una fila sirve. Un riesgo que
solo se vigila leyendo esta tabla se hereda sin revisarse.

### 11.1 Riesgos

| ID | Riesgo | Medida | Impacto | Cómo se detecta |
|---|---|---|---|---|
| **R-01** | ~~El margen de ESC-03 está agotado~~ · **Cerrado en la S14.** Medido, incumplía; se bajó el sondeo a 5 s | Quedaban **1,68 s** para la persona · ahora **4,68 s** | — | `medir_esc03.py` devuelve error si deja de cumplirse · `test_escenarios_de_calidad.py` fija el intervalo por los dos lados |
| **R-02** | **scrypt protege menos de lo que ADR-0007 afirma**, y no hay límite de intentos | 100 ms medidos en el portátil · ~35 ms en producción. **Confirmado en la S14** por una segunda operación: el portátil es 4,5× más lento que el contenedor ([§10.7](#evaluacion)) | Alto: es la única barrera contra probar contraseñas en serie | Ninguna automática. Ligado a R-07: las dos correcciones se estorban |
| **R-03** | **El bus de eventos en proceso fallaría en silencio con más de un proceso** de API | Hoy: 1 proceso | Alto *si ocurre*: un panel no se enteraría de que no se entera | `test_el_evento_se_pierde_si_no_hay_nadie_escuchando` obliga a revisar al aparecer un suscriptor |
| **R-04** | **`GET /metricas` dejaría de significar lo que dice** con más de un proceso: la ventana es por proceso y no agregable | Hoy: 1 proceso | Medio: se decide con esas cifras, incluida la de no cachear | Ninguna automática. Declarado en [§8.6](#consistencia) |
| **R-05** | **Un proceso por servicio, sin redundancia.** `restart: unless-stopped` recupera, pero no evita la caída | 1 réplica de cada uno | Medio: la cuota de 4 contenedores impide duplicar | `GET /health` y el chequeo del compose |
| **R-06** | **Un proxy que no controlamos filtra clientes automatizados.** Si la pasarela usara un agente filtrado, sus avisos no llegarían y sería indistinguible de «el evento no llegó» | `Python-urllib` recibe `403` en una sola petición | Medio: el pedido queda en `pendiente_pago`, estado honesto y consultable | Medido en [§7.2](#despliegue-topologia). No mitigable desde aquí: ver fallo 9 de [§6.7](#fallos-parciales) |
| **R-07** | **Agotar la CPU pidiendo iniciar sesión.** `POST /v1/sesiones` es caro a propósito y no hay límite de intentos | **≈14 peticiones/s** saturan 0,5 CPU · 35 ms por derivación | **Alto: el servicio deja de responder**, y el atacante no necesita cuenta | Ninguna automática. Modelada como DoS-1 en [§8.7](#amenazas) |
| **R-08** | **No se puede saber qué persona avanzó un pedido.** `avanzar_estado` recibe el establecimiento, no el usuario | — | Medio: afecta a la auditoría del canje, que es lo que vale dinero | Ninguna: el dato no se guarda |
| **R-09** | **`GET /metricas` es público** y publica el volumen de tráfico por operación | — | Bajo: el inventario de operaciones ya es público; el volumen no lo era | Ninguna automática |
| **R-10** | **La contraseña inicial sigue en el panel, en claro, mucho después de usarse** | 1 uso real, vigente indefinidamente | Medio: es una credencial válida y visible. No se puede rotar por la deuda D-04 | Ninguna |
| **R-11** | ~~Un pago rechazado es indistinguible de uno que aún no ha confirmado~~ · **Cerrado.** Se publica el estado del cobro (`GET /v1/pagos/intentos/{ref}`, contrato 3.2.0) y la pantalla de espera ofrece reintentar | — | — | `test_tras_un_rechazo_el_pedido_y_el_cobro_dicen_cosas_distintas` y su pareja `..._los_dos_dicen_pendiente`, que es la que impide que pase con un endpoint que diga «rechazado» siempre |
| **R-12** | **Con `PIDEUTB_URL_PASARELA_SIMULADA` definida, cualquiera que alcance `/v1/pagos/simulador/{ref}` puede dar un pedido por pagado** | Sin la variable la ruta responde `404` · hoy está definida solo en el despliegue de demostración, desde el panel | **Alto donde esté encendida**: el código de canje es lo que vale dinero | `test_sin_configurar_el_simulador_no_existe` fija que apagada no existe. Que esté apagada en producción **no lo vigila nada**: es configuración |

#### R-01 y R-02 en detalle, que son los dos que tienen número

**R-01, cerrado, y vale como ejemplo de para qué sirve medir.** La S12 lo
encontró cruzando dos documentos: [ESC-03](#esc-03) concede 10 segundos desde que
un pedido se paga hasta que el encargado lo ha visualizado y cambiado de estado,
y el sondeo del panel se comía 8 de ellos. Se dejó anotado con una estimación de
2 segundos para la persona y se aplazó la decisión, porque bajar el intervalo
cambia el comportamiento en producción.

La S14 lo midió entero —red, servidor y sondeo— y el número desmontó la
estimación: quedaban **1,68 s**, no 2. Con una reacción realista en hora pico el
escenario **se incumplía** en el peor caso, y lo hacía sin que nada fallara: el
pedido simplemente aparecía tarde.

Eso convirtió una preferencia en un defecto, y con ello la decisión dejó de ser
discutible. Se bajó el sondeo a 5 000 ms —4,68 s para la persona, 46 s de CPU
por turno y panel— y la medición quedó ejecutable en `medir_esc03.py`, que
devuelve código de error si el umbral deja de cumplirse. El detalle está en
[§10.7](#evaluacion).

#### R-11 y R-12 en detalle

**R-11, cerrado, y era un hueco del contrato y no un defecto de
implementación.** `procesar_evento` guardaba el rechazo donde corresponde —el
intento pasa a `rechazado`— y dejaba el pedido en `pendiente_pago`, que es lo
correcto: un cobro rechazado no cancela un pedido, permite reintentarlo. Lo que
faltaba era que el cliente pudiera enterarse. El contrato publicaba el pedido y
no el intento, así que desde el sitio «rechazado» y «todavía no» eran la misma
respuesta, y la pantalla de espera seguía girando.

Se comprobó en el navegador antes de tocar nada: con el intento en `rechazado`,
el sondeo no cambiaba de pantalla.

**Dónde se publica, y por qué no dentro de `Pedido`.** La opción cómoda era
añadir `estado_pago` a la respuesta del pedido: el cliente ya la sondea y no
haría falta una petición más. Se descartó porque obligaría al router de Pedidos
a importar `pagos.service`, que ya importa `pedidos.service` — un ciclo entre
contextos justo en la frontera que [ADR-0001](../adr/0001-estilo-arquitectonico.md)
mantiene separada, y por la comodidad de ahorrar una consulta en una pantalla
que solo ve una persona. Se publica donde el dato vive: `GET
/v1/pagos/intentos/{referencia_pago}`.

**El orden del sondeo tampoco es casual.** El cliente consulta **primero** el
pedido y solo pregunta por el cobro si sigue en `pendiente_pago`. Es por la
ventana de `conciliar`: `procesar_evento` escribe el pedido antes que el intento
a propósito —falla hacia el cliente— y en esa ventana el pedido ya está pagado
mientras el cobro figura pendiente. Sondeando el cobro primero, quien ya tiene
su código seguiría esperando, que es exactamente el fallo que ese orden de
escritura existe para evitar.

Lo que el cliente **no** afirma es por qué se rechazó. La pasarela no lo dice, y
un motivo inventado —«fondos insuficientes»— sería peor que no darlo.

**R-12 es el precio de poder demostrar el flujo.** La pasarela simulada existe
porque no hay cuenta de comercio: sin ella no se puede recorrer pedido → cobro →
código de canje, ni en una sustentación ni desarrollando sin red.

La barrera es que **la operación no existe sin su variable**: `simular_evento`
comprueba `PIDEUTB_URL_PASARELA_SIMULADA` antes de hacer nada y la ruta responde
`404` —el mismo código que daría una ruta inexistente, y no `403`, que
confirmaría que está ahí y solo falta configurarla—. La ruta además queda fuera
de `openapi.yaml` (`include_in_schema=False`): no es parte del contrato, es un
doble del sistema externo.

Lo que **ninguna prueba puede vigilar** es que la variable esté vacía en un
despliegue con cobros reales, porque eso es configuración y no código. Por eso
está anotado aquí y por eso `deploy/compose.lab.yaml` no la fija: se enciende
desde el panel y se apaga borrándola, sin desplegar.

**R-02.** [ADR-0007](../adr/0007-autenticacion-del-panel.md) eligió los
parámetros de scrypt (N=2¹⁴, r=8, p=1) midiendo **100 ms de mediana en el
portátil de desarrollo**, y dejó constancia de que la cifra depende de la
máquina. Esa cautela es la que salva al ADR, porque la máquina resultó ser otra:

| | Derivación | Intentos por segundo y núcleo |
|---|---|---|
| Portátil de desarrollo (15 repeticiones) | **100 ms** | ~10 |
| Producción *(37,15 ms de p50 de `POST /v1/sesiones`, menos ~2 ms de las dos consultas)* | **~35 ms** | **~29** |

Los parámetros son constantes del código (`credenciales.py`), idénticos en los
dos entornos: la diferencia es puramente de máquina. Y como **no hay límite de
intentos** —decisión declarada en ADR-0007, porque hacerlo bien exige
almacenamiento compartido entre instancias— el costo de la derivación *es* toda
la defensa. En producción vale **unas tres veces menos** de lo que el
razonamiento del ADR asumía.

No se toca esta semana. Subir los parámetros endurece también el arranque del
panel y afecta a `POST /v1/sesiones`, que ya es la operación más lenta del
sistema: es una decisión con dos medidas que corresponde a la S13, no un ajuste
de constante.

#### R-07 es el que sale de juntar tres decisiones correctas

Ninguna de las tres está mal por separado, y es lo que lo hace interesante:

1. `POST /v1/sesiones` deriva scrypt, que cuesta **~35 ms de CPU**. Es la
   defensa de ADR-0007 contra probar contraseñas en serie.
2. **No hay límite de intentos.** Declarado en ese mismo ADR, porque hacerlo
   bien exige almacenamiento compartido entre instancias.
3. El contenedor tiene **0,5 CPU** de tope (ADR-0008).

```
500 ms de CPU por segundo ÷ 35 ms por derivación ≈ 14 peticiones/s
```

Y el detalle que ninguna anticipó: **el atacante no necesita una cuenta.** La
defensa contra ataques de tiempo deriva contra un hash de descarte cuando el
correo no existe, de modo que un correo inventado cuesta lo mismo que uno real.
Para proteger los tiempos de respuesta se hizo que cualquiera pueda obligar al
servidor a trabajar.

Lo que hoy lo contiene no es nuestro: Cloudflare rechaza a los clientes que
identifica como automatismos (R-06, y el fallo 9 de [§6.7](#fallos-parciales)).
Es decir, **lo que la semana 11 anotó como un obstáculo es lo que la semana 13
encuentra conteniendo su amenaza más grave.** No cuenta como mitigación —no la
controlamos y un `User-Agent` de navegador la pasa— pero explica por qué el
riesgo es real y no ha ocurrido.

Se trata en la S14 y no aquí porque hay que medir antes: un límite por IP en
memoria del proceso funcionaría hoy con una sola instancia y **dejaría de
funcionar en silencio con dos**, que es el modo de fallo de R-03. Subir el coste
de scrypt, la otra opción, empeora R-07 mientras mejora R-02.

Las dos correcciones apuntan en direcciones opuestas, y eso es exactamente lo
que hay que resolver con un número delante.

### 11.2 Deuda técnica

| ID | Deuda | Qué cuesta | Qué la pagaría |
|---|---|---|---|
| **D-01** | **No se puede ejecutar el despliegue en local**: no hay Docker en la máquina de desarrollo | Cinco defectos de configuración llegaron a producción invisibles para 282 pruebas ([§7.6](#despliegue-deuda)) | Instalar Docker y correr `deploy/compose.lab.yaml`. Los cinco se habrían visto en treinta segundos |
| **D-02** | **El canal de eventos no tiene suscriptores.** `publicar()` es una operación nula | Quien lea `publicar(...)` asume que algo pasa después | Evaluado en [ADR-0010](../adr/0010-notificar-al-panel-por-sondeo.md): se conserva como costura, y la trampa se desactiva nombrándola |
| **D-03** | **ESC-03 no se ha vuelto a medir en la plataforma nueva.** La medición de ~0,7 s en caliente es de Render | No se sabe si el escenario se cumple hoy, solo que debería | Remedir en la S14, que es donde toca |
| **D-04** | **No hay forma de restablecer una contraseña en producción.** La cuenta inicial se siembra una vez | Una contraseña perdida deja el panel inaccesible sin tocar la base | Se analiza en la S13 |

D-01 es la que explica a las demás. El patrón está en
[§7.6](#despliegue-deuda) y se resume en una frase: **la prueba y el entorno real
no recorren el mismo camino.** Los defectos que produce no dan error: dan un
sistema que parece sano. Dos de esta semana —un aviso que explicaba al usuario
una plataforma abandonada, y un ADR cuyo título afirmaba una decisión que se
había revertido— son de la misma familia, aunque no sean de configuración:
**afirmaciones que nadie volvió a comprobar contra la realidad.**

------------------------------------------------------------------------

<a id="glosario"></a>

## 12. Glosario

  -----------------------------------------------------------------------------------------------------------
  Término                              Definición
  ------------------------------------- -----------------------------------------------------------------------
  **Usuario**                           Rol que agrupa a estudiantes y profesores de la UTB que usan PideUTB
                                         para comprar comida; ambos tienen el mismo comportamiento dentro del
                                         sistema (consultar, pedir, pagar, recoger con código).

  **Cuenta**                            Cualquier actor autenticado del sistema: usuario, establecimiento o
                                         administrador. Es el superconjunto que gestiona el módulo `usuarios`;
                                         no confundir con **Usuario** (ver ddd-contextos.md §1).

  **Establecimiento**                   Negocio de comida dentro del campus que publica su menú en PideUTB.
                                         Es un tipo de **Cuenta**, y el módulo `usuarios` es su único
                                         escritor (ADR-0002).

  **Carrito**                           Sinónimo de «pedido en estado `pendiente_pago`». No es una entidad
                                         separada del sistema (ver ESC-05 y ddd-contextos.md §1).

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
