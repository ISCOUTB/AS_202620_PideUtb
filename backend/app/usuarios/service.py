"""Interfaz pública del contexto Cuentas (módulo `usuarios`).

Única puerta de entrada para que `menu` y `pedidos` consulten datos de un
establecimiento. Ningún módulo accede a `usuarios.repository` ni a
`usuarios.models` directamente (ADR-0001, precisado por ADR-0002).
"""
from app.usuarios import credenciales, repository
from app.usuarios.contracts import EstablecimientoPublico, RolUsuario, UsuarioAutenticado


def obtener_establecimiento(establecimiento_id: int) -> EstablecimientoPublico | None:
    """Devuelve los datos publicados del establecimiento, o `None`."""
    establecimiento = repository.buscar_establecimiento_por_id(establecimiento_id)
    if establecimiento is None:
        return None
    return EstablecimientoPublico(
        establecimiento_id=establecimiento.id,
        nombre=establecimiento.nombre,
        activo=establecimiento.activo,
    )


def establecimiento_esta_activo(establecimiento_id: int) -> bool:
    """Indica si el establecimiento existe y está recibiendo pedidos."""
    establecimiento = obtener_establecimiento(establecimiento_id)
    return establecimiento is not None and establecimiento.activo


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

#: Longitud mínima de contraseña.
#:
#: Doce y no ocho porque la longitud es lo único que de verdad encarece un
#: ataque por fuerza bruta: las reglas de «al menos un símbolo» producen
#: contraseñas predecibles —todo el mundo pone el signo al final— y molestan sin
#: proteger.
LONGITUD_MINIMA_CONTRASENA = 12


class CorreoYaRegistradoError(Exception):
    pass


class ContrasenaDebilError(Exception):
    pass


class CredencialesInvalidasError(Exception):
    """Correo desconocido o contraseña incorrecta. **Un solo error para los
    dos casos**, a propósito: distinguirlos permitiría averiguar qué correos
    están registrados probándolos uno a uno."""


def crear_usuario(
    *,
    correo: str,
    contrasena: str,
    rol: str,
    establecimiento_id: int | None,
) -> UsuarioAutenticado:
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        raise ContrasenaDebilError(
            f"La contraseña necesita al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."
        )

    correo = correo.strip().lower()
    if repository.buscar_usuario_por_correo(correo) is not None:
        raise CorreoYaRegistradoError(f"Ya hay una cuenta con {correo}.")

    usuario = repository.crear_usuario(
        correo=correo,
        hash_contrasena=credenciales.derivar(contrasena),
        rol=RolUsuario(rol),
        establecimiento_id=establecimiento_id,
    )
    return _publicar_usuario(usuario)


def autenticar(correo: str, contrasena: str) -> tuple[str, UsuarioAutenticado]:
    """Comprueba las credenciales y abre una sesión.

    Devuelve `(token, usuario)`. **El token se entrega aquí y no se puede volver
    a consultar**: lo que queda almacenado es su hash.
    """
    usuario = repository.buscar_usuario_por_correo(correo.strip().lower())

    # Se deriva igualmente cuando el usuario no existe, contra una derivación
    # de descarte. Sin esto, una cuenta inexistente responde al instante y una
    # existente tarda los ~100 ms de scrypt: esa diferencia, medida desde
    # fuera, revela qué correos están registrados.
    hash_a_comparar = usuario.hash_contrasena if usuario else _HASH_DE_DESCARTE
    coincide = credenciales.coincide(contrasena, hash_a_comparar)

    if usuario is None or not usuario.activo or not coincide:
        raise CredencialesInvalidasError("Correo o contraseña incorrectos.")

    token, token_hash = credenciales.nuevo_token()
    repository.abrir_sesion(usuario.id, token_hash, credenciales.HORAS_DE_SESION)
    return token, _publicar_usuario(usuario)


def usuario_de_sesion(token: str) -> UsuarioAutenticado | None:
    """Quién es el dueño de un token vigente, o `None`."""
    if not token:
        return None
    usuario = repository.buscar_usuario_de_sesion(credenciales.hash_de_token(token))
    return None if usuario is None else _publicar_usuario(usuario)


def cerrar_sesion(token: str) -> bool:
    if not token:
        return False
    return repository.cerrar_sesion(credenciales.hash_de_token(token))


def _publicar_usuario(usuario) -> UsuarioAutenticado:
    return UsuarioAutenticado(
        usuario_id=usuario.id,
        correo=usuario.correo,
        rol=usuario.rol,
        establecimiento_id=usuario.establecimiento_id,
    )


#: Derivación de una contraseña que nadie usa, para gastar el mismo tiempo
#: cuando el correo no existe. Se calcula una vez al importar el módulo.
_HASH_DE_DESCARTE = credenciales.derivar("contrasena-que-nadie-usa-jamas")
