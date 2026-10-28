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
    #: Sin valor por defecto, igual que `codigo_canje` en `PedidoResponse`:
    #: así quedan declarados como **requeridos y anulables** en lugar de
    #: opcionales. El consumidor encuentra siempre la clave y solo mira si vale
    #: `null`, en vez de distinguir entre «ausente» y «vacío».
    imagen: str | None
    categoria: str | None
    descripcion: str | None

    #: Precio normal, solo mientras la promoción está en curso, para que la
    #: carta pueda tacharlo. Es la API quien resuelve la franja: el navegador
    #: no decide a qué precio se vende, entre otras cosas porque su reloj no es
    #: de fiar.
    precio_antes_centavos: int | None
    promocion_hasta: str | None

    @classmethod
    def desde_contrato(cls, item: ItemDisponible) -> "ItemMenuResponse":
        return cls(
            item_id=item.item_id,
            establecimiento_id=item.establecimiento_id,
            nombre=item.nombre,
            precio_centavos=item.precio_centavos,
            disponible=item.disponible,
            imagen=item.imagen,
            categoria=item.categoria,
            descripcion=item.descripcion,
            precio_antes_centavos=item.precio_antes_centavos,
            promocion_hasta=item.promocion_hasta,
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
