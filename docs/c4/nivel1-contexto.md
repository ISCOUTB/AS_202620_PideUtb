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
    System_Ext(smtp, "Servidor de correo", "Entrega el comprobante de pago al cliente")
    System_Ext(push, "Servicios de push", "De Google, Apple, Mozilla y Microsoft: avisan al teléfono del cliente")

    Rel(usuario, pideutb, "Consulta menús, realiza pedidos, paga y recibe código")
    Rel(establecimiento, pideutb, "Gestiona productos y pedidos")
    Rel(admin, pideutb, "Administra la plataforma")
    Rel(usuario, wompi, "Paga en la pasarela, con la dirección que le da PideUTB", "HTTPS")
    Rel(wompi, pideutb, "Confirma la transacción", "HTTPS · webhook firmado")
    Rel(pideutb, smtp, "Manda el comprobante", "SMTP")
    Rel(pideutb, push, "Avisa de que el pedido está listo", "HTTPS")
```

**Leyenda del diagrama**

| Color       | Elemento del diagrama | Qué representa                                                                                                      |
|-------------|------------------------|------------------------------------------------------------------------------------------------------------------|
| Azul oscuro | `Person(...)`          | Personas que se conectan al sistema: usuario (estudiante o profesor), personal del establecimiento, administrador. |
| Azul claro  | `System(...)`          | El software que estamos construyendo: PideUTB.                                                                    |
| Gris        | `System_Ext(...)`      | Servicios externos de los que depende nuestro software. Son tres: Wompi, el servidor de correo y los servicios de push.                                 |

### Por qué ya no aparece la base de datos

Hasta la semana 11, este diagrama incluía **Supabase** como sistema externo. Ya
no: la base de datos es un contenedor del propio despliegue
([ADR-0008](../adr/0008-despliegue-en-el-servidor-del-laboratorio.md)), así que
está *dentro* de la frontera del sistema y le corresponde el
[nivel 2](nivel2-contenedores.md), no este.

No es un detalle de dibujo. En el nivel 1, un sistema externo es algo **que no
controlamos y que puede fallar por su cuenta**; cada uno es una dependencia que
hay que gestionar y un acuerdo que mantener. Pasar de dos a uno significa
exactamente eso: hay una cosa menos que puede romperse por motivos ajenos.

Queda Wompi, y queda por la razón de siempre: el dinero no es nuestro.

El C4 de nivel 1 muestra el sistema desde una perspectiva externa. No representa componentes internos como clases, módulos o tablas de la base de datos (ver [arc42.md §3.3](../arc42/arc42.md#alcance-externo) para el detalle de cada interacción).
