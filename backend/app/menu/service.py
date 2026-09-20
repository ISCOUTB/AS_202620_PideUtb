"""Interfaz pública del contexto Catálogo (módulo `menu`).

Responde siempre con tipos de `menu.contracts`, nunca con entidades
internas. Ver ADR-0001 (regla de comunicación) y ADR-0002 (lenguaje
publicado y propiedad de los datos de establecimiento).
"""
from app.menu import repository
from app.menu.contracts import ItemDisponible
from app.menu.models import ItemMenu
from app.usuarios import service as cuentas_service


class EstablecimientoNoEncontradoError(Exception):
    """El establecimiento consultado no existe en el contexto Cuentas."""


def _publicar(item: ItemMenu) -> ItemDisponible:
    return ItemDisponible(
        item_id=item.id,
        establecimiento_id=item.establecimiento_id,
        nombre=item.nombre,
        precio_centavos=item.precio_centavos,
        disponible=item.disponible,
    )


def obtener_item(item_id: int) -> ItemDisponible | None:
    """Devuelve el ítem publicado si existe, o `None` si no existe.

    `pedidos.service` usa esta función para validar el ítem y conocer su
    precio y a qué establecimiento pertenece, sin saber cómo se almacena
    el catálogo.
    """
    item = repository.buscar_por_id(item_id)
    if item is None:
        return None
    return _publicar(item)


def listar_items_de_establecimiento(
    establecimiento_id: int, solo_disponibles: bool = False
) -> list[ItemDisponible]:
    """Ítems que ofrece un establecimiento.

    Distingue dos situaciones que un cliente necesita separar: el
    establecimiento **no existe** (error, `404`) y el establecimiento existe
    pero **no tiene ítems** (lista vacía, `200`). Devolver lista vacía en
    ambos casos obligaría al frontend a adivinar cuál de las dos ocurrió.

    Quién sabe si el establecimiento existe es el contexto Cuentas, su único
    escritor (ADR-0002); Catálogo lo pregunta en lugar de guardar una copia.
    """
    if cuentas_service.obtener_establecimiento(establecimiento_id) is None:
        raise EstablecimientoNoEncontradoError(
            f"El establecimiento {establecimiento_id} no existe"
        )

    items = repository.buscar_por_establecimiento(establecimiento_id)
    if solo_disponibles:
        items = [item for item in items if item.disponible]

    return [_publicar(item) for item in items]
