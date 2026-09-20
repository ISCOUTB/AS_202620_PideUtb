"""Lógica de negocio del contexto Pedidos.

`crear_pedido` orquesta dos llamadas a interfaces PÚBLICAS de otros
contextos —Catálogo, para validar el ítem y conocer su precio; Cuentas,
para saber si el establecimiento está operando— y persiste el pedido a
través de `pedidos.repository`.

Pedidos es el único escritor de `Pedido`. No escribe nada del catálogo ni
de las cuentas.

Las funciones públicas reciben valores simples y devuelven
`contracts.PedidoPublicado`, nunca la entidad interna ni el esquema HTTP. Así
el servicio no sabe que existe una API REST: si mañana el pedido se crea desde
un consumidor de cola en vez de desde un `POST`, este archivo no cambia.
"""
import secrets

from app.eventos import CANAL_PEDIDO_PAGADO, publicar
from app.menu import service as catalogo_service
from app.pedidos import repository
from app.pedidos.contracts import EstadoPedido, PedidoPublicado
from app.pedidos.models import Pedido
from app.usuarios import service as cuentas_service

#: Alfabeto del código de canje. Debe respetar el `pattern` declarado para
#: `codigo_canje` en docs/api/openapi.yaml.
_ALFABETO_CANJE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_LONGITUD_CANJE = 6


class ItemNoEncontradoError(Exception):
    pass


class ItemNoDisponibleError(Exception):
    pass


class EstablecimientoInactivoError(Exception):
    pass


class PedidoNoEncontradoError(Exception):
    pass


def _publicar(pedido: Pedido) -> PedidoPublicado:
    return PedidoPublicado(
        pedido_id=pedido.id,
        establecimiento_id=pedido.establecimiento_id,
        item_id=pedido.item_id,
        nombre_item=pedido.nombre_item,
        precio_unitario_centavos=pedido.precio_unitario_centavos,
        cantidad=pedido.cantidad,
        total_centavos=pedido.total_centavos,
        estado=pedido.estado,
        codigo_canje=pedido.codigo_canje,
    )


def _generar_codigo_canje() -> str:
    """Genera un código impredecible.

    Se usa `secrets` y no `random`: el código es lo único que se presenta para
    retirar comida ya pagada, así que un generador cuya secuencia se puede
    predecir a partir de un código observado permitiría reclamar el pedido de
    otra persona. Es el requisito de seguridad de ESC-04.
    """
    return "".join(secrets.choice(_ALFABETO_CANJE) for _ in range(_LONGITUD_CANJE))


def crear_pedido(item_id: int, cantidad: int) -> PedidoPublicado:
    item = catalogo_service.obtener_item(item_id)

    if item is None:
        raise ItemNoEncontradoError(f"El ítem {item_id} no existe")

    if not item.disponible:
        raise ItemNoDisponibleError(f"El ítem '{item.nombre}' no está disponible")

    # El establecimiento se DERIVA del ítem, y quien dice si está operando
    # es el contexto Cuentas, su único escritor (ADR-0002).
    if not cuentas_service.establecimiento_esta_activo(item.establecimiento_id):
        raise EstablecimientoInactivoError(
            f"El establecimiento {item.establecimiento_id} no está recibiendo pedidos"
        )

    pedido = Pedido(
        id=repository.siguiente_id(),
        establecimiento_id=item.establecimiento_id,
        item_id=item.item_id,
        nombre_item=item.nombre,
        precio_unitario_centavos=item.precio_centavos,
        cantidad=cantidad,
        total_centavos=item.precio_centavos * cantidad,
        estado=EstadoPedido.PENDIENTE_PAGO,
    )
    return _publicar(repository.guardar(pedido))


def obtener_pedido(pedido_id: int) -> PedidoPublicado | None:
    """Estado actual de un pedido.

    Es la consulta con la que el frontend cierra el flujo de pago: como la
    confirmación llega por un canal asíncrono que no controlamos, el cliente
    necesita poder preguntar en vez de quedarse esperando
    (ADR-0003).
    """
    pedido = repository.buscar_por_id(pedido_id)
    return None if pedido is None else _publicar(pedido)


def confirmar_pago(pedido_id: int) -> tuple[PedidoPublicado, bool]:
    """Marca el pedido como pagado y genera su código de canje.

    Devuelve `(pedido, ya_estaba_pagado)`. **Es idempotente**: si el pedido ya
    estaba pagado no se genera un segundo código ni se vuelve a publicar el
    evento, y se indica con `True`.

    La idempotencia no es un detalle de implementación sino una obligación del
    contrato: la pasarela entrega al-menos-una-vez y reintenta si no recibe
    `2xx`, así que el mismo aviso llegará repetido más de una vez en la vida
    del sistema (`docs/api/asyncapi.yaml`, `recibirTransaccionActualizada`).

    Solo Pedidos puede hacer esta transición, porque es el único escritor de
    `Pedido`. `pagos` la solicita, no la ejecuta.
    """
    pedido = repository.buscar_por_id(pedido_id)
    if pedido is None:
        raise PedidoNoEncontradoError(f"El pedido {pedido_id} no existe")

    if pedido.estado is not EstadoPedido.PENDIENTE_PAGO:
        return _publicar(pedido), True

    confirmado = pedido.model_copy(
        update={
            "estado": EstadoPedido.PAGADO,
            "codigo_canje": _generar_codigo_canje(),
        }
    )
    repository.guardar(confirmado)

    # El evento se publica DESPUÉS de persistir, nunca antes: anunciar un hecho
    # que todavía podría no ocurrir obliga a compensarlo después, y ese es el
    # tipo de deuda que la integración asíncrona debe evitar, no crear.
    publicar(
        CANAL_PEDIDO_PAGADO,
        {
            "pedido_id": confirmado.id,
            "establecimiento_id": confirmado.establecimiento_id,
            "codigo_canje": confirmado.codigo_canje,
        },
    )

    return _publicar(confirmado), False
