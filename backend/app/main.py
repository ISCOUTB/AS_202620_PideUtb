from fastapi import FastAPI

from app.menu.router import router as menu_router
from app.pedidos.router import router as pedidos_router

app = FastAPI(title="PideUTB API")

app.include_router(menu_router)
app.include_router(pedidos_router)
# app.include_router(pagos_router)      # pendiente — próxima entrega
# app.include_router(usuarios_router)   # pendiente


@app.get("/health")
def health():
    return {"status": "ok"}
