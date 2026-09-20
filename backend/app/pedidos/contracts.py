"""Lenguaje publicado del contexto Pedidos.

Lo que otros contextos —hoy `pagos`— pueden conocer de un pedido. Igual que en
`menu.contracts`, separarlo del modelo interno permite que la entidad
almacenada evolucione sin arrastrar a quien la consume.

`EstadoPedido` vive aquí y no en `models.py` a propósito: el conjunto de
estados **es** parte del lenguaje publicado. Mientras fue texto libre
(`docs/violaciones.md`, V-08) ningún consumidor podía saber qué valores debía
estar preparado para recibir, que es tanto como no tener contrato.
"""
from enum import Enum

from pydantic import BaseModel, Field


class EstadoPedido(str, Enum):
    """Conjunto cerrado de estados. Debe coincidir con el `enum` de
    `EstadoPedido` en `docs/api/openapi.yaml`, y que coincida lo verifica
    `tests/test_contrato_api.py`.

    Añadir un valor aquí es un cambio incompatible para los consumidores que
    reciben el estado (`docs/api/politica-versionado.md` §3.1).
    """

    PENDIENTE_PAGO = "pendiente_pago"
    PAGADO = "pagado"
    EN_PREPARACION = "en_preparacion"
    LISTO_PARA_RECOGER = "listo_para_recoger"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class PedidoPublicado(BaseModel):
    """Vista de un pedido hacia fuera del contexto Pedidos."""

    pedido_id: int
    establecimiento_id: int
    item_id: int
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_centavos: int = Field(ge=0)
    estado: EstadoPedido
    codigo_canje: str | None
