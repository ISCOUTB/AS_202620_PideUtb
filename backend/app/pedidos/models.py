"""Entidades del contexto Pedidos.

`Pedido` guarda una **instantánea** de los datos del catálogo en el momento
de la compra (`nombre_item`, `precio_unitario`, `total`). No es una
escritura compartida con Catálogo ni una duplicación por descuido: Catálogo
sigue siendo el único escritor de `ItemMenu`; Pedidos solo copia el valor
una vez, como registro histórico. Si el establecimiento renombra el
producto o sube el precio después, el pedido conserva lo que se compró y
lo que se pagó.

`establecimiento_id` es una referencia opaca: el dueño de los datos del
establecimiento es el contexto Cuentas (ADR-0002).

Ver `docs/ddd-contextos.md` §3 y §4 (hallazgo H-1).
"""
from pydantic import BaseModel, Field


class CrearPedidoRequest(BaseModel):
    """Lo único que el cliente decide es qué ítem quiere y cuántos.

    `establecimiento_id` NO se acepta del cliente: es un dato derivado del
    ítem. Aceptarlo permitía crear pedidos asignados a un establecimiento
    que no vende ese producto (ver `docs/violaciones.md`, V-01).
    """

    item_id: int
    cantidad: int = Field(default=1, ge=1, le=50)


class Pedido(BaseModel):
    id: int
    establecimiento_id: int
    item_id: int
    nombre_item: str
    precio_unitario: float
    cantidad: int
    total: float
    estado: str = "pendiente_pago"
