"""Acceso a datos del contexto Catálogo.

Implementación en memoria para esta entrega, pensada para reemplazarse por
el cliente de Supabase sin cambiar la interfaz pública. Solo este módulo
lee y escribe las tablas del catálogo (`menu_*`).

Los precios están en **centavos de COP**: 400000 son 4 000 pesos.
"""
from app.menu.models import ItemMenu

# TODO(supabase): reemplazar por consultas reales a `menu_items`.
_ITEMS_SEED = {
    1: ItemMenu(id=1, establecimiento_id=1, nombre="Arepa de huevo", precio_centavos=400000, disponible=True),
    2: ItemMenu(id=2, establecimiento_id=1, nombre="Jugo de mango", precio_centavos=300000, disponible=True),
    3: ItemMenu(id=3, establecimiento_id=2, nombre="Empanada", precio_centavos=250000, disponible=False),
    4: ItemMenu(id=4, establecimiento_id=3, nombre="Café americano", precio_centavos=200000, disponible=True),
}


def buscar_por_id(item_id: int) -> ItemMenu | None:
    return _ITEMS_SEED.get(item_id)


def buscar_por_establecimiento(establecimiento_id: int) -> list[ItemMenu]:
    """Ítems de un establecimiento, ordenados de forma estable.

    El orden se fija aquí y no se deja al azar del almacenamiento: una lista
    que cambia de orden entre dos llamadas idénticas obliga al consumidor a
    reordenar por su cuenta, y el contrato no promete ningún criterio.
    """
    return sorted(
        (item for item in _ITEMS_SEED.values() if item.establecimiento_id == establecimiento_id),
        key=lambda item: item.id,
    )
