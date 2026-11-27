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

from app.menu.contracts import ItemDisponible, TipoDeProducto


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
    #: Comida, bebida o acompañante: lo que el sitio necesita para apagar el «+»
    #: antes de que la API rechace el pedido por pasarse del tope de su tipo.
    tipo: TipoDeProducto | None
    descripcion: str | None

    #: Precio normal, solo mientras la promoción está en curso, para que la
    #: carta pueda tacharlo. Es la API quien resuelve la franja: el navegador
    #: no decide a qué precio se vende, entre otras cosas porque su reloj no es
    #: de fiar.
    precio_antes_centavos: int | None
    promocion_hasta: str | None
    sugerido: bool

    #: Cuántas quedan hoy, o `null` si este producto no lleva cuenta
    #: (ADR-0015). Requerido y anulable como los demás. Es lo que le permite a
    #: la carta avisar «quedan 2» y apagar el «+» antes de que `crearPedido`
    #: responda `409`; quien decide si alcanza sigue siendo la API.
    unidades_hoy: int | None

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
            tipo=item.tipo,
            descripcion=item.descripcion,
            precio_antes_centavos=item.precio_antes_centavos,
            promocion_hasta=item.promocion_hasta,
            sugerido=item.sugerido,
            unidades_hoy=item.unidades_hoy,
        )


class InventarioDelDiaRequest(BaseModel):
    """Cuántas unidades hay hoy de un producto, según el mostrador.

    Es lo único que el mostrador puede escribir del catálogo por HTTP, y el
    cuerpo tiene un solo campo a propósito: la forma de la petición dice qué
    está permitido tocar, igual que `CambiarEstadoRequest` con el estado.

    `null` **apaga** el control: el producto vuelve a venderse sin descontar,
    que es como se vendían todos antes de la 6.1.0. Cero lo deja agotado. El
    tope de 999 no es un dato del negocio sino un freno a un error de tecleo:
    ningún mostrador del campus prepara mil unidades de nada en un día.
    """

    unidades_hoy: int | None = Field(ge=0, le=999)


class ListaItemsMenuResponse(BaseModel):
    """Sobre con la lista dentro, nunca una lista desnuda.

    Devolver `[...]` en la raíz condena cualquier metadato futuro —paginación,
    total, momento de la consulta— a ser un cambio incompatible. Con el sobre,
    añadirlos es un campo nuevo en una respuesta, que la política clasifica
    como compatible.
    """

    establecimiento_id: int = Field(ge=1)
    items: list[ItemMenuResponse]

    #: Entre qué horas se puede programar una recogida, hora local de Bogotá. Es
    #: texto por lo mismo que `promocion_hasta`, y nulo si el establecimiento no
    #: publica su horario. El sitio solo lo usa para orientar: quien valida la
    #: hora es `crearPedido`.
    hora_apertura: str | None
    hora_cierre: str | None
