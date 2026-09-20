"""Forma que el contexto Pagos publica por HTTP.

Debe coincidir con `docs/api/openapi.yaml` y, en el caso de `EventoPagoRequest`,
también con el mensaje `transaccion.actualizada` de `docs/api/asyncapi.yaml`.
Que los tres coincidan lo verifica `tests/test_contrato_api.py`.
"""
from typing import Literal

from pydantic import BaseModel, Field

from app.pagos.contracts import EstadoPago, IntentoPagoPublicado, MetodoDePago
from app.pedidos.contracts import EstadoPedido


class IniciarPagoRequest(BaseModel):
    pedido_id: int = Field(ge=1)
    metodo: MetodoDePago


class IntentoPagoResponse(BaseModel):
    referencia_pago: str = Field(min_length=1, max_length=64)
    pedido_id: int = Field(ge=1)
    monto_centavos: int = Field(ge=0)
    estado_pago: EstadoPago
    url_checkout: str

    @classmethod
    def desde_contrato(cls, intento: IntentoPagoPublicado) -> "IntentoPagoResponse":
        return cls(**intento.model_dump())


class EventoPagoRequest(BaseModel):
    """Cuerpo del webhook de la pasarela.

    `ocurrido_en` es opcional porque el sistema **no decide en función del
    orden temporal**: los eventos pueden llegar desordenados y el resultado se
    resuelve por el estado que traen, no por su marca de tiempo. Hacerlo
    obligatorio sería prometer que lo usamos.
    """

    evento: Literal["transaccion.actualizada"]
    referencia_pago: str = Field(min_length=1, max_length=64)
    estado_pago: EstadoPago
    ocurrido_en: str | None = None


class AcuseDeEventoResponse(BaseModel):
    """Acuse de recibo, no confirmación de efecto.

    Se responde con `202` y este cuerpo tanto la primera vez como en los
    reintentos: para el emisor, un duplicado no es un fallo del que deba
    recuperarse.
    """

    recibido: Literal[True]
    pedido_id: int = Field(ge=1)
    estado: EstadoPedido
    duplicado: bool
