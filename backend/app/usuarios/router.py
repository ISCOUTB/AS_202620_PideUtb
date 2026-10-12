"""Frontera HTTP del contexto Cuentas: abrir y cerrar sesión.

El router traduce excepciones de dominio a códigos HTTP (arc42 §8.4); el
servicio no conoce el protocolo.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.autenticacion import token_de_sesion, usuario_actual
from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.usuarios import service as cuentas_service
from app.usuarios.contracts import UsuarioAutenticado
from app.usuarios.esquemas_api import IniciarSesionRequest, SesionResponse

router = APIRouter(prefix="/v1/sesiones", tags=["sesiones"])


@router.post(
    "",
    status_code=201,
    response_model=SesionResponse,
    responses={401: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Abre una sesión.",
)
def iniciar_sesion(datos: IniciarSesionRequest) -> SesionResponse:
    """Comprueba las credenciales y devuelve el token.

    **El token se entrega una vez.** Lo que queda almacenado es su hash, así que
    no hay forma de volver a consultarlo: si se pierde, se abre otra sesión.

    Responde `401` tanto si el correo no existe como si la contraseña es
    incorrecta, con el mismo mensaje. Distinguirlos permitiría averiguar qué
    correos están registrados probándolos uno a uno.
    """
    try:
        token, usuario = cuentas_service.autenticar(datos.correo, datos.contrasena)
    except cuentas_service.CredencialesInvalidasError as e:
        raise HTTPException(
            status_code=401, detail=str(e), headers={"WWW-Authenticate": "Bearer"}
        )

    return SesionResponse(token=token, usuario=usuario)


@router.delete(
    "",
    status_code=204,
    responses={401: {"model": ErrorDeNegocio}},
    summary="Cierra la sesión actual.",
)
def cerrar_sesion(
    _: UsuarioAutenticado = Depends(usuario_actual),
    token: str = Depends(token_de_sesion),
) -> None:
    """Borra **la** sesión con la que se llama, no todas las del usuario.

    Alguien que entra desde dos navegadores y sale en uno espera seguir dentro
    en el otro. Por eso se borra por el token presentado y no por el usuario.

    Depende también de `usuario_actual` para exigir que la sesión sea válida: sin
    eso, cualquiera podría mandar cadenas al azar y el endpoint respondería `204`
    igualmente, que es ruido inútil en los logs.
    """
    cuentas_service.cerrar_sesion(token)
