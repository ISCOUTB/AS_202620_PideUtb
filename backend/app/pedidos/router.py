"""Frontera HTTP del contexto Pedidos.

El router es el único que traduce excepciones de dominio a códigos HTTP
(arc42 §8.4): el servicio no conoce el protocolo.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

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
    responses={404: {"model": ErrorDeNegocio}, 409: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Crea un pedido.",
)
def crear_pedido(datos: CrearPedidoRequest) -> PedidoResponse:
    try:
        pedido = service.crear_pedido([(l.item_id, l.cantidad) for l in datos.lineas])
    except service.ItemNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.ItemNoDisponibleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except service.ItemRepetidoError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except service.CarritoVacioError as e:
        # 422 y no 409: un carrito vacío es una petición mal formada, no un
        # estado del sistema que impida la operación.
        raise HTTPException(status_code=422, detail=str(e))
    except service.EstablecimientoInactivoError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return PedidoResponse.desde_contrato(pedido)


@router.get(
    "/{pedido_id}",
    responses={404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Consulta un pedido y su estado.",
)
def obtener_pedido(
    pedido_id: int,
    x_token_pedido: Annotated[
        str | None,
        Header(
            alias="X-Token-Pedido",
            description="El `token_consulta` que devolvió `crearPedido`.",
        ),
    ] = None,
) -> PedidoResponse:
    """Exige el token que se entregó al crear el pedido.

    **Antes no exigía nada**, y como los identificadores son secuenciales
    cualquiera podía recorrerlos y cosechar los códigos de canje de los pedidos
    pagados. Ese es el motivo del salto a 4.0.0 y de que se aplique §5 bis de la
    política de versionado: cuando lo viejo **es** el defecto, no hay periodo de
    convivencia que valga, porque el plazo que protege a los consumidores
    protegería también a quien quiera entrar.

    Sin token, con uno equivocado o con un pedido que no existe la respuesta es
    la misma: `404`. Distinguirlos le diría a quien prueba números cuáles
    existen.
    """
    if x_token_pedido is None:
        raise HTTPException(status_code=404, detail=f"El pedido {pedido_id} no existe")

    pedido = service.consultar_pedido(pedido_id, x_token_pedido)
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"El pedido {pedido_id} no existe")
    return PedidoResponse.desde_contrato(pedido)


@router.get(
    "",
    responses={
        401: {"model": ErrorDeNegocio},
        403: {"model": ErrorDeNegocio},
        422: {"model": ErrorDeValidacion},
    },
    summary="Lista los pedidos del establecimiento de la sesión.",
)
def listar_pedidos(
    usuario: Annotated[UsuarioAutenticado, Depends(personal_de_establecimiento)],
    establecimiento_id: Annotated[
        int | None,
        Query(
            ge=1,
            description=(
                "Solo para administradores. El personal opera sobre su propio "
                "establecimiento y recibe `403` si indica otro."
            ),
        ),
    ] = None,
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
    usuario: Annotated[UsuarioAutenticado, Depends(personal_de_establecimiento)],
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
