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
import hmac
import secrets

from app.eventos import CANAL_PEDIDO_PAGADO, publicar
from app.menu import service as catalogo_service
from app.pedidos import repository
from app.pedidos.contracts import EstadoPedido, LineaPublicada, PedidoPublicado
from app.pedidos.models import LineaPedido, Pedido
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


class CodigoDeCanjeInvalidoError(Exception):
    """El código presentado no es el del pedido, o ya se usó."""


class TransicionNoPermitidaError(Exception):
    """Se pidió llevar un pedido a un estado al que no puede ir desde donde está."""


def _publicar(pedido: Pedido, *, con_token: bool = False) -> PedidoPublicado:
    """Vista del pedido hacia fuera.

    `con_token` solo se pide al **crear** el pedido. En cualquier otra lectura
    el token se omite: devolverlo también al consultar lo volvería inútil,
    porque entonces bastaría acertar un identificador una vez para tenerlo para
    siempre. El valor por defecto es el seguro, para que omitirlo por descuido
    no filtre nada.
    """
    return PedidoPublicado(
        pedido_id=pedido.id,
        establecimiento_id=pedido.establecimiento_id,
        lineas=[
            LineaPublicada(
                item_id=l.item_id,
                nombre_item=l.nombre_item,
                precio_unitario_centavos=l.precio_unitario_centavos,
                cantidad=l.cantidad,
                total_linea_centavos=l.total_linea_centavos,
            )
            for l in pedido.lineas
        ],
        total_centavos=pedido.total_centavos,
        token_consulta=pedido.token_consulta if con_token else None,
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


class CarritoVacioError(Exception):
    """Un pedido sin líneas no es un pedido."""


class ItemRepetidoError(Exception):
    """El mismo producto dos veces en el mismo carrito."""


def crear_pedido(lineas_pedidas: list[tuple[int, int]]) -> PedidoPublicado:
    """Crea un pedido con una o varias líneas.

    `lineas_pedidas` son pares `(item_id, cantidad)`. Se valida **todo** antes
    de escribir nada: un carrito con un producto agotado se rechaza entero, y
    no a medias. Un pedido parcial sería peor que ninguno — el cliente pagaría
    por algo distinto de lo que pidió.
    """
    if not lineas_pedidas:
        raise CarritoVacioError("El pedido no lleva ningún producto")

    vistos = {item_id for item_id, _ in lineas_pedidas}
    if len(vistos) != len(lineas_pedidas):
        # La base también lo impide, pero un 409 explicado es mejor que un
        # error de integridad: aquí sabemos *qué* producto se repitió.
        raise ItemRepetidoError(
            "El mismo producto aparece dos veces; aumentá su cantidad en lugar "
            "de añadirlo otra vez"
        )

    lineas: list[LineaPedido] = []
    establecimiento_id: int | None = None

    for item_id, cantidad in lineas_pedidas:
        item = catalogo_service.obtener_item(item_id)

        if item is None:
            raise ItemNoEncontradoError(f"El ítem {item_id} no existe")

        if not item.disponible:
            raise ItemNoDisponibleError(f"El ítem '{item.nombre}' no está disponible")

        # Todas las líneas tienen que ser del mismo establecimiento: un pedido
        # se recoge en un mostrador, no en dos. Como el establecimiento se
        # deriva del ítem, mezclarlos solo puede venir de un carrito armado a
        # mano contra la API.
        if establecimiento_id is None:
            establecimiento_id = item.establecimiento_id
        elif item.establecimiento_id != establecimiento_id:
            raise EstablecimientoInactivoError(
                "Un pedido no puede mezclar productos de dos establecimientos"
            )

        lineas.append(
            LineaPedido(
                item_id=item.item_id,
                nombre_item=item.nombre,
                precio_unitario_centavos=item.precio_centavos,
                cantidad=cantidad,
                total_linea_centavos=item.precio_centavos * cantidad,
            )
        )

    # El establecimiento se DERIVA de los ítems, y quien dice si está operando
    # es el contexto Cuentas, su único escritor (ADR-0002).
    if not cuentas_service.establecimiento_esta_activo(establecimiento_id):
        raise EstablecimientoInactivoError(
            f"El establecimiento {establecimiento_id} no está recibiendo pedidos"
        )

    # El identificador lo asigna el almacenamiento, no este servicio. Antes lo
    # pedía a un contador en memoria del proceso, y con dos instancias
    # desplegadas las dos habrían empezado por 1: era el ejemplo concreto de
    # V-09 (`docs/violaciones.md`).
    # El token lo genera el servicio y no el repositorio, para que las dos
    # implementaciones reciban el mismo valor en vez de cada una el suyo.
    #
    # `token_urlsafe(24)` son 192 bits. Es más de lo que haría falta: lo que
    # protege no es un secreto de larga vida, sino un identificador que no se
    # pueda adivinar partiendo del número de pedido, que sí es secuencial.
    pedido = repository.crear(
        establecimiento_id=establecimiento_id,
        lineas=lineas,
        total_centavos=sum(l.total_linea_centavos for l in lineas),
        token_consulta=secrets.token_urlsafe(24),
    )

    # **El único sitio donde el token sale.**
    return _publicar(pedido, con_token=True)


def obtener_pedido(pedido_id: int) -> PedidoPublicado | None:
    """Estado actual de un pedido, **para uso interno del proceso**.

    No pide token: quien la llama es otro contexto dentro de la misma
    aplicación, no alguien de fuera. La consulta que atiende peticiones HTTP es
    `consultar_pedido`, y están separadas a propósito — con un solo argumento
    opcional, olvidarlo abriría la puerta sin que se notara al leer la llamada.
    """
    pedido = repository.buscar_por_id(pedido_id)
    return None if pedido is None else _publicar(pedido)


def consultar_pedido(pedido_id: int, token_consulta: str) -> PedidoPublicado | None:
    """Estado de un pedido para quien lo hizo. **Exige su token.**

    Es la consulta con la que el cliente cierra el flujo de pago: como la
    confirmación llega por un canal asíncrono que no controlamos, necesita poder
    preguntar en vez de quedarse esperando (ADR-0003).

    ### Por qué hace falta un token

    Los identificadores de pedido son secuenciales y esta consulta no exigía
    nada, así que **cualquiera podía recorrer `/v1/pedidos/1`, `/2`, `/3`… y
    cosechar los códigos de canje** de los pedidos pagados, que es el papel con
    el que se recoge la comida. No hay cuentas de cliente —y es una decisión,
    no una carencia (arc42 §8.8)—, así que lo que identifica al dueño del
    pedido no puede ser una sesión: es un token opaco que recibió al crearlo.

    ### Por qué `None` y no un error distinto

    Un token equivocado y un pedido inexistente devuelven lo mismo, y el router
    los convierte en el mismo `404`. Es el criterio que I-1 ya fijó para la
    cola del mostrador: un `403` confirmaría que el pedido existe, que es
    justo lo que no hay que confirmar a quien está probando números.

    La comparación es en tiempo constante por el mismo motivo que la firma de
    la pasarela: una que termina en el primer byte distinto filtra, por su
    duración, cuántos acertó.
    """
    pedido = repository.buscar_por_id(pedido_id)
    if pedido is None:
        return None

    if not hmac.compare_digest(pedido.token_consulta, token_consulta):
        return None

    return _publicar(pedido)


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


def ids_pagados() -> list[int]:
    """Los pedidos que están pagados, por identificador.

    Es la puerta por la que Pagos puede preguntar sin leer la tabla de Pedidos:
    [ADR-0001](../../../docs/adr/0001-estilo-arquitectonico.md) permite llamar a
    la función pública de otro contexto y prohíbe tocar su almacenamiento.
    """
    return repository.buscar_ids_pagados()


def listar_por_establecimiento(establecimiento_id: int) -> list[PedidoPublicado]:
    """Pedidos de un establecimiento, para el panel del mostrador.

    Devuelve **todos** los estados, incluidos los ya entregados. Ocultarlos
    obligaría a quien atiende a recordar qué acaba de entregar para poder
    corregirse, y ESC-03 pide resolver en tres interacciones, no recordar.
    """
    return [_publicar(p) for p in repository.buscar_por_establecimiento(establecimiento_id)]


def avanzar_estado(
    pedido_id: int,
    nuevo_estado: EstadoPedido,
    *,
    establecimiento_id: int,
    codigo_canje: str | None = None,
) -> PedidoPublicado:
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

    # Un pedido de otro establecimiento se trata como inexistente, no como
    # prohibido. Responder «no podés tocar ese» confirmaría que existe, y eso
    # permite enumerar los pedidos del campus probando identificadores.
    if pedido.establecimiento_id != establecimiento_id:
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

    # Entregar exige presentar el código, que es lo que cierra ESC-04.
    #
    # La comprobación va aquí, en la última transición, y no en un endpoint
    # aparte: así el código no es un trámite opcional sino la condición para que
    # el pedido salga del mostrador.
    #
    # El rechazo del 100 % de las reutilizaciones no necesita código propio: sale
    # de que `entregado` sea un estado final. El segundo intento no falla por el
    # código sino porque ya no hay transición desde ahí.
    if nuevo_estado is EstadoPedido.ENTREGADO:
        if not codigo_canje or not _codigo_coincide(codigo_canje, pedido.codigo_canje):
            raise CodigoDeCanjeInvalidoError(
                "El código de canje no corresponde a este pedido."
            )

    return _publicar(repository.guardar(pedido.model_copy(update={"estado": nuevo_estado})))


def _codigo_coincide(presentado: str, real: str | None) -> bool:
    """Compara en tiempo constante y sin distinguir mayúsculas.

    `compare_digest` y no `==` por el mismo motivo que en la firma del webhook:
    una comparación que termina en el primer carácter distinto filtra, por su
    duración, cuántos acertó quien la intenta. Aquí el alfabeto es pequeño y el
    código corto, así que esa fuga es aprovechable de verdad.

    Sin distinguir mayúsculas porque el código se dicta en voz alta en un
    mostrador, y quien lo teclea no debería fallar por eso.
    """
    if real is None:
        return False
    return secrets.compare_digest(presentado.strip().upper(), real.upper())
