"""Forma que el contexto Pedidos publica por HTTP.

Debe coincidir con `docs/api/openapi.yaml`; que coincida lo verifica
`tests/test_contrato_api.py`.
"""
from pydantic import BaseModel, Field

from app.pedidos.contracts import EstadoPedido, PedidoPublicado


class CrearPedidoRequest(BaseModel):
    """Lo único que el cliente decide es qué ítem quiere y cuántos.

    `establecimiento_id` NO se acepta del cliente: es un dato derivado del
    ítem. Aceptarlo permitía crear pedidos asignados a un establecimiento
    que no vende ese producto (ver `docs/violaciones.md`, V-01). Un campo
    extra en la petición se ignora en lugar de producir un error, y eso forma
    parte del contrato: un cliente antiguo que siga enviándolo no se rompe,
    pero tampoco consigue influir en el resultado.
    """

    item_id: int = Field(ge=1)
    cantidad: int = Field(default=1, ge=1, le=50)


class PedidoResponse(BaseModel):
    """Representación pública de un pedido."""

    pedido_id: int = Field(ge=1)
    establecimiento_id: int = Field(ge=1)
    item_id: int = Field(ge=1)
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_centavos: int = Field(ge=0)
    estado: EstadoPedido

    #: Sin valor por defecto a propósito: así queda declarado como **requerido
    #: y anulable** en lugar de opcional. El consumidor encuentra siempre la
    #: clave y solo tiene que mirar si vale `null`, en vez de distinguir entre
    #: «ausente» y «vacío», que es una fuente clásica de fallos en el cliente.
    codigo_canje: str | None

    @classmethod
    def desde_contrato(cls, pedido: PedidoPublicado) -> "PedidoResponse":
        return cls(**pedido.model_dump())
