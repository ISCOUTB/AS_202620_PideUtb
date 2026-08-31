from pydantic import BaseModel


class CrearPedidoRequest(BaseModel):
    establecimiento_id: int
    item_id: int
    cantidad: int = 1


class Pedido(BaseModel):
    id: int
    establecimiento_id: int
    item_id: int
    nombre_item: str
    cantidad: int
    total: float
    estado: str = "pendiente_pago"
