"""Acceso a datos del módulo `pedidos`.

Igual que en `menu`, esto es en memoria por ahora y se reemplaza por
Supabase manteniendo la misma interfaz (`guardar`, `siguiente_id`).
"""
from app.pedidos.models import Pedido

# TODO(supabase): reemplazar por tabla `pedidos`.
_PEDIDOS: dict[int, Pedido] = {}
_contador = 0


def siguiente_id() -> int:
    global _contador
    _contador += 1
    return _contador


def guardar(pedido: Pedido) -> Pedido:
    _PEDIDOS[pedido.id] = pedido
    return pedido
