"""Lenguaje publicado del contexto Pagos.

Hoy ningún otro contexto consume estos tipos —Pagos llama a Pedidos, no al
revés—, pero se declaran igual que en los demás módulos para que el día que el
panel del establecimiento necesite saber si un cobro se intentó, la superficie
ya exista y no haya que abrir `models.py` de urgencia.
"""
from enum import Enum

from pydantic import BaseModel, Field


class MetodoDePago(str, Enum):
    """Medios aceptados por la pasarela en ambiente Sandbox.

    Aparece en **peticiones**, así que añadir un valor es compatible y quitarlo
    no lo es (`docs/api/politica-versionado.md` §3.1).
    """

    TARJETA = "tarjeta"
    NEQUI = "nequi"
    PSE = "pse"


class EstadoPago(str, Enum):
    """Estado de un intento de cobro.

    `PENDIENTE` no es un estado de transición interno sino el estado normal
    durante toda la ventana en que el usuario está en la pasarela. Es la
    consecuencia directa de que el resultado no llegue de forma síncrona.
    """

    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


class IntentoPagoPublicado(BaseModel):
    referencia_pago: str = Field(min_length=1, max_length=64)
    pedido_id: int
    monto_centavos: int = Field(ge=0)
    estado_pago: EstadoPago
    url_checkout: str
