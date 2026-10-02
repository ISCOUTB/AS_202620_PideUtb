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

import time
from typing import Callable

from app import base_de_datos
from app.esquemas_comunes import EstadoDependencia
from app.menu import service as catalogo_service

#: El límite de tiempo de la sonda de base de datos no se declara aquí: lo pone
#: el pool con `base_de_datos.TIMEOUT_POOL_S`. Tener dos habría permitido que se
#: separaran, y entonces la sonda podría rendirse antes que la aplicación —
#: reportando «caído» un servicio que atiende— o después, perdiendo el
#: diagnóstico porque la plataforma ya cortó el chequeo.

Sonda = Callable[[], EstadoDependencia]


def _tipo_del_almacenamiento() -> str:
    """Qué hay de verdad detrás del catálogo.

    El chequeo declara lo que hay en vez de reportar `ok` sobre lo que no
    comprobó. Mientras el sistema corrió en memoria, esta función devolvía
    `memoria` y eso era la verdad incómoda; ahora devuelve `postgresql`
    cuando lo es, y sigue diciendo `memoria` si alguien despliega sin
    configurar la base de datos.
    """
    return "postgresql" if base_de_datos.hay_base_de_datos() else "memoria"


def _sondar_catalogo() -> EstadoDependencia:
    """Comprueba que la capa de datos responde a una consulta real.

    No es un `return True`: ejecuta la misma función que sirve la carta. Si el
    almacenamiento quedara vacío tras una migración mal aplicada, o lanzara al
    importarse, esta sonda lo detecta.

    Llama al **servicio** de Catálogo, no a su repositorio. La primera versión
    de este archivo —generada con IA en la semana 8— importaba
    `app.menu.repository`, saltándose la interfaz pública del contexto y
    violando ADR-0001. La auditoría automática no lo detectó porque solo
    revisaba archivos dentro de `app/<contexto>/`, y este vive suelto en
    `app/`. Ver `docs/evidencia-s9.md` §2.
    """
    inicio = time.perf_counter()
    try:
        items = catalogo_service.listar_items_de_establecimiento(1)
    except Exception as error:
        return EstadoDependencia(
            estado="caido",
            tipo=_tipo_del_almacenamiento(),
            latencia_ms=_ms(inicio),
            detalle=type(error).__name__,
        )

    if not items:
        # Responder sin fallar pero sin datos es el modo de fallo silencioso
        # más peligroso: el sitio mostraría una carta vacía y el usuario
        # concluiría que no hay comida, no que el sistema está roto.
        return EstadoDependencia(
            estado="caido",
            tipo=_tipo_del_almacenamiento(),
            latencia_ms=_ms(inicio),
            detalle="el catalogo respondio vacio",
        )

    return EstadoDependencia(
        estado="ok", tipo=_tipo_del_almacenamiento(), latencia_ms=_ms(inicio)
    )


def _sondar_base_de_datos() -> EstadoDependencia:
    """Pide a PostgreSQL que conteste, por la misma vía que usa la aplicación.

    Es un `SELECT 1` a través del **pool**, no una conexión nueva. La diferencia
    importa: una sonda que abriera su propia conexión diría que la base de datos
    está viva mientras el pool está agotado y todas las peticiones reales
    fallan. Comprobaría el servicio equivocado.

    Solo se registra cuando `PIDEUTB_DATABASE_URL` está configurada. Mientras no
    lo esté, esta dependencia **no aparece** en la respuesta en vez de aparecer
    como `ok`: el sistema no depende de ella, y anunciarla sería describir una
    arquitectura que no está desplegada.
    """
    inicio = time.perf_counter()
    try:
        with base_de_datos.conexion() as conexion, conexion.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as error:
        return EstadoDependencia(
            estado="caido",
            tipo="postgresql",
            latencia_ms=_ms(inicio),
            # Solo el tipo de la excepción, nunca su mensaje: psycopg incluye la
            # cadena de conexión en algunos errores, y ahí viaja la contraseña.
            detalle=type(error).__name__,
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
    if base_de_datos.hay_base_de_datos():
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
