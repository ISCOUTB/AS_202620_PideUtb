# C4 — Nivel 2: Diagrama de contenedores

> Referenciado desde [`arc42.md` §5.1](../arc42/arc42.md#c4-contenedores).
> Los flujos que recorren estas flechas en tiempo de ejecución están en
> [`arc42.md` §6](../arc42/arc42.md#runtime-flujos).

El diagrama de contexto ([Nivel 1](nivel1-contexto.md)) mostró a PideUTB como una caja negra. El siguiente diagrama abre esa caja y muestra sus piezas desplegables: el frontend web, la API backend y los sistemas externos de los que depende.

**Cada flecha lleva su protocolo, su formato y su modo de interacción** (síncrono o asíncrono). No es decoración: el modo es lo que determina qué le pasa al usuario si el otro extremo no responde, y esa consecuencia está justificada una a una en [ADR-0003](../adr/0003-estrategia-integracion.md).

``` mermaid
C4Container
    title Diagrama de Contenedores — PideUTB

    Person(usuario, "Usuario (estudiante o profesor)")
    Person(establecimiento, "Personal del establecimiento")
    Person(admin, "Administrador")

    System_Boundary(pideutb, "PideUTB") {
        Container(frontend, "Frontend Web", "HTML, CSS, JavaScript", "Interfaz web consumida por los tres roles: consulta de menú, pedidos, gestión de estados.")
        Container(api, "API PideUTB", "FastAPI (Python) — monolito modular", "Expone /v1 según docs/api/openapi.yaml. Cuatro módulos de dominio que solo se comunican por funciones públicas de servicio (ADR-0001).")
    }

    System_Ext(supabase, "Supabase", "Persistencia (PostgreSQL) y autenticación.")
    System_Ext(wompi, "Wompi Sandbox", "Procesamiento de pagos de prueba.")

    Rel(usuario, frontend, "Consulta menús, pide, paga y recoge", "HTTPS · HTML/JSON · síncrono")
    Rel(establecimiento, frontend, "Gestiona productos y estados de pedido", "HTTPS · HTML/JSON · síncrono")
    Rel(admin, frontend, "Administra la plataforma", "HTTPS · HTML/JSON · síncrono")

    Rel(frontend, api, "Consume la API v1", "HTTPS · JSON (REST) · síncrono")
    Rel(api, supabase, "Lee/escribe datos, valida identidad", "HTTPS · JSON (PostgREST) · síncrono")
    Rel(api, wompi, "Abre el intento de cobro", "HTTPS · JSON · síncrono")
    Rel_Back(api, wompi, "Confirma la transacción (webhook firmado)", "HTTPS · JSON + HMAC · ASÍNCRONO")

    UpdateRelStyle(frontend, api, $offsetY="-30")
    UpdateRelStyle(api, wompi, $offsetX="-90", $offsetY="-40")
    UpdateRelStyle(api, supabase, $offsetX="-60", $offsetY="-20")
```

## Etiquetado de las relaciones

La misma información del diagrama, en forma consultable. La última columna es la que convierte el modo en algo verificable en lugar de una etiqueta.

| # | Origen → Destino | Protocolo | Formato | Modo | Contrato | Si el destino no responde |
|---|---|---|---|---|---|---|
| 1 | Usuario / Personal / Admin → Frontend Web | HTTPS | HTML + JSON | Síncrono | *(interfaz de usuario)* | No hay producto |
| 2 | Frontend Web → API PideUTB | HTTPS | JSON (REST) | Síncrono | [`openapi.yaml`](../api/openapi.yaml) | El usuario no puede operar; se acepta porque sin API no hay sistema |
| 3 | API PideUTB → Supabase | HTTPS | JSON (PostgREST) | Síncrono | *(pendiente — hoy repositorios en memoria,* [V-09](../violaciones.md#v-09)*)* | La operación falla y se responde un error explícito |
| 4 | API PideUTB → Wompi Sandbox | HTTPS | JSON | Síncrono | API externa de la pasarela | Error inmediato; **el pedido se conserva** y se puede reintentar |
| 5 | Wompi Sandbox → API PideUTB | HTTPS | JSON + firma HMAC (`X-Firma-Evento`) | **Asíncrono** | [`asyncapi.yaml`](../api/asyncapi.yaml) · canal `eventos-de-pago` | El pedido queda en `pendiente_pago`, consultable por el frontend |

### Por qué la flecha 5 va en sentido contrario

Es la única relación en la que **un sistema externo inicia la conversación**, y por eso se dibuja hacia dentro. Un webhook no es «la respuesta» de la llamada 4: es una petición nueva, que llega minutos después, por una conexión distinta, y que puede llegar **varias veces o ninguna**.

Dibujarla como retorno de la flecha 4 sugeriría que hay una petición esperando al otro lado, que es justo lo que no ocurre y lo que hace que esta integración sea asíncrona.

De ahí se derivan tres exigencias que ninguna de las otras flechas tiene, y que están implementadas y probadas ([arc42 §6.5](../arc42/arc42.md#runtime-modos-de-fallo)):

- **Idempotencia**, porque la entrega es al-menos-una-vez.
- **Autenticación propia** (firma HMAC), porque el interlocutor ya no es nuestro frontend sino Internet.
- **Un camino para que el usuario se entere después**, que es `GET /v1/pedidos/{pedido_id}`.

### El canal de eventos interno no aparece en este nivel

[`asyncapi.yaml`](../api/asyncapi.yaml) declara un segundo canal asíncrono, `pedidos-pagados`, que hoy **se entrega dentro del proceso de la API**. Como el nivel 2 muestra piezas desplegables y ese canal no cruza ninguna frontera de despliegue, aparece en el [nivel 3](nivel3-modulos.md) y no aquí.

Que el transporte sea trivial no lo convierte en una llamada síncrona disfrazada: el publicador no conoce a sus suscriptores, no espera resultado y un suscriptor que falle no tumba el cobro. El día que el panel del establecimiento sea un desplegable propio, ese canal sube a este nivel como una flecha más — y el contrato ya estará escrito.

## Leyenda del diagrama

Los colores son los que aplica Mermaid por defecto a cada tipo de elemento:

| Color       | Elemento del diagrama                        | Qué representa                                                              |
|-------------|-----------------------------------------------|-----------------------------------------------------------------------------|
| Azul oscuro | `Person(...)`                                 | Personas que se conectan al sistema.                                        |
| Azul claro  | `Container(...)` dentro de `System_Boundary`  | Piezas desplegables del software que estamos construyendo (frontend y API). |
| Gris        | `System_Ext(...)`                             | Servicios externos de los que depende nuestro software: Supabase y Wompi.   |

**Nota de despliegue:** frontend y API se despliegan como servicios separados en Vercel, pero la API sigue siendo un único contenedor internamente (monolito modular) — no hay un contenedor por módulo de dominio. La integración asíncrona de la flecha 5 **no contradice** esa decisión: lo que se desacopla es el momento, no el despliegue ([ADR-0003](../adr/0003-estrategia-integracion.md), «Lo que no cambia»).
