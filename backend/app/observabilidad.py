"""Logs estructurados y medición de latencia.

Dos señales mínimas de operación, en un solo archivo porque comparten origen:
cada petición produce **una línea de log** y **una muestra de latencia**.

### Por qué JSON y no texto

Un `print("algo ocurrió")` sirve para leerlo con los ojos y para nada más. Una
línea JSON se puede filtrar, contar y agregar sin escribir un parser: en el
panel de la plataforma se busca por `event` o por `request_id`, y con `jq` se
calcula un percentil desde la terminal.

### Qué NO se registra

Nunca: contraseñas, tokens, firmas (`X-Firma-Evento`), cuerpos de petición
completos ni cabeceras de autorización. Un log es un lugar donde los secretos
sobreviven mucho después de que alguien los rote.

Se registra la **ruta con plantilla** (`/v1/pedidos/{pedido_id}`) y no la ruta
concreta: agrupa las métricas por operación en vez de producir una serie
distinta por cada identificador.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import deque
from statistics import median

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_LOG = logging.getLogger("pideutb")

#: Tamaño de la ventana de latencias que se conserva en memoria.
#:
#: Suficiente para un percentil estable durante un pico de almuerzo (~1000
#: peticiones) sin crecer sin límite. `deque` con `maxlen` descarta la muestra
#: más antigua al llegar una nueva, así que el consumo de memoria es constante.
TAMANO_VENTANA = 1000


class FormatoJSON(logging.Formatter):
    """Convierte cada registro en una línea JSON."""

    def format(self, registro: logging.LogRecord) -> str:
        linea = {
            "timestamp": self.formatTime(registro, "%Y-%m-%dT%H:%M:%S%z"),
            "level": registro.levelname,
            "service": "api",
            "event": registro.getMessage(),
        }

        # Los campos extra viajan en `extra={...}` y se fusionan aquí. Se
        # filtran los atributos internos de logging para no volcar el registro
        # entero en cada línea.
        for clave, valor in registro.__dict__.items():
            if clave not in _ATRIBUTOS_INTERNOS and not clave.startswith("_"):
                linea[clave] = valor

        if registro.exc_info:
            linea["exception"] = self.formatException(registro.exc_info)

        return json.dumps(linea, ensure_ascii=False, default=str)


_ATRIBUTOS_INTERNOS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__)


class Latencias:
    """Ventana deslizante de latencias por operación.

    Vive en memoria del proceso, con la misma limitación que el resto del
    estado ([V-09](../../docs/violaciones.md)): se reinicia con el servicio y no
    se comparte entre réplicas. Es suficiente para responder «¿cómo va el p95
    ahora mismo?», que es lo que pide el escenario, y no pretende sustituir a un
    sistema de métricas.
    """

    def __init__(self) -> None:
        self._muestras: dict[str, deque[float]] = {}

    def registrar(self, operacion: str, ms: float) -> None:
        self._muestras.setdefault(operacion, deque(maxlen=TAMANO_VENTANA)).append(ms)

    def resumen(self) -> dict[str, dict[str, float | int]]:
        return {
            operacion: {
                "muestras": len(muestras),
                "p50_ms": round(median(sorted(muestras)), 2),
                "p95_ms": round(_percentil(sorted(muestras), 95), 2),
                "max_ms": round(max(muestras), 2),
            }
            for operacion, muestras in self._muestras.items()
            if muestras
        }

    def limpiar(self) -> None:
        """Solo para aislar pruebas entre sí."""
        self._muestras.clear()


def _percentil(ordenadas: list[float], p: float) -> float:
    """Mismo método que `scripts/medir_linea_base.py`.

    Se repite en lugar de importarlo porque `app/` no debe depender de
    `scripts/`: uno es el producto y el otro es instrumental de medición.
    """
    indice = min(int(round(p / 100 * len(ordenadas))) - 1, len(ordenadas) - 1)
    return ordenadas[max(indice, 0)]


LATENCIAS = Latencias()


class RegistroDePeticiones(BaseHTTPMiddleware):
    """Registra una línea por petición y alimenta la ventana de latencias."""

    async def dispatch(self, peticion: Request, siguiente):
        # El `request_id` permite seguir una petición por todas sus líneas de
        # log. Si el cliente ya envió uno, se respeta: así la traza no se corta
        # al cruzar de un servicio a otro.
        request_id = peticion.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        inicio = time.perf_counter()

        try:
            respuesta = await siguiente(peticion)
        except Exception:
            duracion = (time.perf_counter() - inicio) * 1000
            _LOG.exception(
                "peticion_fallida",
                extra={
                    "request_id": request_id,
                    "method": peticion.method,
                    "path": _plantilla(peticion),
                    "duration_ms": round(duracion, 2),
                },
            )
            raise

        duracion = (time.perf_counter() - inicio) * 1000
        operacion = f"{peticion.method} {_plantilla(peticion)}"
        LATENCIAS.registrar(operacion, duracion)

        _LOG.info(
            "peticion_atendida",
            extra={
                "request_id": request_id,
                "method": peticion.method,
                "path": _plantilla(peticion),
                "status": respuesta.status_code,
                "duration_ms": round(duracion, 2),
            },
        )

        # Devolver el identificador permite a quien reporta un problema citarlo,
        # y encontrar su petición exacta en el log sin adivinar por la hora.
        respuesta.headers["X-Request-Id"] = request_id
        return respuesta


def _plantilla(peticion: Request) -> str:
    """Ruta con plantilla (`/v1/pedidos/{pedido_id}`), no la concreta.

    Sin esto, cada identificador produciría su propia serie de métricas y el
    percentil por operación sería inútil.
    """
    ruta = peticion.scope.get("route")
    return getattr(ruta, "path", peticion.url.path)


def configurar_logs(nivel: str = "INFO") -> None:
    """Deja el log raíz emitiendo JSON por salida estándar.

    Se escribe a stdout y no a un archivo a propósito: en una plataforma
    gestionada el sistema de archivos es efímero, así que un log en disco
    desaparece en cada despliegue. La plataforma recoge stdout y lo conserva.
    """
    manejador = logging.StreamHandler()
    manejador.setFormatter(FormatoJSON())

    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.addHandler(manejador)
    raiz.setLevel(nivel)

    # Uvicorn trae sus propios manejadores con formato de texto. Se desactivan
    # para que no convivan dos formatos distintos en la misma salida.
    for nombre in ("uvicorn.access", "uvicorn.error"):
        registrador = logging.getLogger(nombre)
        registrador.handlers.clear()
        registrador.propagate = True

    # `httpx` registra en INFO la URL completa de cada llamada saliente. Es la
    # vía más común por la que un token acaba en un log: basta con que alguna
    # vez viaje en la cadena de consulta. Se sube a WARNING para que solo
    # hable cuando algo falle.
    logging.getLogger("httpx").setLevel(logging.WARNING)
