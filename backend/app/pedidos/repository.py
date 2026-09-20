"""Acceso a datos del módulo `pedidos`.

Igual que en `menu`, esto es en memoria por ahora y se reemplaza por
Supabase manteniendo la misma interfaz (`guardar`, `siguiente_id`,
`buscar_por_id`).

El estado vive en memoria del proceso, que es la violación V-09 de
`docs/violaciones.md`: con más de una instancia desplegada, un pedido creado
en una no existe en la otra. Sigue siendo deuda consciente y bloquea el
despliegue real, no esta entrega.
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


def buscar_por_id(pedido_id: int) -> Pedido | None:
    return _PEDIDOS.get(pedido_id)
