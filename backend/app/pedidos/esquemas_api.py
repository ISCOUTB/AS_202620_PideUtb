"""Forma que el contexto Pedidos publica por HTTP.

Debe coincidir con `docs/api/openapi.yaml`; que coincida lo verifica
`tests/test_contrato_api.py`.
"""
from pydantic import BaseModel, Field

from app.pedidos.contracts import EstadoPedido, EstadoSolicitable, PedidoPublicado


class CrearPedidoRequest(BaseModel):
    """Lo único que el cliente decide es qué ítem quiere y cuántos.

    `establecimiento_id` NO se acepta del cliente: es un dato derivado del
    ítem. Aceptarlo permitía crear pedidos asignados a un establecimiento
    que no vende ese producto (ver `docs/violaciones.md`, V-01). Un campo
    extra en la petición se ignora en lugar de producir un error, y eso forma
    parte del contrato: un cliente antiguo que siga enviándolo no se rompe,
    pero tampoco consigue influir en el resultado.
    """

    item_id: int = Field(ge=1)
    cantidad: int = Field(default=1, ge=1, le=50)


class PedidoResponse(BaseModel):
    """Representación pública de un pedido."""

    pedido_id: int = Field(ge=1)
    establecimiento_id: int = Field(ge=1)
    item_id: int = Field(ge=1)
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_centavos: int = Field(ge=0)
    estado: EstadoPedido

    #: Sin valor por defecto a propósito: así queda declarado como **requerido
    #: y anulable** en lugar de opcional. El consumidor encuentra siempre la
    #: clave y solo tiene que mirar si vale `null`, en vez de distinguir entre
    #: «ausente» y «vacío», que es una fuente clásica de fallos en el cliente.
    codigo_canje: str | None

    @classmethod
    def desde_contrato(cls, pedido: PedidoPublicado) -> "PedidoResponse":
        return cls(**pedido.model_dump())


class CambiarEstadoRequest(BaseModel):
    """Estado al que el mostrador quiere llevar el pedido.

    Usa `EstadoSolicitable` y no `EstadoPedido` completo. La consecuencia
    práctica es que los dos modos de fallo quedan separados por código HTTP, y
    cada uno dice algo distinto:

    - **`422`** — «ese estado no es algo que puedas pedir». Es el caso de
      `pagado`: no lo decide el mostrador, lo decide el webhook firmado de la
      pasarela.
    - **`409`** — «ese estado es pedible, pero no desde donde está el pedido».
      Lo responde la lógica de negocio, con el estado actual en el mensaje,
      porque quien atiende suele tener la pantalla desactualizada.

    Meter todo en un solo código habría perdido esa distinción, que es
    justamente la que le dice a quien atiende si el problema es suyo o de otro.
    """

    estado: EstadoSolicitable


class ListaDePedidosResponse(BaseModel):
    """Pedidos de un establecimiento.

    Va envuelto en un objeto y no como array en la raíz, por el mismo motivo
    que la carta: con un sobre, añadir paginación o un total más adelante es un
    campo nuevo en una respuesta —cambio compatible—; con un array en la raíz
    sería una rotura.
    """

    establecimiento_id: int = Field(ge=1)
    pedidos: list[PedidoResponse]
