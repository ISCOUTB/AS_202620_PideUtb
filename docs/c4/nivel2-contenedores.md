# C4 — Nivel 2: Diagrama de contenedores

> Referenciado desde [`arc42.md` §5.1](../arc42/arc42.md#c4-contenedores).

El diagrama de contexto ([Nivel 1](nivel1-contexto.md)) mostró a PideUTB como una caja negra. El siguiente diagrama abre esa caja y muestra sus piezas desplegables: el frontend web, la API backend y los sistemas externos de los que depende.

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

**Leyenda del diagrama.** Igual que en el [Nivel 1](nivel1-contexto.md), los colores son los que aplica Mermaid por defecto a cada tipo de elemento:

| Color       | Elemento del diagrama                        | Qué representa                                                              |
|-------------|-----------------------------------------------|-----------------------------------------------------------------------------|
| Azul oscuro | `Person(...)`                                 | Personas que se conectan al sistema.                                        |
| Azul claro  | `Container(...)` dentro de `System_Boundary`  | Piezas desplegables del software que estamos construyendo (frontend y API). |
| Gris        | `System_Ext(...)`                             | Servicios externos de los que depende nuestro software: Supabase y Wompi.   |

**Nota de despliegue:** frontend y API se despliegan como servicios separados en Vercel, pero la API sigue siendo un único contenedor internamente (monolito modular) — no hay un contenedor por módulo de dominio.
