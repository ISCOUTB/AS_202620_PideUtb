"""Frontera HTTP del contexto Pedidos.

El router es el único que traduce excepciones de dominio a códigos HTTP
(arc42 §8.4): el servicio no conoce el protocolo.
"""
from fastapi import APIRouter, HTTPException

from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.pedidos import service
from app.pedidos.esquemas_api import CrearPedidoRequest, PedidoResponse

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
