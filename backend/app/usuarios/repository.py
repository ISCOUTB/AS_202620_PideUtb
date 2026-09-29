"""Acceso a datos del contexto Cuentas.

Solo este módulo lee y escribe las tablas de cuentas (`establecimientos`).
Cuentas es el **único escritor** de `Establecimiento` (ADR-0002).

Como en el resto de contextos, hay dos implementaciones tras la misma interfaz:
PostgreSQL cuando `PIDEUTB_DATABASE_URL` está configurada, memoria cuando no.
"""
from app import base_de_datos
from app.usuarios.models import Establecimiento

#: Semilla en memoria. Debe coincidir con `migraciones/002_datos_semilla.sql`,
#: y que coincida lo verifica `tests/test_repositorios.py`.
#:
#: Los cuatro están por un motivo, y tres de ellos son el único caso de prueba
#: de una regla del sistema.
_ESTABLECIMIENTOS_SEED = {
    1: Establecimiento(
        id=1, nombre="Cafetería Central", ubicacion="Bloque A, primer piso",
        horario="L-V 07:00-18:00", activo=True,
    ),
    2: Establecimiento(
        id=2, nombre="Kiosco Bloque D", ubicacion="Bloque D, entrada norte",
        horario="L-V 09:00-16:00", activo=True,
    ),
    3: Establecimiento(
        id=3, nombre="Punto Café", ubicacion="Biblioteca, piso 2",
        horario="cerrado temporalmente", activo=False,
    ),
    # Existe y opera, pero todavía no ha cargado su carta. Es el caso que
    # obliga a distinguir «no existe» (404) de «existe y no tiene nada»
    # (200 con lista vacía): sin él, el frontend no puede saber si mostrar un
    # error o un mensaje de «aún sin productos».
    4: Establecimiento(
        id=4, nombre="Carrito de frutas", ubicacion="Plazoleta central",
        horario="L-V 10:00-15:00", activo=True,
    ),
}

_COLUMNAS = "id, nombre, ubicacion, horario, activo"


def _desde_fila(fila) -> Establecimiento:
    return Establecimiento(
        id=fila[0], nombre=fila[1], ubicacion=fila[2], horario=fila[3], activo=fila[4]
    )


def buscar_establecimiento_por_id(establecimiento_id: int) -> Establecimiento | None:
    if not base_de_datos.hay_base_de_datos():
        return _ESTABLECIMIENTOS_SEED.get(establecimiento_id)

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM establecimientos WHERE id = %s",
            (establecimiento_id,),
        )
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)
