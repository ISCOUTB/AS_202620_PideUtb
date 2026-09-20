"""Frontera HTTP del contexto Catálogo.

Las rutas viven bajo `/v1` porque el prefijo es lo que permite que una futura
versión incompatible conviva con esta en lugar de reemplazarla
(`docs/api/politica-versionado.md` §1).

Cada respuesta de error se declara explícitamente en el decorador, y no se
deja que el framework las omita: un código de respuesta que el contrato promete
pero la aplicación no documenta es exactamente la divergencia que
`tests/test_contrato_api.py` está puesto a detectar.
"""
from fastapi import APIRouter, HTTPException, Query

from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.menu import service
from app.menu.esquemas_api import ItemMenuResponse, ListaItemsMenuResponse

router = APIRouter(prefix="/v1/menu", tags=["menu"])


@router.get(
    "/items/{item_id}",
    response_model=ItemMenuResponse,
    responses={404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Consulta un ítem del menú.",
)
def obtener_item(item_id: int) -> ItemMenuResponse:
    item = service.obtener_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
    return ItemMenuResponse.desde_contrato(item)


@router.get(
    "/establecimientos/{establecimiento_id}/items",
    response_model=ListaItemsMenuResponse,
    responses={404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Lista los ítems que ofrece un establecimiento.",
)
def listar_items(
    establecimiento_id: int,
    solo_disponibles: bool = Query(
        default=False,
        description="Si es `true`, omite los ítems marcados como no disponibles.",
    ),
) -> ListaItemsMenuResponse:
    try:
        items = service.listar_items_de_establecimiento(
            establecimiento_id, solo_disponibles=solo_disponibles
        )
    except service.EstablecimientoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ListaItemsMenuResponse(
        establecimiento_id=establecimiento_id,
        items=[ItemMenuResponse.desde_contrato(item) for item in items],
    )
