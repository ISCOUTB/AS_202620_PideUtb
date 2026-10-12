"""Forma que el contexto Cuentas publica por HTTP.

Debe coincidir con `docs/api/openapi.yaml`; que coincida lo verifica
`tests/test_contrato_api.py`.
"""
from pydantic import BaseModel, Field

from app.usuarios.contracts import UsuarioAutenticado


class IniciarSesionRequest(BaseModel):
    """Credenciales de ingreso.

    `contrasena` no declara longitud máxima por capricho sino por un motivo
    concreto: `scrypt` tarda proporcionalmente a lo que se le da, así que sin
    tope alguien podría enviar un megabyte y ocupar un trabajador del servidor
    durante segundos. El tope convierte eso en un `422` inmediato.

    La mínima **no** se declara aquí: una petición con contraseña corta tiene
    que responder `401` como cualquier otra credencial equivocada. Si devolviera
    `422`, quien prueba sabría que acertó el formato y falló el valor.
    """

    correo: str = Field(min_length=3, max_length=254)
    contrasena: str = Field(min_length=1, max_length=256)


class SesionResponse(BaseModel):
    """La sesión recién abierta.

    `token` se entrega **una sola vez**: lo almacenado es su hash, así que no hay
    forma de volver a consultarlo. Si se pierde, se abre otra sesión.

    Viene acompañado del usuario para que el panel sepa de inmediato qué
    establecimiento mostrar, sin una segunda llamada. Un cliente que tuviera que
    preguntar «¿y quién soy?» tras ingresar gastaría un viaje de red en algo que
    el servidor ya sabía.
    """

    token: str
    usuario: UsuarioAutenticado
