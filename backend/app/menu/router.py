"""Frontera HTTP del contexto Catálogo.

Las rutas viven bajo `/v1` porque el prefijo es lo que permite que una futura
versión incompatible conviva con esta en lugar de reemplazarla
(`docs/api/politica-versionado.md` §1).

Cada respuesta de error se declara explícitamente en el decorador, y no se
deja que el framework las omita: un código de respuesta que el contrato promete
pero la aplicación no documenta es exactamente la divergencia que
`tests/test_contrato_api.py` está puesto a detectar.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.autenticacion import establecimiento_que_puede_ver, personal_de_establecimiento
from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.menu import service
from app.menu.esquemas_api import (
    InventarioDelDiaRequest,
    ItemMenuResponse,
    ListaItemsMenuResponse,
)
from app.usuarios.contracts import UsuarioAutenticado

router = APIRouter(prefix="/v1/menu", tags=["menu"])


@router.get(
    "/items/{item_id}",
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
    responses={404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Lista los ítems que ofrece un establecimiento.",
)
def listar_items(
    establecimiento_id: int,
    solo_disponibles: Annotated[
        bool,
        Query(description="Si es `true`, omite los ítems marcados como no disponibles."),
    ] = False,
) -> ListaItemsMenuResponse:
    try:
        items = service.listar_items_de_establecimiento(
            establecimiento_id, solo_disponibles=solo_disponibles
        )
    except service.EstablecimientoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))

    apertura, cierre = service.horario_de_atencion(establecimiento_id)
    return ListaItemsMenuResponse(
        establecimiento_id=establecimiento_id,
        items=[ItemMenuResponse.desde_contrato(item) for item in items],
        hora_apertura=apertura,
        hora_cierre=cierre,
    )


@router.post(
    "/items/{item_id}/inventario",
    responses={
        401: {"model": ErrorDeNegocio},
        403: {"model": ErrorDeNegocio},
        404: {"model": ErrorDeNegocio},
        422: {"model": ErrorDeValidacion},
    },
    summary="Fija cuántas unidades hay hoy de un ítem del establecimiento de la sesión.",
)
def fijar_inventario_del_dia(
    item_id: int,
    datos: InventarioDelDiaRequest,
    usuario: Annotated[UsuarioAutenticado, Depends(personal_de_establecimiento)],
) -> ItemMenuResponse:
    """El mostrador cuenta lo que tiene en la vitrina y lo escribe aquí.

    Es un sub-recurso con nombre (`/inventario`) y no un `PATCH` sobre el ítem,
    por coherencia con `/estado` en Pedidos: `PATCH /v1/menu/items/{id}`
    sugeriría que el precio o el nombre también se pueden cambiar desde el
    mostrador, y lo único que puede tocar es el conteo del día. La forma de la
    ruta dice qué está permitido. Y es `POST` y no `PUT` porque no reemplaza el
    ítem: le ordena algo a uno que ya existe.

    **El establecimiento sale de la sesión, no de la petición**, igual que en la
    cola del mostrador. Un ítem de otro establecimiento responde `404` y no
    `403`: confirmar que existe permitiría recorrer la carta ajena probando
    identificadores.
    """
    item = service.fijar_unidades_del_dia(
        item_id,
        datos.unidades_hoy,
        establecimiento_id=establecimiento_que_puede_ver(usuario, None),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
    return ItemMenuResponse.desde_contrato(item)
