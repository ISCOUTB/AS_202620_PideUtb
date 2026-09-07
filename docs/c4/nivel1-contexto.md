# C4 — Nivel 1: Diagrama de contexto

> Referenciado desde [`arc42.md` §3.2](../arc42/arc42.md#c4-contexto).

El siguiente diagrama representa el sistema PideUTB, sus principales usuarios y los sistemas externos con los que interactúa.

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

**Leyenda del diagrama**

| Color       | Elemento del diagrama | Qué representa                                                                                                      |
|-------------|------------------------|------------------------------------------------------------------------------------------------------------------|
| Azul oscuro | `Person(...)`          | Personas que se conectan al sistema: usuario (estudiante o profesor), personal del establecimiento, administrador. |
| Azul claro  | `System(...)`          | El software que estamos construyendo: PideUTB.                                                                    |
| Gris        | `System_Ext(...)`      | Servicios externos de los que depende nuestro software: Wompi y Supabase.                                         |

El C4 de nivel 1 muestra el sistema desde una perspectiva externa. No representa componentes internos como clases, módulos o tablas de la base de datos (ver [arc42.md §3.3](../arc42/arc42.md#alcance-externo) para el detalle de cada interacción).
