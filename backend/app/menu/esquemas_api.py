"""Forma que el contexto Catálogo publica por HTTP.

Tercera superficie del módulo, y conviene no confundirla con las otras dos:

| Archivo | Frontera | Público |
|---|---|---|
| `models.py` | ninguna — interno | El propio módulo |
| `contracts.py` | entre contextos, en proceso | `pedidos`, `usuarios` |
| `esquemas_api.py` | HTTP, fuera del sistema | Frontend y cualquier cliente |

Separarlas cuesta un archivo y evita que un refactor interno se convierta en
un cambio incompatible para clientes que no controlamos: `menu.contracts`
puede cambiar en un commit porque sus dos consumidores viven en este
repositorio, mientras que cambiar esto exige la ceremonia de
`docs/api/politica-versionado.md`.

Estos tipos deben coincidir con `docs/api/openapi.yaml`, y que coincidan lo
verifica `tests/test_contrato_api.py`.
"""
from pydantic import BaseModel, Field

from app.menu.contracts import ItemDisponible


class ItemMenuResponse(BaseModel):
    """Representación pública de un ítem del catálogo."""

    item_id: int = Field(ge=1)
    establecimiento_id: int = Field(ge=1)
    nombre: str = Field(min_length=1, max_length=80)
    precio_centavos: int = Field(ge=0)
    disponible: bool

    @classmethod
    def desde_contrato(cls, item: ItemDisponible) -> "ItemMenuResponse":
        return cls(
            item_id=item.item_id,
            establecimiento_id=item.establecimiento_id,
            nombre=item.nombre,
            precio_centavos=item.precio_centavos,
            disponible=item.disponible,
        )


class ListaItemsMenuResponse(BaseModel):
    """Sobre con la lista dentro, nunca una lista desnuda.

    Devolver `[...]` en la raíz condena cualquier metadato futuro —paginación,
    total, momento de la consulta— a ser un cambio incompatible. Con el sobre,
    añadirlos es un campo nuevo en una respuesta, que la política clasifica
    como compatible.
    """

    establecimiento_id: int = Field(ge=1)
    items: list[ItemMenuResponse]
