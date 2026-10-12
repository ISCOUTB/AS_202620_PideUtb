"""Acceso a datos del contexto Cuentas.

Solo este módulo lee y escribe las tablas de cuentas (`establecimientos`).
Cuentas es el **único escritor** de `Establecimiento` (ADR-0002).

Como en el resto de contextos, hay dos implementaciones tras la misma interfaz:
PostgreSQL cuando `PIDEUTB_DATABASE_URL` está configurada, memoria cuando no.
"""
from datetime import datetime, timedelta, timezone

from app import base_de_datos
from app.usuarios.contracts import RolUsuario
from app.usuarios.models import Establecimiento, Sesion, Usuario

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


# ---------------------------------------------------------------------------
# Usuarios y sesiones
#
# A diferencia de los establecimientos, **no hay implementación en memoria**.
# Es deliberado: una autenticación de juguete que funciona sin base de datos
# invita a desplegar sin ella, y el modo de fallo sería que cualquiera entra.
# Sin `PIDEUTB_DATABASE_URL` estas funciones lanzan, que es lo correcto.
# ---------------------------------------------------------------------------

_COLUMNAS_USUARIO = "id, establecimiento_id, correo, hash_contrasena, rol, activo"


def _usuario_desde_fila(fila) -> Usuario:
    return Usuario(
        id=fila[0],
        establecimiento_id=fila[1],
        correo=fila[2],
        hash_contrasena=fila[3],
        rol=RolUsuario(fila[4]),
        activo=fila[5],
    )


def crear_usuario(
    *,
    correo: str,
    hash_contrasena: str,
    rol: RolUsuario,
    establecimiento_id: int | None,
) -> Usuario:
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO usuarios (establecimiento_id, correo, hash_contrasena, rol) "
            f"VALUES (%s, %s, %s, %s) RETURNING {_COLUMNAS_USUARIO}",
            (establecimiento_id, correo, hash_contrasena, rol.value),
        )
        return _usuario_desde_fila(cur.fetchone())


def buscar_usuario_por_correo(correo: str) -> Usuario | None:
    """Busca por correo, normalizando a minúsculas.

    Sin normalizar, `Ana@utb.edu` y `ana@utb.edu` serían cuentas distintas y
    quien se registrara con una no podría entrar con la otra.
    """
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS_USUARIO} FROM usuarios WHERE lower(correo) = lower(%s)",
            (correo,),
        )
        fila = cur.fetchone()

    return None if fila is None else _usuario_desde_fila(fila)


def abrir_sesion(usuario_id: int, token_hash: str, horas: int) -> Sesion:
    expira = datetime.now(timezone.utc) + timedelta(hours=horas)
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sesiones (token_hash, usuario_id, expira_en) "
            "VALUES (%s, %s, %s) RETURNING token_hash, usuario_id, expira_en",
            (token_hash, usuario_id, expira),
        )
        fila = cur.fetchone()

    return Sesion(token_hash=fila[0], usuario_id=fila[1], expira_en=fila[2])


def buscar_usuario_de_sesion(token_hash: str) -> Usuario | None:
    """Devuelve el usuario de una sesión **vigente y activa**, o `None`.

    Las tres condiciones viajan dentro de la consulta y no en comprobaciones
    posteriores. Con un `if` fuera, olvidar uno de los tres casos —la sesión
    caducada, el usuario desactivado— deja entrar a quien no debe, y es
    justamente el tipo de olvido que no se nota porque todo sigue funcionando.
    """
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT u.id, u.establecimiento_id, u.correo, u.hash_contrasena, u.rol, u.activo "
            "FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id "
            "WHERE s.token_hash = %s AND s.expira_en > now() AND u.activo",
            (token_hash,),
        )
        fila = cur.fetchone()

    return None if fila is None else _usuario_desde_fila(fila)


def cerrar_sesion(token_hash: str) -> bool:
    """Borra la sesión. Devuelve si existía.

    Se borra en vez de marcarse como cerrada: una sesión cerrada no tiene ningún
    uso posterior, y conservarla solo aumenta lo que se pierde si la tabla se
    filtra.
    """
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sesiones WHERE token_hash = %s", (token_hash,))
        return cur.rowcount > 0


def borrar_sesiones_caducadas() -> int:
    """Limpieza. No la llama nadie todavía: sin ella las filas caducadas se
    acumulan, pero ya no sirven para entrar —`buscar_usuario_de_sesion` las
    descarta—, así que es higiene y no seguridad.
    """
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sesiones WHERE expira_en <= now()")
        return cur.rowcount
