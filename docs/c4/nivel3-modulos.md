# C4 — Nivel 3: Módulos internos de la API (caja blanca)

> Referenciado desde [`arc42.md` §5.2](../arc42/arc42.md#c4-modulos).

El contenedor "API PideUTB" (ver [Nivel 2](nivel2-contenedores.md)) se descompone en cuatro módulos de dominio, uno por cada **contexto delimitado** del [mapa de contextos](../ddd-contextos.md). Cada uno sigue la misma estructura interna:

```
modulo/
├── models.py       # entidades INTERNAS del contexto (no cruzan la frontera)
├── contracts.py    # lenguaje publicado: lo único que otros contextos ven
├── router.py       # endpoints FastAPI (capa de entrada HTTP)
├── service.py      # lógica de negocio + INTERFAZ PÚBLICA del módulo
└── repository.py   # acceso a datos (Supabase), solo del propio contexto
```

> **Actualización S6 (ver [ADR-0002](../adr/0002-propiedad-datos-establecimiento.md)).** Dos cambios respecto al corte 1, sin añadir módulos:
> 1. El módulo `usuarios` gestiona, además de las cuentas de estudiantes y profesores, las **cuentas de tipo Establecimiento** (nombre, ubicación, horario) y es su único escritor. `menu` y `pedidos` guardan solo `establecimiento_id` como referencia y lo resuelven vía `usuarios.service`.
> 2. `contracts.py` es nuevo: antes las funciones públicas devolvían las entidades de `models.py`, de modo que el modelo de un contexto se filtraba dentro de otro.

``` mermaid
graph TD
    subgraph API["API PideUTB (FastAPI)"]
        M["<b>menu</b> — contexto Catálogo<br/>único escritor de: ÍtemMenu"]
        P["<b>pedidos</b> — contexto Pedidos<br/>único escritor de: Pedido"]
        U["<b>usuarios</b> — contexto Cuentas<br/>único escritor de:<br/>Establecimiento, Cuenta"]
        PG["<b>pagos</b> — contexto Pagos<br/>único escritor de:<br/>Transacción, Código de canje"]
    end

    P -->|"lee o solicita<br/>menu.service.obtener_item() → ItemDisponible"| M
    P -->|"lee o solicita<br/>usuarios.service.establecimiento_esta_activo()"| U
    P -.->|"solicitará el cobro vía pagos.service"| PG
    PG -.->|"verificará identidad vía usuarios.service"| U

    style PG stroke-dasharray: 5 5
```

Línea continua: implementado. Línea punteada: previsto.

**Regla de comunicación (ADR-0001, precisada por ADR-0002):** un módulo solo puede importar `service` o `contracts` de otro módulo. Está prohibido importar `repository.py` o `models.py` de un contexto ajeno, y las funciones públicas responden con tipos de `contracts`, nunca con entidades internas.

**La regla se verifica automáticamente.** `backend/tests/test_modularidad.py` recorre el árbol de sintaxis de cada archivo de `app/` y falla la construcción si algún import cruza la frontera. La prueba incluye su propio caso negativo, para demostrar que falla cuando debe.

**Propiedad de datos:** cada dato tiene exactamente un módulo que lo escribe; los demás lo leen o lo solicitan. La tabla completa está en [`docs/ddd-contextos.md` §3](../ddd-contextos.md).

Ver [arc42.md §5.3](../arc42/arc42.md#responsabilidad-modulos) para la responsabilidad y el estado de implementación de cada módulo.
