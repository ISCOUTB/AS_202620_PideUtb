"""Lógica de negocio del módulo `pedidos`.

Este es el corte vertical de la entrega: `crear_pedido` orquesta una
llamada al servicio PÚBLICO de `menu` (nunca a su repositorio) para
validar el ítem y obtener el precio, y luego persiste el pedido a
través de `pedidos.repository`.
"""
from app.menu import service as menu_service
from app.pedidos import repository
from app.pedidos.models import CrearPedidoRequest, Pedido


class ItemNoEncontradoError(Exception):
    pass


class ItemNoDisponibleError(Exception):
    pass


def crear_pedido(datos: CrearPedidoRequest) -> Pedido:
    item = menu_service.obtener_item(datos.item_id)

    if item is None:
        raise ItemNoEncontradoError(f"El ítem {datos.item_id} no existe")

    if not item.disponible:
        raise ItemNoDisponibleError(f"El ítem '{item.nombre}' no está disponible")

    pedido = Pedido(
        id=repository.siguiente_id(),
        establecimiento_id=datos.establecimiento_id,
        item_id=item.id,
        nombre_item=item.nombre,
        cantidad=datos.cantidad,
        total=item.precio * datos.cantidad,
        estado="pendiente_pago",
    )
    return repository.guardar(pedido)
