"""Punto de entrada de la aplicación.

`version` no es decorativa: es la misma que declara `info.version` en
`docs/api/openapi.yaml`, y `tests/test_contrato_api.py` falla si dejan de
coincidir. Un despliegue que anuncia una versión de contrato distinta de la
que cumple es peor que no anunciar ninguna.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.esquemas_comunes import EstadoServicio
from app.menu.router import router as menu_router
from app.pagos.router import router as pagos_router
from app.pedidos.router import router as pedidos_router

#: Orígenes autorizados a llamar a la API desde un navegador.
#:
#: En desarrollo, las direcciones locales desde las que se sirve el sitio. En
#: despliegue llegan por variable de entorno, separadas por coma:
#:
#:   PIDEUTB_ORIGENES_PERMITIDOS=https://pideutb-sitio.onrender.com
#:
#: **Nunca `*`.** Un comodín permitiría que cualquier página de Internet
#: llamara a esta API con el navegador de un usuario. Como todavía no hay
#: sesiones ni cookies el daño sería limitado, pero la autenticación es la
#: siguiente entrega y dejar el comodín puesto sería heredar el agujero.
_ORIGENES_POR_DEFECTO = "http://localhost:5500,http://127.0.0.1:5500"

ORIGENES_PERMITIDOS = [
    origen.strip()
    for origen in os.getenv("PIDEUTB_ORIGENES_PERMITIDOS", _ORIGENES_POR_DEFECTO).split(",")
    if origen.strip()
]

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

# El navegador bloquea las llamadas entre orígenes distintos salvo que el
# servidor las autorice. El Sitio y la API se despliegan como servicios
# separados, así que sin esto el Sitio no puede hablar con la API.
#
# Solo se permiten los métodos y cabeceras que el contrato usa de verdad, en
# lugar de abrir todo «por si acaso»: `X-Firma-Evento` no está en la lista
# porque esa cabecera la envía la pasarela desde su servidor, nunca un
# navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
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
