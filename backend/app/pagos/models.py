"""Entidades internas del contexto Pagos.

Pagos es el único escritor de `IntentoPago`. No escribe `Pedido`: cuando un
cobro se aprueba, **solicita** a `pedidos.service` que haga la transición, y es
Pedidos quien la ejecuta por ser su único escritor (ADR-0002).

`pedido_id` es una referencia opaca, igual que `establecimiento_id` en los
demás contextos: Pagos no guarda el total del pedido como copia editable sino
el monto que efectivamente se mandó a cobrar, que es un hecho distinto y propio
de este contexto.
"""
from pydantic import BaseModel, Field

from app.pagos.contracts import EstadoPago, MetodoDePago


class IntentoPago(BaseModel):
    """Un intento de cobro sobre un pedido."""

    referencia_pago: str = Field(min_length=1, max_length=64)
    pedido_id: int
    monto_centavos: int = Field(ge=0)
    metodo: MetodoDePago
    estado_pago: EstadoPago = EstadoPago.PENDIENTE
    url_checkout: str
