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


class TransicionNoPermitidaError(Exception):
    """Se pidió llevar un pedido a un estado al que no puede ir desde donde está."""


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

    # El identificador lo asigna el almacenamiento, no este servicio. Antes lo
    # pedía a un contador en memoria del proceso, y con dos instancias
    # desplegadas las dos habrían empezado por 1: era el ejemplo concreto de
    # V-09 (`docs/violaciones.md`).
    pedido = repository.crear(
        establecimiento_id=item.establecimiento_id,
        item_id=item.item_id,
        nombre_item=item.nombre,
        precio_unitario_centavos=item.precio_centavos,
        cantidad=cantidad,
        total_centavos=item.precio_centavos * cantidad,
    )
    return _publicar(pedido)


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

    # La transición va dentro de un `UPDATE ... WHERE estado = 'pendiente_pago'`,
    # no detrás de un `if`. La diferencia importa: la pasarela entrega
    # al-menos-una-vez, así que dos avisos del mismo pago pueden llegar a la vez
    # a dos trabajadores distintos. Con leer-decidir-escribir, los dos verían
    # «pendiente» y se generarían **dos códigos de canje** para un solo pedido.
    #
    # `marcar_pagado` devuelve `None` cuando la fila ya no estaba pendiente, que
    # es exactamente el caso del aviso repetido.
    confirmado = repository.marcar_pagado(pedido_id, _generar_codigo_canje())

    if confirmado is None:
        return _publicar(repository.buscar_por_id(pedido_id)), True

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


#: Qué transiciones puede pedir **el mostrador**.
#:
#: Se declara como dato y no como una cadena de `if`, porque así la regla se
#: puede leer de un vistazo y probar entera. Cada clave es el estado actual;
#: cada valor, los estados a los que ese pedido puede pasar.
#:
#: Dos ausencias son deliberadas y valen más que lo que está:
#:
#: 1. **`PENDIENTE_PAGO` no aparece como origen.** El mostrador no puede
#:    marcar un pedido como pagado. Esa transición la hace `confirmar_pago`,
#:    y solo la dispara el webhook firmado de la pasarela (ADR-0003). Si el
#:    panel pudiera hacerla, cualquiera con un navegador comería gratis: no
#:    hay autenticación todavía ([V-10](../../../docs/violaciones.md)).
#: 2. **`ENTREGADO` y `CANCELADO` no aparecen como origen.** Son estados
#:    finales. Un pedido entregado que vuelve a «en preparación» es un error
#:    de registro, no una operación del negocio, y permitirlo haría imposible
#:    contar cuántos pedidos se sirvieron de verdad.
TRANSICIONES_DEL_MOSTRADOR: dict[EstadoPedido, frozenset[EstadoPedido]] = {
    EstadoPedido.PAGADO: frozenset({EstadoPedido.EN_PREPARACION, EstadoPedido.CANCELADO}),
    EstadoPedido.EN_PREPARACION: frozenset({EstadoPedido.LISTO_PARA_RECOGER, EstadoPedido.CANCELADO}),
    EstadoPedido.LISTO_PARA_RECOGER: frozenset({EstadoPedido.ENTREGADO}),
}


def listar_por_establecimiento(establecimiento_id: int) -> list[PedidoPublicado]:
    """Pedidos de un establecimiento, para el panel del mostrador.

    Devuelve **todos** los estados, incluidos los ya entregados. Ocultarlos
    obligaría a quien atiende a recordar qué acaba de entregar para poder
    corregirse, y ESC-03 pide resolver en tres interacciones, no recordar.
    """
    return [_publicar(p) for p in repository.buscar_por_establecimiento(establecimiento_id)]


def avanzar_estado(pedido_id: int, nuevo_estado: EstadoPedido) -> PedidoPublicado:
    """Mueve un pedido dentro de la máquina de estados del mostrador.

    Es la operación que cierra [ESC-03](../../../docs/arc42/arc42.md#esc-03):
    el establecimiento gestiona el estado de sus pedidos.

    Rechaza con `TransicionNoPermitidaError` cualquier salto que
    `TRANSICIONES_DEL_MOSTRADOR` no contemple, **incluido marcar como pagado**.
    La validación vive aquí y no en el router a propósito: una regla de negocio
    en la capa HTTP solo protege a quien entra por HTTP, y dejaría el camino
    libre a cualquier otro que llame al servicio.
    """
    pedido = repository.buscar_por_id(pedido_id)
    if pedido is None:
        raise PedidoNoEncontradoError(f"El pedido {pedido_id} no existe")

    permitidos = TRANSICIONES_DEL_MOSTRADOR.get(pedido.estado, frozenset())
    if nuevo_estado not in permitidos:
        # El mensaje dice el estado actual, no solo que se rechazó: quien
        # atiende suele tener la pantalla desactualizada porque otra persona
        # ya movió el pedido, y saberlo evita que lo intente otras tres veces.
        raise TransicionNoPermitidaError(
            f"Un pedido en '{pedido.estado.value}' no puede pasar a "
            f"'{nuevo_estado.value}'"
        )

    return _publicar(repository.guardar(pedido.model_copy(update={"estado": nuevo_estado})))
