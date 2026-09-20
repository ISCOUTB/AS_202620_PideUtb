# C4 — Nivel 3: Módulos internos de la API (caja blanca)

> Referenciado desde [`arc42.md` §5.2](../arc42/arc42.md#c4-modulos).

El contenedor "API PideUTB" (ver [Nivel 2](nivel2-contenedores.md)) se descompone en cuatro módulos de dominio, uno por cada **contexto delimitado** del [mapa de contextos](../ddd-contextos.md). Cada uno sigue la misma estructura interna:

```
modulo/
├── models.py         # entidades INTERNAS del contexto (no cruzan la frontera)
├── contracts.py      # lenguaje publicado hacia OTROS CONTEXTOS (en proceso)
├── esquemas_api.py   # lenguaje publicado hacia FUERA DEL SISTEMA (HTTP)
├── router.py         # endpoints FastAPI (capa de entrada HTTP)
├── service.py        # lógica de negocio + INTERFAZ PÚBLICA del módulo
└── repository.py     # acceso a datos (Supabase), solo del propio contexto
```

Son **tres** superficies distintas y conviene no confundirlas, porque evolucionan
a ritmos distintos:

| Archivo | Frontera que publica | Quién la consume | Coste de cambiarla |
|---|---|---|---|
| `models.py` | Ninguna | El propio módulo | Un commit |
| `contracts.py` | Entre contextos, en proceso | Los otros módulos | Un commit: sus consumidores viven en este repositorio |
| `esquemas_api.py` | HTTP, fuera del sistema | Clientes que no controlamos | La ceremonia de [`politica-versionado.md`](../api/politica-versionado.md) |

> **Actualización S7 (ver [ADR-0003](../adr/0003-estrategia-integracion.md)).** Tres cambios, sin añadir módulos de dominio:
> 1. El módulo `pagos` deja de estar vacío: implementa el inicio síncrono del cobro y la recepción asíncrona del evento de la pasarela.
> 2. Aparece `app/eventos.py`, un bus en proceso que **no es un módulo de dominio**: no tiene contexto ni datos propios, solo transporta. Por eso queda fuera de la regla de dependencia y no aparece en la tabla de propiedad de datos.
> 3. El **código de canje pertenece a Pedidos**, no a Pagos. Lo genera `pedidos.service.confirmar_pago` porque es un atributo del `Pedido`, cuyo único escritor es Pedidos (ADR-0002). Pagos *solicita* la transición; no la ejecuta.
>
> **Actualización S6 (ver [ADR-0002](../adr/0002-propiedad-datos-establecimiento.md)).** Dos cambios respecto al corte 1, sin añadir módulos:
> 1. El módulo `usuarios` gestiona, además de las cuentas de estudiantes y profesores, las **cuentas de tipo Establecimiento** (nombre, ubicación, horario) y es su único escritor. `menu` y `pedidos` guardan solo `establecimiento_id` como referencia y lo resuelven vía `usuarios.service`.
> 2. `contracts.py` es nuevo: antes las funciones públicas devolvían las entidades de `models.py`, de modo que el modelo de un contexto se filtraba dentro de otro.

``` mermaid
graph TD
    subgraph API["API PideUTB (FastAPI)"]
        M["<b>menu</b> — contexto Catálogo<br/>único escritor de: ÍtemMenu"]
        P["<b>pedidos</b> — contexto Pedidos<br/>único escritor de: Pedido"]
        U["<b>usuarios</b> — contexto Cuentas<br/>único escritor de:<br/>Establecimiento, Cuenta"]
        PG["<b>pagos</b> — contexto Pagos<br/>único escritor de: IntentoPago"]
        BUS(["bus de eventos — app/eventos.py<br/><i>no es un contexto: solo transporta</i>"])
    end

    PANEL["Panel del establecimiento<br/><i>suscriptor previsto</i>"]

    P -->|"SÍNCRONO en proceso<br/>menu.service.obtener_item() → ItemDisponible"| M
    P -->|"SÍNCRONO en proceso<br/>usuarios.service.establecimiento_esta_activo()"| U
    PG -->|"SÍNCRONO en proceso<br/>pedidos.service.confirmar_pago() → PedidoPublicado"| P
    P -->|"ASÍNCRONO · publica pedido.pagado"| BUS
    BUS -.->|"pedido.pagado · JSON<br/>sin espera de respuesta"| PANEL
    PG -.->|"verificará identidad vía usuarios.service"| U

    style PANEL stroke-dasharray: 5 5
```

Línea continua: implementado. Línea punteada: previsto.

**Nótese la dirección de la flecha `pagos → pedidos`.** Es Pagos quien llama a
Pedidos y no al revés, porque el dato que cambia —el estado del pedido y su
código de canje— pertenece a Pedidos. Si Pagos escribiera el pedido
directamente habría dos escritores del mismo dato, que es exactamente la
violación que ADR-0002 cerró.

**Y nótese que el bus no devuelve nada.** El publicador no sabe si hay
suscriptores ni si tuvieron éxito: es la propiedad que distingue publicar un
hecho de llamar a una función, y la que hace que un panel caído no tumbe un
cobro ya realizado ([ADR-0003](../adr/0003-estrategia-integracion.md)).

**Regla de comunicación (ADR-0001, precisada por ADR-0002):** un módulo solo puede importar `service` o `contracts` de otro módulo. Está prohibido importar `repository.py` o `models.py` de un contexto ajeno, y las funciones públicas responden con tipos de `contracts`, nunca con entidades internas.

**La regla se verifica automáticamente.** `backend/tests/test_modularidad.py` recorre el árbol de sintaxis de cada archivo de `app/` y falla la construcción si algún import cruza la frontera. La prueba incluye su propio caso negativo, para demostrar que falla cuando debe.

**Propiedad de datos:** cada dato tiene exactamente un módulo que lo escribe; los demás lo leen o lo solicitan. La tabla completa está en [`docs/ddd-contextos.md` §3](../ddd-contextos.md).

Ver [arc42.md §5.3](../arc42/arc42.md#responsabilidad-modulos) para la responsabilidad y el estado de implementación de cada módulo.
