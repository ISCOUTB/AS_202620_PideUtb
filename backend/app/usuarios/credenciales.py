"""Derivación de contraseñas y generación de tokens de sesión.

Vive aparte del servicio porque es la pieza que más se mira cuando algo sale
mal, y conviene poder leerla sin atravesar lógica de negocio.

### Por qué scrypt y no sha256

`sha256` está pensado para ser **rápido**, que es exactamente lo contrario de lo
que hace falta aquí: una tarjeta gráfica prueba miles de millones de candidatos
por segundo contra un hash rápido. `scrypt` es un derivador de clave: se le pide
que tarde y que gaste memoria, y ese costo lo paga también quien intenta
adivinar.

Está en la biblioteca estándar desde Python 3.6, así que esto no añade ninguna
dependencia — y no añadirla importa en un proyecto donde la cadena de
suministro ya se audita (`docs/evidencia-s9.md` §3.1).

### Por qué cada contraseña lleva su propia sal

Sin sal, dos usuarios con la misma contraseña producen la misma derivación, y
quien vea la tabla sabe que coinciden. Con sal distinta por usuario, además,
una tabla precalculada no sirve: habría que rehacerla para cada sal.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

#: Parámetros de scrypt. Son los que recomienda la documentación de Python para
#: uso interactivo: cuestan unos 100 ms por derivación en una máquina modesta.
#:
#: Ese costo es el punto. Cien milisegundos no los nota quien inicia sesión una
#: vez, y multiplican por cien mil el trabajo de quien prueba contraseñas en
#: serie. Subirlos endurece el sistema y también el arranque del panel: si
#: alguna vez se tocan, hay que medir las dos cosas.
_N = 2 ** 14
_R = 8
_P = 1
_LONGITUD_CLAVE = 32
_LONGITUD_SAL = 16

#: Bytes de aleatoriedad del token de sesión. 32 bytes son 256 bits: adivinarlo
#: por fuerza bruta no es una amenaza realista, y ese es el único requisito.
_LONGITUD_TOKEN = 32

#: Cuánto dura una sesión. Ocho horas cubre un turno completo sin obligar a
#: reingresar a media jornada, y acota el daño de un token robado a ese turno.
HORAS_DE_SESION = 8


def derivar(contrasena: str, sal: bytes | None = None) -> str:
    """Deriva una contraseña a un texto almacenable.

    El formato incluye la sal y los parámetros, no solo el resultado: sin ellos
    no se podría volver a derivar para comparar, y atarlos a constantes del
    código impediría cambiarlos sin invalidar todas las contraseñas existentes.
    """
    sal = sal or secrets.token_bytes(_LONGITUD_SAL)
    clave = hashlib.scrypt(
        contrasena.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=_LONGITUD_CLAVE
    )
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P,
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(clave).decode("ascii"),
    )


def coincide(contrasena: str, almacenado: str) -> bool:
    """Compara una contraseña con su derivación almacenada.

    Devuelve `False` ante cualquier formato inesperado en vez de lanzar: una
    fila corrupta en la tabla tiene que impedir el ingreso, no tumbar el
    servicio con un error que además revelaría que esa cuenta existe.
    """
    try:
        etiqueta, n, r, p, sal_b64, clave_b64 = almacenado.split("$")
        if etiqueta != "scrypt":
            return False
        esperada = hashlib.scrypt(
            contrasena.encode("utf-8"),
            salt=base64.b64decode(sal_b64),
            n=int(n), r=int(r), p=int(p),
            dklen=len(base64.b64decode(clave_b64)),
        )
    except (ValueError, TypeError):
        return False

    # `compare_digest` y no `==`: una comparación que termina en el primer byte
    # distinto filtra, por su duración, cuántos bytes acertó quien la intenta.
    return hmac.compare_digest(esperada, base64.b64decode(clave_b64))


def nuevo_token() -> tuple[str, str]:
    """Genera un token de sesión y su hash.

    Devuelve `(token, hash)`. **El token se entrega una vez y no se guarda**; lo
    que se almacena es su hash, igual que con las contraseñas. Si la tabla de
    sesiones se filtrara, lo que se lleva quien la lea no sirve para entrar.

    Aquí el hash sí es `sha256` directo y no scrypt, y la diferencia tiene
    motivo: un token de 256 bits aleatorios no se adivina probando candidatos
    —no hay diccionario de tokens— así que encarecer cada intento no protege de
    nada y sí añadiría 100 ms a **cada petición autenticada**.
    """
    token = secrets.token_urlsafe(_LONGITUD_TOKEN)
    return token, hash_de_token(token)


def hash_de_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
