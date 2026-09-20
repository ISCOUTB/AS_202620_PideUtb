"""Acceso a datos del contexto Pagos.

Implementación en memoria para esta entrega. Solo este módulo lee y escribe
las tablas de pagos (`pagos_*`).

Se indexa por `referencia_pago` y además por `pedido_id`, porque las dos
búsquedas responden a preguntas distintas: el webhook llega con la referencia
y no sabe nada del pedido, mientras que el frontend pide el intento de un
pedido y no conoce la referencia hasta que se la devolvemos.
"""
from app.pagos.contracts import EstadoPago
from app.pagos.models import IntentoPago

# TODO(supabase): reemplazar por la tabla `pagos_intentos`.
_INTENTOS: dict[str, IntentoPago] = {}


def guardar(intento: IntentoPago) -> IntentoPago:
    _INTENTOS[intento.referencia_pago] = intento
    return intento


def buscar_por_referencia(referencia_pago: str) -> IntentoPago | None:
    return _INTENTOS.get(referencia_pago)


def buscar_pendiente_de_pedido(pedido_id: int) -> IntentoPago | None:
    """Intento aún sin resolver para un pedido, si lo hay.

    Es lo que hace idempotente a `iniciar_intento`: sin esta consulta, pulsar
    dos veces «Pagar» abriría dos cobros sobre el mismo pedido.
    """
    for intento in _INTENTOS.values():
        if intento.pedido_id == pedido_id and intento.estado_pago is EstadoPago.PENDIENTE:
            return intento
    return None
