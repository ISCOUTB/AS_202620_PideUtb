"""Punto de entrada de la aplicación.

`version` no es decorativa: es la misma que declara `info.version` en
`docs/api/openapi.yaml`, y `tests/test_contrato_api.py` falla si dejan de
coincidir. Un despliegue que anuncia una versión de contrato distinta de la
que cumple es peor que no anunciar ninguna.
"""
from fastapi import FastAPI

from app.esquemas_comunes import EstadoServicio
from app.menu.router import router as menu_router
from app.pagos.router import router as pagos_router
from app.pedidos.router import router as pedidos_router

app = FastAPI(
    title="PideUTB API",
    version="1.0.0",
    description=(
        "Pedidos de comida dentro del campus universitario. El contrato "
        "versionado que esta aplicación implementa está en "
        "`docs/api/openapi.yaml`; los canales asíncronos, en "
        "`docs/api/asyncapi.yaml`."
    ),
)

app.include_router(menu_router)
app.include_router(pedidos_router)
app.include_router(pagos_router)
# app.include_router(usuarios_router)   # pendiente — autenticación y roles


@app.get(
    "/health",
    tags=["operacion"],
    response_model=EstadoServicio,
    summary="Comprueba que el proceso responde.",
)
def health() -> EstadoServicio:
    """Sonda de vida.

    Queda **fuera de `/v1`** a propósito: es una sonda para la plataforma de
    despliegue, no parte de la superficie de negocio, y por eso no arrastra la
    promesa de compatibilidad de la API
    (`docs/api/politica-versionado.md` §1).
    """
    return EstadoServicio(status="ok")
