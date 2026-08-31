from fastapi import APIRouter, HTTPException

from app.menu import service

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/{item_id}")
def obtener_item(item_id: int):
    item = service.obtener_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
    return item
