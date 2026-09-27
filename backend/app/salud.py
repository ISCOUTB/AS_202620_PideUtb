"""Chequeo de salud con sondas de dependencias.

### El problema que resuelve

Un `/health` que devuelve `{"status": "ok"}` sin comprobar nada solo demuestra
que el proceso de Python está vivo. La plataforma de despliegue lo usa para
decidir si enrutar tráfico, así que un chequeo así **miente por omisión**:
mantiene el servicio en rotación mientras la base de datos está caída y todas
las peticiones reales fallan con 500.

### La regla que se sigue aquí

**No se reporta `ok` sobre nada que no se haya comprobado.** Cada dependencia
aparece en la respuesta únicamente si hay una sonda que la interrogó de verdad,
y cada entrada declara su `tipo`, para que `almacenamiento: memoria` no se
pueda confundir con una base de datos gestionada.

La consecuencia incómoda y deliberada es que hoy la respuesta dice
`tipo: "memoria"`: es la verdad ([V-09](../../docs/violaciones.md)), y un
chequeo honesto que admite una limitación vale más que uno bonito que la tapa.

### Por qué hay un tiempo límite

Una sonda sin `timeout` puede colgarse contra una dependencia que no responde.
El chequeo entonces nunca contesta, la plataforma lo interpreta como caída
*igual*, y además se queda un trabajador ocupado. Con límite, una dependencia
lenta se reporta como caída en un tiempo acotado, que es información, no un
bloqueo.
"""
from __future__ import annotations

import os
import time
from typing import Callable

import httpx

from app.esquemas_comunes import EstadoDependencia
from app.menu import repository as repositorio_catalogo

#: Segundos que se le conceden a una sonda antes de darla por caída.
#:
#: Se elige por debajo del tiempo que la plataforma espera por el chequeo: si
#: la sonda tardara más que ese margen, la plataforma cortaría la conexión y
#: perderíamos el diagnóstico —sabríamos que falló, no por qué.
TIMEOUT_SONDA_S = 3.0

Sonda = Callable[[], EstadoDependencia]


def _sondar_catalogo() -> EstadoDependencia:
    """Comprueba que la capa de datos responde a una consulta real.

    No es un `return True`: ejecuta la misma función que sirve la carta. Si el
    repositorio quedara vacío tras una migración mal aplicada, o lanzara al
    importarse, esta sonda lo detecta.
    """
    inicio = time.perf_counter()
    try:
        items = repositorio_catalogo.buscar_por_establecimiento(1)
    except Exception as error:
        return EstadoDependencia(
            estado="caido",
            tipo="memoria",
            latencia_ms=_ms(inicio),
            detalle=type(error).__name__,
        )

    if not items:
        # Responder sin fallar pero sin datos es el modo de fallo silencioso
        # más peligroso: el sitio mostraría una carta vacía y el usuario
        # concluiría que no hay comida, no que el sistema está roto.
        return EstadoDependencia(
            estado="caido",
            tipo="memoria",
            latencia_ms=_ms(inicio),
            detalle="el catalogo respondio vacio",
        )

    return EstadoDependencia(estado="ok", tipo="memoria", latencia_ms=_ms(inicio))


def _sondar_base_de_datos() -> EstadoDependencia:
    """Pide a la base de datos gestionada que conteste.

    Solo se registra cuando `PIDEUTB_SUPABASE_URL` está configurada. Mientras
    no lo esté, esta dependencia **no aparece** en la respuesta, en vez de
    aparecer como `ok`: el sistema no depende todavía de ella, y anunciarla
    sería describir una arquitectura que no está desplegada.
    """
    url = os.environ["PIDEUTB_SUPABASE_URL"].rstrip("/")
    inicio = time.perf_counter()
    try:
        respuesta = httpx.get(f"{url}/rest/v1/", timeout=TIMEOUT_SONDA_S)
    except httpx.HTTPError as error:
        return EstadoDependencia(
            estado="caido",
            tipo="postgresql",
            latencia_ms=_ms(inicio),
            detalle=type(error).__name__,
        )

    # 401 cuenta como vivo: el servicio contestó y rechazó la sonda por no
    # traer credenciales, que es exactamente lo que debe hacer. Confundir
    # «me rechazó» con «está caído» produce alertas falsas a las 3 de la
    # mañana, y una alerta que miente se termina ignorando.
    if respuesta.status_code >= 500:
        return EstadoDependencia(
            estado="caido",
            tipo="postgresql",
            latencia_ms=_ms(inicio),
            detalle=f"HTTP {respuesta.status_code}",
        )

    return EstadoDependencia(estado="ok", tipo="postgresql", latencia_ms=_ms(inicio))


def _ms(inicio: float) -> float:
    return round((time.perf_counter() - inicio) * 1000, 2)


def sondas_activas() -> dict[str, Sonda]:
    """Sondas que corresponden a la configuración actual del entorno.

    Se calcula en cada llamada y no al importar el módulo para que las pruebas
    puedan activar y desactivar dependencias con variables de entorno sin
    recargar la aplicación entera.
    """
    sondas: dict[str, Sonda] = {"catalogo": _sondar_catalogo}
    if os.getenv("PIDEUTB_SUPABASE_URL"):
        sondas["base_de_datos"] = _sondar_base_de_datos
    return sondas


def revisar() -> tuple[bool, dict[str, EstadoDependencia]]:
    """Ejecuta todas las sondas activas.

    Devuelve `(sano, dependencias)`. El servicio se considera sano solo si
    **ninguna** dependencia está caída: no existe aquí la noción de «caído a
    medias», porque quien consume el chequeo —la plataforma— solo puede tomar
    una decisión binaria, enrutar tráfico o no.
    """
    dependencias = {}
    for nombre, sonda in sondas_activas().items():
        try:
            dependencias[nombre] = sonda()
        except Exception as error:
            # Una sonda que revienta es una sonda que no sabe el estado de su
            # dependencia. Se reporta como caída y no se deja que su
            # excepción tumbe el chequeo completo, que dejaría al resto de
            # dependencias sin diagnosticar.
            dependencias[nombre] = EstadoDependencia(
                estado="caido",
                tipo="desconocido",
                latencia_ms=0.0,
                detalle=f"la sonda fallo: {type(error).__name__}",
            )

    sano = all(dep.estado == "ok" for dep in dependencias.values())
    return sano, dependencias
