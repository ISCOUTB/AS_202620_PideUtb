from fastapi import APIRouter, HTTPException

from app.menu import service
from app.menu.contracts import ItemDisponible

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/{item_id}", response_model=ItemDisponible)
def obtener_item(item_id: int) -> ItemDisponible:
    item = service.obtener_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem de menú no encontrado")
    return item
