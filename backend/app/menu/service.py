"""Interfaz pública del contexto Catálogo (módulo `menu`).

Responde siempre con tipos de `menu.contracts`, nunca con entidades
internas. Ver ADR-0001 (regla de comunicación) y ADR-0002 (lenguaje
publicado y propiedad de los datos de establecimiento).
"""
from app.menu import repository
from app.menu.contracts import ItemDisponible


def obtener_item(item_id: int) -> ItemDisponible | None:
    """Devuelve el ítem publicado si existe, o `None` si no existe.

    `pedidos.service` usa esta función para validar el ítem y conocer su
    precio y a qué establecimiento pertenece, sin saber cómo se almacena
    el catálogo.
    """
    item = repository.buscar_por_id(item_id)
    if item is None:
        return None
    return ItemDisponible(
        item_id=item.id,
        establecimiento_id=item.establecimiento_id,
        nombre=item.nombre,
        precio=item.precio,
        disponible=item.disponible,
    )
