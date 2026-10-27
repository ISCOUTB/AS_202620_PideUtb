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


class LineaPedido(BaseModel):
    """Un producto dentro de un pedido, con su instantánea de catálogo.

    La instantánea vive **en la línea** y no en el pedido desde que un pedido
    puede llevar varios productos (migración 004). El motivo no cambió: si el
    establecimiento sube el precio de la arepa, esta línea sigue valiendo lo
    que valía cuando se compró.
    """

    item_id: int
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_linea_centavos: int = Field(ge=0)


class Pedido(BaseModel):
    id: int
    establecimiento_id: int

    #: Al menos una. Un pedido vacío no es un pedido, y dejarlo representable
    #: obligaría a comprobarlo en cada sitio que recorre las líneas.
    lineas: list[LineaPedido] = Field(min_length=1)

    #: La **suma** de las líneas, no un producto. La base lo verifica con un
    #: disparador diferido, porque una restricción de fila no puede mirar otra
    #: tabla (migración 004).
    total_centavos: int = Field(ge=0)

    estado: EstadoPedido = EstadoPedido.PENDIENTE_PAGO
    codigo_canje: str | None = None
