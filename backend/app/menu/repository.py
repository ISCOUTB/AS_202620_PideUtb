"""Acceso a datos del contexto Catálogo.

Implementación en memoria para esta entrega, pensada para reemplazarse por
el cliente de Supabase sin cambiar la interfaz pública. Solo este módulo
lee y escribe las tablas del catálogo (`menu_*`).
"""
from app.menu.models import ItemMenu

# TODO(supabase): reemplazar por consultas reales a `menu_items`.
_ITEMS_SEED = {
    1: ItemMenu(id=1, establecimiento_id=1, nombre="Arepa de huevo", precio=4000, disponible=True),
    2: ItemMenu(id=2, establecimiento_id=1, nombre="Jugo de mango", precio=3000, disponible=True),
    3: ItemMenu(id=3, establecimiento_id=2, nombre="Empanada", precio=2500, disponible=False),
    4: ItemMenu(id=4, establecimiento_id=3, nombre="Café americano", precio=2000, disponible=True),
}


def buscar_por_id(item_id: int) -> ItemMenu | None:
    return _ITEMS_SEED.get(item_id)
