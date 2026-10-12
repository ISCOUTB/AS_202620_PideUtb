"""Frontera HTTP del contexto Pedidos.

El router es el único que traduce excepciones de dominio a códigos HTTP
(arc42 §8.4): el servicio no conoce el protocolo.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.autenticacion import establecimiento_que_puede_ver, personal_de_establecimiento

from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.pedidos import service
from app.pedidos.contracts import EstadoPedido
from app.usuarios.contracts import UsuarioAutenticado
from app.pedidos.esquemas_api import (
    CambiarEstadoRequest,
    CrearPedidoRequest,
    ListaDePedidosResponse,
    PedidoResponse,
)

router = APIRouter(prefix="/v1/pedidos", tags=["pedidos"])


@router.post(
    "",
    status_code=201,
    response_model=PedidoResponse,
    responses={404: {"model": ErrorDeNegocio}, 409: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Crea un pedido.",
)
def crear_pedido(datos: CrearPedidoRequest) -> PedidoResponse:
    try:
        pedido = service.crear_pedido(datos.item_id, datos.cantidad)
    except service.ItemNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.ItemNoDisponibleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except service.EstablecimientoInactivoError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return PedidoResponse.desde_contrato(pedido)


@router.get(
    "/{pedido_id}",
    response_model=PedidoResponse,
    responses={404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Consulta un pedido y su estado.",
)
def obtener_pedido(pedido_id: int) -> PedidoResponse:
    pedido = service.obtener_pedido(pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"El pedido {pedido_id} no existe")
    return PedidoResponse.desde_contrato(pedido)


@router.get(
    "",
    response_model=ListaDePedidosResponse,
    responses={
        401: {"model": ErrorDeNegocio},
        403: {"model": ErrorDeNegocio},
        422: {"model": ErrorDeValidacion},
    },
    summary="Lista los pedidos del establecimiento de la sesión.",
)
def listar_pedidos(
    usuario: UsuarioAutenticado = Depends(personal_de_establecimiento),
    establecimiento_id: int | None = Query(
        default=None,
        ge=1,
        description=(
            "Solo para administradores. El personal opera sobre su propio "
            "establecimiento y recibe `403` si indica otro."
        ),
    ),
) -> ListaDePedidosResponse:
    """Los pedidos que el mostrador tiene que atender.

    **El establecimiento sale de la sesión, no del parámetro.** Antes era un
    parámetro obligatorio y cualquiera podía pedir el de otro
    ([V-10](../../../docs/violaciones.md)); ahora el parámetro solo sirve para
    que un administrador elija, y para el personal es como mucho una forma de
    pedir algo que no le corresponde.
    """
    efectivo = establecimiento_que_puede_ver(usuario, establecimiento_id)
    pedidos = service.listar_por_establecimiento(efectivo)
    return ListaDePedidosResponse(
        establecimiento_id=efectivo,
        pedidos=[PedidoResponse.desde_contrato(p) for p in pedidos],
    )


@router.post(
    "/{pedido_id}/estado",
    response_model=PedidoResponse,
    responses={
        401: {"model": ErrorDeNegocio},
        403: {"model": ErrorDeNegocio},
        404: {"model": ErrorDeNegocio},
        409: {"model": ErrorDeNegocio},
        422: {"model": ErrorDeValidacion},
    },
    summary="Avanza el estado de un pedido del establecimiento de la sesión.",
)
def cambiar_estado(
    pedido_id: int,
    datos: CambiarEstadoRequest,
    usuario: UsuarioAutenticado = Depends(personal_de_establecimiento),
) -> PedidoResponse:
    """Mueve el pedido dentro de la máquina de estados del mostrador.

    Es un sub-recurso con nombre (`/estado`) y no un `PATCH` sobre el pedido a
    propósito: `PATCH /v1/pedidos/{id}` sugeriría que cualquier campo se puede
    modificar, y aquí lo único que el mostrador puede tocar es el estado. La
    forma de la ruta dice qué está permitido.

    Devuelve `409` —y no `422`— cuando la transición no está permitida: la
    petición está bien formada, lo que no encaja es el estado del recurso.
    """
    try:
        # `EstadoSolicitable` es un subconjunto de `EstadoPedido` y los
        # valores coinciden; la conversión es explícita para que el
        # servicio siga hablando solo el lenguaje del dominio.
        pedido = service.avanzar_estado(
            pedido_id,
            EstadoPedido(datos.estado.value),
            establecimiento_id=establecimiento_que_puede_ver(usuario, None),
            codigo_canje=datos.codigo_canje,
        )
    except service.PedidoNoEncontradoError as e:
        # También se llega aquí cuando el pedido existe pero es de otro
        # establecimiento. Es deliberado: distinguirlo con un 403 confirmaría
        # que existe, y permitiría enumerar los pedidos del campus.
        raise HTTPException(status_code=404, detail=str(e))
    except service.TransicionNoPermitidaError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except service.CodigoDeCanjeInvalidoError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return PedidoResponse.desde_contrato(pedido)
