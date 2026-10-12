"""Dependencias de FastAPI que resuelven quién hace cada petición.

Es un módulo transversal: no pertenece a ningún contexto y solo habla con la
interfaz pública de Cuentas (`usuarios.service` y `usuarios.contracts`), como
exige ADR-0001. Desde la semana 9 la auditoría de modularidad **sí revisa** los
archivos sueltos en `app/`, así que esa regla aquí es comprobable y no una
intención.

### Por qué un token en la cabecera y no una cookie

El sitio es estático y vive en un origen distinto al de la API. Con cookies haría
falta `SameSite=None`, `Secure`, CORS con credenciales y protección contra CSRF;
con un token en `Authorization` no hay envío automático desde otro sitio, así
que el CSRF deja de existir como clase de problema.

El costo es el otro lado de la moneda y hay que decirlo: el token vive en
`sessionStorage` del navegador, así que un fallo de XSS podría leerlo. Hoy el
sitio no renderiza HTML de nadie —todo el texto se inserta con `textContent`—
pero eso es una propiedad que hay que mantener, no una garantía del mecanismo.
Queda anotado en [V-12](../../docs/violaciones.md).
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.usuarios import service as cuentas_service
from app.usuarios.contracts import RolUsuario, UsuarioAutenticado


def _token_de(authorization: str | None) -> str:
    """Extrae el token de `Authorization: Bearer <token>`.

    Devuelve cadena vacía ante cualquier forma inesperada, en vez de lanzar: una
    cabecera malformada es una petición no autenticada, no un error del
    servidor.
    """
    if not authorization:
        return ""
    partes = authorization.split(None, 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return ""
    return partes[1].strip()


def token_de_sesion(authorization: str | None = Header(default=None)) -> str:
    """El token tal cual viaja, para operaciones que actúan sobre la sesión misma.

    Existe porque cerrar sesión no es una operación sobre el usuario sino sobre
    **una** de sus sesiones: alguien que entra desde dos navegadores y sale en
    uno espera seguir dentro en el otro.
    """
    return _token_de(authorization)


def usuario_actual(
    authorization: str | None = Header(default=None),
) -> UsuarioAutenticado:
    """Exige una sesión válida. Responde `401` si no la hay.

    La cabecera `WWW-Authenticate` acompaña al `401` porque la especificación de
    HTTP la exige: sin ella, un cliente que recibe `401` no sabe qué tipo de
    credencial se le está pidiendo.
    """
    usuario = cuentas_service.usuario_de_sesion(_token_de(authorization))

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión no válida o expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def personal_de_establecimiento(
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> UsuarioAutenticado:
    """Exige una sesión de alguien que atiende un mostrador.

    Un administrador **también pasa**: puede operar sobre cualquier
    establecimiento. Lo que no pasa es una sesión válida sin ninguno de los dos
    roles, que hoy no existe pero existiría en cuanto se añada un tercero.
    """
    if usuario.rol not in (RolUsuario.PERSONAL_ESTABLECIMIENTO, RolUsuario.ADMINISTRADOR):
        raise HTTPException(status_code=403, detail="Tu rol no permite esta operación.")
    return usuario


def establecimiento_que_puede_ver(
    usuario: UsuarioAutenticado,
    solicitado: int | None,
) -> int:
    """Resuelve sobre qué establecimiento opera la petición.

    Es la regla de autorización del panel, y está aquí y no en el router para
    que sea una sola y se pueda probar sola:

    - **El personal opera sobre el suyo.** Si pide otro, `403`. No se ignora el
      parámetro en silencio: quien pide los pedidos del establecimiento 3 y
      recibe los del 1 creería estar viendo el 3.
    - **El administrador opera sobre el que indique**, y sobre ninguno por
      defecto, porque no pertenece a ninguno.
    """
    if usuario.rol is RolUsuario.ADMINISTRADOR:
        if solicitado is None:
            raise HTTPException(
                status_code=422,
                detail="Un administrador debe indicar el establecimiento.",
            )
        return solicitado

    # Personal: su establecimiento no es negociable.
    propio = usuario.establecimiento_id
    if solicitado is not None and solicitado != propio:
        raise HTTPException(
            status_code=403,
            detail="Solo podés operar sobre tu propio establecimiento.",
        )
    return propio
