"""Conexión a PostgreSQL y el pool que la sostiene.

Este módulo es la razón por la que [ADR-0004](../../docs/adr/0004-plataforma-de-despliegue.md)
eligió un contenedor con proceso persistente sobre una función sin servidor. El
argumento decisivo era el pool: un proceso que vive entre peticiones **abre las
conexiones una vez y las reutiliza**, mientras que una invocación aislada tiene
que abrir la suya cada vez. Con la capa gratuita de Supabase, que limita las
conexiones simultáneas, y con un pico de almuerzo concentrado en dos horas, la
segunda opción agota el límite justo cuando llega el tráfico.

### Dos implementaciones, una interfaz

Los `repository.py` de cada contexto llaman a este módulo, pero **siguen
funcionando sin base de datos**. Cuando `PIDEUTB_DATABASE_URL` no está
configurada, el sistema usa el almacenamiento en memoria de siempre.

Eso no es indecisión: es lo que permite que las 146 pruebas sigan corriendo en
un portátil sin PostgreSQL instalado, y que el equipo no quede bloqueado por una
dependencia de infraestructura. El riesgo —que las dos implementaciones se
separen— se controla ejecutando **las mismas pruebas contra las dos**
(`tests/test_repositorios.py`).

### Por qué el esquema no está en Terraform

`infra/supabase.tf` crea el proyecto, no sus tablas. Un `terraform apply` que
gestionara el esquema trataría una columna eliminada como un recurso a destruir,
y borraría datos de producción sin preguntar. Las migraciones van en
`backend/migraciones/` y se aplican con `scripts/migrar.py`.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

_LOG = logging.getLogger("pideutb")

#: Cadena de conexión. Ausente = almacenamiento en memoria.
#:
#: Llega por variable de entorno y **nunca** se escribe en el repositorio:
#: contiene la contraseña de la base de datos. Ver `infra/README.md`.
URL_BASE_DE_DATOS = os.getenv("PIDEUTB_DATABASE_URL", "").strip()

#: Conexiones que el pool mantiene abiertas y su techo.
#:
#: El techo es bajo a propósito. La capa gratuita de Supabase concede pocas
#: conexiones simultáneas para **todo** el proyecto, y un pool ambicioso en un
#: único servicio las acapararía: el resto de herramientas —el panel de
#: Supabase, una migración, una segunda instancia— se quedarían fuera. Con 512
#: MB de memoria tampoco hay margen para más.
POOL_MINIMO = int(os.getenv("PIDEUTB_POOL_MINIMO", "1"))
POOL_MAXIMO = int(os.getenv("PIDEUTB_POOL_MAXIMO", "5"))

#: Segundos que una petición espera por una conexión libre antes de rendirse.
#:
#: Sin tope, un pico de tráfico encola peticiones que el usuario ya abandonó, y
#: el servicio sigue trabajando para nadie mientras rechaza a quien acaba de
#: llegar. Fallar rápido es información; esperar indefinidamente no.
TIMEOUT_POOL_S = float(os.getenv("PIDEUTB_TIMEOUT_POOL", "5"))

_pool = None


def hay_base_de_datos() -> bool:
    """Si el sistema está configurado contra PostgreSQL.

    Es la única pregunta que los repositorios hacen para elegir implementación.
    Se consulta en cada llamada y no se guarda en una constante de módulo para
    que las pruebas puedan activarla y desactivarla sin recargar la aplicación.
    """
    return bool(os.getenv("PIDEUTB_DATABASE_URL", "").strip())


def abrir_pool() -> None:
    """Crea el pool. Se llama una vez, al arrancar el proceso.

    `open=True` conecta en el arranque en lugar de en la primera petición. Con
    un plan que duerme el servicio, la alternativa sería pagar el coste de
    establecer la conexión dentro de la primera petición de cada pico —la misma
    que ya sufre el arranque en frío—, sumando dos esperas para el mismo
    usuario.
    """
    global _pool
    if _pool is not None or not hay_base_de_datos():
        return

    from psycopg_pool import ConnectionPool

    _pool = ConnectionPool(
        conninfo=os.environ["PIDEUTB_DATABASE_URL"],
        min_size=POOL_MINIMO,
        max_size=POOL_MAXIMO,
        timeout=TIMEOUT_POOL_S,
        open=True,
        # Sin esto, una conexión que el servidor cerró por inactividad —cosa
        # que pasa a diario cuando el servicio duerme— se entregaría rota a la
        # siguiente petición, que fallaría sin motivo aparente.
        check=_comprobar_conexion,
    )
    _LOG.info("pool_abierto", extra={"min": POOL_MINIMO, "max": POOL_MAXIMO})


def _comprobar_conexion(conexion) -> None:
    from psycopg_pool import ConnectionPool

    ConnectionPool.check_connection(conexion)


def cerrar_pool() -> None:
    """Cierra el pool al apagar el proceso, para no dejar conexiones colgando."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def conexion() -> Iterator:
    """Presta una conexión del pool y la devuelve al terminar.

    Cada bloque `with` es **una transacción**: psycopg hace `commit` al salir
    sin excepción y `rollback` si la hubo. Es lo que garantiza que una operación
    a medias no quede escrita —por ejemplo, un pago confirmado sin su código de
    canje generado.
    """
    if _pool is None:
        abrir_pool()
    if _pool is None:
        raise RuntimeError(
            "No hay base de datos configurada. Definí PIDEUTB_DATABASE_URL o "
            "usá el almacenamiento en memoria."
        )

    with _pool.connection() as conn:
        yield conn


def estado_del_pool() -> dict:
    """Cifras del pool, para la sonda de salud.

    Se exponen porque el agotamiento del pool es **el modo de fallo que ADR-0004
    identificó como decisivo**, y hasta ahora solo se podía razonar sobre él.
    Con estos números se puede observar.
    """
    if _pool is None:
        return {"abierto": False}

    estadisticas = _pool.get_stats()
    return {
        "abierto": True,
        "tamano": estadisticas.get("pool_size", 0),
        "disponibles": estadisticas.get("pool_available", 0),
        # Peticiones que tuvieron que esperar por una conexión libre. Si este
        # número crece, el pool se está quedando corto para el tráfico real.
        "esperas": estadisticas.get("requests_waiting", 0),
    }
