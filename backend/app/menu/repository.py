"""Acceso a datos del módulo `menu`.

Implementación en memoria para esta entrega, pensada para reemplazarse
por el cliente de Supabase sin cambiar la interfaz pública (misma
firma de `buscar_por_id`). Así `menu.service` no necesita cambiar
cuando se conecte la base de datos real.
"""
from app.menu.models import ItemMenu

# TODO(supabase): reemplazar por consulta real a la tabla `menu_items`.
# Se deja como diccionario en memoria únicamente para tener el corte
# vertical ejecutable sin depender de credenciales de Supabase en esta
# entrega.
_ITEMS_SEED = {
    1: ItemMenu(id=1, establecimiento_id=1, nombre="Arepa de huevo", precio=4000, disponible=True),
    2: ItemMenu(id=2, establecimiento_id=1, nombre="Jugo de mango", precio=3000, disponible=True),
    3: ItemMenu(id=3, establecimiento_id=2, nombre="Empanada", precio=2500, disponible=False),
}


def buscar_por_id(item_id: int) -> ItemMenu | None:
    return _ITEMS_SEED.get(item_id)
