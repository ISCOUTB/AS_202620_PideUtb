"""Punto de entrada de la aplicación.

`version` no es decorativa: es la misma que declara `info.version` en
`docs/api/openapi.yaml`, y `tests/test_contrato_api.py` falla si dejan de
coincidir. Un despliegue que anuncia una versión de contrato distinta de la
que cumple es peor que no anunciar ninguna.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import salud
from app.esquemas_comunes import EstadoServicio, Metricas, ServicioNoDisponible
from app.menu.router import router as menu_router
from app.observabilidad import LATENCIAS, TAMANO_VENTANA, RegistroDePeticiones, configurar_logs
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
    version="1.1.0",
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

# Se añade después de CORS y por eso queda **por fuera**: Starlette envuelve
# cada middleware nuevo alrededor de los anteriores. Así el tiempo medido
# incluye todo lo que tarda la petición de verdad, incluida la comprobación de
# origen, y no solo la parte de la que este servicio se siente responsable.
app.add_middleware(RegistroDePeticiones)

configurar_logs(os.getenv("PIDEUTB_NIVEL_LOG", "INFO"))

app.include_router(menu_router)
app.include_router(pedidos_router)
app.include_router(pagos_router)
# app.include_router(usuarios_router)   # pendiente — autenticación y roles


@app.get(
    "/health",
    tags=["operacion"],
    response_model=EstadoServicio,
    summary="Comprueba que el servicio y sus dependencias responden.",
    responses={503: {"model": ServicioNoDisponible, "description": "Alguna dependencia no responde."}},
)
def health() -> EstadoServicio | JSONResponse:
    """Sonda de disponibilidad.

    Queda **fuera de `/v1`** a propósito: es una sonda para la plataforma de
    despliegue, no parte de la superficie de negocio, y por eso no arrastra la
    promesa de compatibilidad de la API
    (`docs/api/politica-versionado.md` §1).

    Devuelve `503` cuando alguna dependencia sondeada no responde. El código
    importa más que el cuerpo: la plataforma decide si enruta tráfico leyendo
    el estado HTTP, y un `200` con `{"estado": "mal"}` dentro la dejaría
    mandando usuarios a un servicio roto.
    """
    sano, dependencias = salud.revisar()

    if not sano:
        # Se construye la respuesta a mano porque `response_model` fija el
        # esquema del 200. Devolver el 503 con su propio esquema es lo que
        # mantiene `status` como `enum` cerrado en cada código y evita la
        # regla I-8.
        return JSONResponse(
            status_code=503,
            content=ServicioNoDisponible(status="no_disponible", dependencias=dependencias).model_dump(),
        )

    return EstadoServicio(status="ok", dependencias=dependencias)


@app.get(
    "/metricas",
    tags=["operacion"],
    response_model=Metricas,
    summary="Latencias observadas por operación.",
)
def metricas() -> Metricas:
    """Percentiles de latencia de las últimas peticiones atendidas.

    Existe para poder responder con un número, y no con una impresión, sobre el
    escenario **ESC-02**: *el proceso completo de pedir toma menos de 2 minutos
    en el 90 % de los intentos*.

    La métrica no mide ESC-02 entera, y decir lo contrario sería exagerar lo que
    prueba: esos 120 segundos incluyen el tiempo que una persona tarda en elegir
    qué comer, que no ocurre en el servidor. Mide **la parte del presupuesto que
    el servidor sí controla**, en `p95_ms` de `POST /v1/pedidos`. Sirve para
    distinguir un escenario incumplido por lentitud del backend de uno
    incumplido por el arranque en frío o por el usuario.

    Es deliberadamente modesto: mide **este** proceso, en una ventana de las
    últimas peticiones, y se reinicia con el servicio. No sustituye a un
    sistema de métricas; sustituye a no tener ninguno.
    """
    return Metricas(
        ventana_maxima=TAMANO_VENTANA,
        operaciones=LATENCIAS.resumen(),
    )
