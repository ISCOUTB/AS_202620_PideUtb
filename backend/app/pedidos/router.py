from fastapi import APIRouter, HTTPException

from app.pedidos import service
from app.pedidos.models import CrearPedidoRequest, Pedido

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", status_code=201, response_model=Pedido)
def crear_pedido(datos: CrearPedidoRequest) -> Pedido:
    try:
        return service.crear_pedido(datos)
    except service.ItemNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.ItemNoDisponibleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except service.EstablecimientoInactivoError as e:
        raise HTTPException(status_code=409, detail=str(e))
