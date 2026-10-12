"""Lenguaje publicado del contexto Cuentas.

Único tipo del contexto que puede cruzar la frontera. Separarlo del
modelo interno permite que las cuentas crezcan (credenciales, roles,
autenticación) sin arrastrar a `menu` ni a `pedidos`.
"""
from enum import Enum

from pydantic import BaseModel


class EstablecimientoPublico(BaseModel):
    """Lo que otros contextos necesitan saber de un establecimiento."""

    establecimiento_id: int
    nombre: str
    activo: bool


class RolUsuario(str, Enum):
    """Conjunto cerrado de roles. Debe coincidir con el tipo `rol_usuario` de
    `migraciones/003_autenticacion.sql`, y que coincida lo verifica
    `tests/test_autenticacion.py`.

    Dos y solo dos. Un rol mal escrito en texto libre no sería un error sino un
    usuario sin permisos, que es un fallo mucho más difícil de ver.
    """

    PERSONAL_ESTABLECIMIENTO = "personal_establecimiento"
    ADMINISTRADOR = "administrador"


class UsuarioAutenticado(BaseModel):
    """Quién está haciendo la petición.

    Es lo único que Cuentas publica sobre una sesión. **No lleva el token ni la
    derivación de la contraseña**: ningún otro contexto los necesita, y lo que
    no se publica no se puede filtrar por descuido en un log o en una respuesta.

    `establecimiento_id` es nulo para un administrador, que no pertenece a
    ninguno. Quien lo consuma tiene que decidir qué hacer con ese caso, y que
    sea nulo y no cero lo obliga a mirarlo.
    """

    usuario_id: int
    correo: str
    rol: RolUsuario
    establecimiento_id: int | None
