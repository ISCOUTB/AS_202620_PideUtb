"""Lenguaje publicado del contexto Pedidos.

Lo que otros contextos —hoy `pagos`— pueden conocer de un pedido. Igual que en
`menu.contracts`, separarlo del modelo interno permite que la entidad
almacenada evolucione sin arrastrar a quien la consume.

`EstadoPedido` vive aquí y no en `models.py` a propósito: el conjunto de
estados **es** parte del lenguaje publicado. Mientras fue texto libre
(`docs/violaciones.md`, V-08) ningún consumidor podía saber qué valores debía
estar preparado para recibir, que es tanto como no tener contrato.
"""
from enum import Enum

from pydantic import BaseModel, Field


class EstadoPedido(str, Enum):
    """Conjunto cerrado de estados. Debe coincidir con el `enum` de
    `EstadoPedido` en `docs/api/openapi.yaml`, y que coincida lo verifica
    `tests/test_contrato_api.py`.

    Añadir un valor aquí es un cambio incompatible para los consumidores que
    reciben el estado (`docs/api/politica-versionado.md` §3.1).
    """

    PENDIENTE_PAGO = "pendiente_pago"
    PAGADO = "pagado"
    EN_PREPARACION = "en_preparacion"
    LISTO_PARA_RECOGER = "listo_para_recoger"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class EstadoSolicitable(str, Enum):
    """Estados que **el mostrador** puede pedir para un pedido.

    Es un subconjunto de `EstadoPedido`, y existir por separado resuelve dos
    problemas a la vez.

    **Uno de contrato.** `EstadoPedido` viaja en las respuestas. Si además se
    usara en la petición, el `enum` quedaría en las dos direcciones y quitarle
    un valor pasaría a ser incompatible por la regla **I-7**, no solo por la
    I-8: perdería la evolucionabilidad que la política le reconoce a un `enum`
    de respuesta. Lo detectó una prueba de mutación al intentar justamente eso.

    **Uno de seguridad.** Al no incluir `pendiente_pago` ni `pagado`, la regla
    de que el mostrador **no puede marcar un pedido como pagado** deja de vivir
    solo en el código y pasa a estar escrita en el contrato, donde cualquier
    consumidor la lee sin ejecutar nada.

    El conjunto debe coincidir con los destinos de
    `service.TRANSICIONES_DEL_MOSTRADOR`; que coincida lo verifica
    `tests/test_panel_mostrador.py`.
    """

    EN_PREPARACION = "en_preparacion"
    LISTO_PARA_RECOGER = "listo_para_recoger"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class PedidoPublicado(BaseModel):
    """Vista de un pedido hacia fuera del contexto Pedidos."""

    pedido_id: int
    establecimiento_id: int
    item_id: int
    nombre_item: str
    precio_unitario_centavos: int = Field(ge=0)
    cantidad: int = Field(ge=1, le=50)
    total_centavos: int = Field(ge=0)
    estado: EstadoPedido
    codigo_canje: str | None
