"""Lógica de negocio del contexto Pedidos.

`crear_pedido` orquesta dos llamadas a interfaces PÚBLICAS de otros
contextos —Catálogo, para validar el ítem y conocer su precio; Cuentas,
para saber si el establecimiento está operando— y persiste el pedido a
través de `pedidos.repository`.

Pedidos es el único escritor de `Pedido`. No escribe nada del catálogo ni
de las cuentas.
"""
from app.menu import service as catalogo_service
from app.pedidos import repository
from app.pedidos.models import CrearPedidoRequest, Pedido
from app.usuarios import service as cuentas_service


class ItemNoEncontradoError(Exception):
    pass


class ItemNoDisponibleError(Exception):
    pass


class EstablecimientoInactivoError(Exception):
    pass


def crear_pedido(datos: CrearPedidoRequest) -> Pedido:
    item = catalogo_service.obtener_item(datos.item_id)

    if item is None:
        raise ItemNoEncontradoError(f"El ítem {datos.item_id} no existe")

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
        precio_unitario=item.precio,
        cantidad=datos.cantidad,
        total=item.precio * datos.cantidad,
        estado="pendiente_pago",
    )
    return repository.guardar(pedido)
