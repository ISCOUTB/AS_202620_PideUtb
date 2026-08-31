"""Interfaz pública del módulo `menu`.

Estas son las ÚNICAS funciones que otros módulos (como `pedidos`)
tienen permitido llamar. Nada fuera de este archivo debe ser
importado por otro módulo (ver ADR-0001 y arc42 §5.2).
"""
from app.menu import repository
from app.menu.models import ItemMenu


def obtener_item(item_id: int) -> ItemMenu | None:
    """Devuelve el ítem de menú si existe, o None si no existe.

    `pedidos.service` usa esta función para validar el ítem y obtener
    su precio antes de crear un pedido, sin conocer cómo se almacenan
    los ítems internamente.
    """
    return repository.buscar_por_id(item_id)
