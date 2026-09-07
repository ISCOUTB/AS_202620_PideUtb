# C4 — Nivel 3: Módulos internos de la API (caja blanca)

> Referenciado desde [`arc42.md` §5.2](../../arc42.md#52-nivel-2--módulos-internos-de-la-api-caja-blanca).

El contenedor "API PideUTB" (ver [Nivel 2](nivel2-contenedores.md)) se descompone en los cuatro módulos de dominio definidos en la estrategia de solución (arc42 §4). Cada uno sigue la misma estructura interna:

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

**Regla de comunicación (ADR-0001):** un módulo solo puede invocar funciones exportadas por el `service.py` de otro módulo. Está prohibido importar `repository.py` o acceder a `models.py` de un módulo distinto directamente.

Ver [arc42.md §5.3](../../arc42.md#53-responsabilidad-de-cada-módulo) para la responsabilidad y estado de implementación de cada módulo.
