"""Entidades del contexto Pedidos.

`Pedido` guarda una **instantánea** de los datos del catálogo en el momento
de la compra (`nombre_item`, `precio_unitario_centavos`, `total_centavos`). No
es una escritura compartida con Catálogo ni una duplicación por descuido:
Catálogo sigue siendo el único escritor de `ItemMenu`; Pedidos solo copia el
valor una vez, como registro histórico. Si el establecimiento renombra el
producto o sube el precio después, el pedido conserva lo que se compró y lo que
se pagó.

`establecimiento_id` es una referencia opaca: el dueño de los datos del
establecimiento es el contexto Cuentas (ADR-0002).

Los importes son **enteros en centavos** (`docs/violaciones.md`, V-07). El
dinero en punto flotante acumula error en cada operación y no tiene una
representación exacta para valores tan corrientes como 0,10; un pedido cuyo
total difiere del importe cobrado por la pasarela es una disputa, no un
redondeo.

Ver `docs/ddd-contextos.md` §3 y §4 (hallazgo H-1).
"""
from pydantic import BaseModel, Field

from app.pedidos.contracts import EstadoPedido


class Pedido(BaseModel):
    id: int
    establecimiento_id: int
    item_id: int
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_centavos: int = Field(ge=0)
    estado: EstadoPedido = EstadoPedido.PENDIENTE_PAGO
    codigo_canje: str | None = None
