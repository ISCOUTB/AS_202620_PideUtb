"""Conexión a PostgreSQL y el pool que la sostiene.

Este módulo es la razón por la que [ADR-0004](../../docs/adr/0004-plataforma-de-despliegue.md)
eligió un contenedor con proceso persistente sobre una función sin servidor, y
es la parte de esa decisión que **sobrevivió al cambio de plataforma**: el
proveedor lo eligió de nuevo ADR-0008, el argumento del pool no se tocó.

Un proceso que vive entre peticiones **abre las conexiones una vez y las
reutiliza**; una invocación aislada tiene que abrir la suya cada vez. Con un
pico de almuerzo concentrado en dos horas, la segunda opción paga el
establecimiento de conexión justo cuando llega el tráfico.

El límite concreto cambió de sitio. Antes era la capa gratuita de Supabase, que
acotaba las conexiones simultáneas de todo el proyecto; hoy PostgreSQL corre en
un contenedor vecino con **160 MB** (`deploy/compose.lab.yaml`), y cada backend
suyo cuesta memoria de ese presupuesto. El argumento no se debilitó: cambió de
dueño.

### Dos implementaciones, una interfaz

Los `repository.py` de cada contexto llaman a este módulo, pero **siguen
funcionando sin base de datos**. Cuando `PIDEUTB_DATABASE_URL` no está
configurada, el sistema usa el almacenamiento en memoria de siempre.

Eso no es indecisión: es lo que permite que la suite siga corriendo en un
portátil sin PostgreSQL instalado —hoy 228 de las 289 pruebas, y el resto se
omiten diciéndolo— y que el equipo no quede bloqueado por una dependencia de
infraestructura. El riesgo —que las dos implementaciones se
separen— se controla ejecutando **las mismas pruebas contra las dos**
(`tests/test_repositorios.py`).

### Por qué el esquema no está en Terraform

El razonamiento es independiente del proveedor, y conviene conservarlo porque
sobrevivió a dos: un `terraform apply` que gestionara el esquema trataría una
columna eliminada como un recurso a destruir, y borraría datos de producción sin
preguntar. Terraform razona en estado deseado; una migración, en pasos
aplicados.

Las migraciones van en `backend/migraciones/` y se aplican con
`scripts/migrar.py`, que el contenedor ejecuta al arrancar
(`backend/entrypoint.sh`). Desde ADR-0008 la base **vive dentro del
despliegue**, así que no hay proyecto externo que declarar: `infra/` quedó
obsoleta entera y lo dice en su README.
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
#: El techo es bajo a propósito, y el motivo cambió sin que el valor tuviera
#: que cambiar. Antes era la capa gratuita de Supabase, que acotaba las
#: conexiones simultáneas de todo el proyecto. Hoy el límite está más cerca:
#: PostgreSQL corre en un contenedor con **160 MB** y cada conexión es un
#: proceso suyo con su memoria. Un pool ambicioso no le quitaría sitio a un
#: panel ajeno; se lo quitaría a la propia base.
#:
#: Dicho de otro modo: la restricción dejó de ser una cuota de un tercero y
#: pasó a ser el presupuesto de ADR-0008, que es más fácil de comprobar y más
#: difícil de olvidar.
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

    `open=True` conecta en el arranque en lugar de en la primera petición.

    El motivo original era el arranque en frío del proveedor anterior, que ya
    hacía esperar a la primera persona de cada pico; sumarle el establecimiento
    de conexiones la dejaba esperando el doble. Ese arranque en frío desapareció
    con ADR-0008, y la decisión se queda por una razón que no depende de él:
    **el costo se paga en el arranque, que es tiempo que el orquestador ya
    concede** —`start_period: 60s` en `deploy/compose.lab.yaml`— en lugar de
    dentro de la petición de alguien.
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
