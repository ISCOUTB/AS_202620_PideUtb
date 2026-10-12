"""Entidades internas del contexto Cuentas.

No cruzan la frontera del contexto: otros módulos piden los datos a
`usuarios.service`, que responde con los tipos de `usuarios.contracts`.
"""
from datetime import datetime

from pydantic import BaseModel

from app.usuarios.contracts import RolUsuario


class Establecimiento(BaseModel):
    """Cuenta de tipo establecimiento: un punto de venta del campus.

    El contexto Cuentas es su **único escritor** (ADR-0002). `menu` y
    `pedidos` guardan solo `establecimiento_id` como referencia y nunca
    duplican estos campos.
    """

    id: int
    nombre: str
    ubicacion: str
    horario: str
    activo: bool = True


class Usuario(BaseModel):
    """Cuenta con credenciales. Interna: nunca cruza la frontera del contexto.

    `hash_contrasena` es la razón de que esta clase no salga de aquí. Hacia
    fuera viaja `UsuarioAutenticado`, que no lo lleva.
    """

    id: int
    establecimiento_id: int | None
    correo: str
    hash_contrasena: str
    rol: RolUsuario
    activo: bool = True


class Sesion(BaseModel):
    """Una sesión abierta.

    Guarda el **hash** del token, no el token: si esta tabla se filtrara, lo que
    se lleva quien la lea no sirve para entrar.
    """

    token_hash: str
    usuario_id: int
    expira_en: datetime
