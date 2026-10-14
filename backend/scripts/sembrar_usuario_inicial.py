"""Crea la primera cuenta del panel, y solo la primera.

Lo ejecuta `entrypoint.sh` en cada arranque. No hace nada salvo en un caso: que
la tabla `usuarios` esté **vacía** y el entorno traiga las tres variables.

### Por qué existe

`crear_usuario.py` necesita hablar con PostgreSQL, y en el servidor del
laboratorio eso no se puede desde fuera: la base es un contenedor sin puertos
publicados —a propósito, para que no sea alcanzable desde Internet— y el panel
no da terminal del servidor.

Sin este guion, un despliegue limpio deja un panel sin cuentas y sin forma de
crear ninguna: el sistema arranca perfecto y nadie puede entrar. Y como **no hay
copia de seguridad garantizada** de los volúmenes, «un despliegue limpio» no es
un caso hipotético, es el procedimiento de recuperación.

### Por qué no es una migración

Sembrar la cuenta en SQL exigiría escribir en el repositorio una contraseña o su
derivación. Eso es exactamente [V-11](../../docs/violaciones.md): un valor «de
desarrollo» que nadie trata como secreto porque no lo parece. Aquí la contraseña
viaja por el entorno, su valor vive en el panel, y el repositorio no la ve.

### Por qué solo con la tabla vacía

Para que esto no sea una puerta trasera. Si actuara con la tabla poblada, quien
pudiera escribir una variable de entorno podría crearse una cuenta en un sistema
en marcha, o reponer la contraseña de otro. Limitado al arranque en frío, lo
único que puede hacer es lo que ya puede hacer quien despliega.

No lleva valores por defecto. Sin las variables no hace nada y lo dice: una
cuenta inicial con contraseña conocida sería peor que no tener cuenta.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import base_de_datos  # noqa: E402
from app.usuarios import repository  # noqa: E402
from app.usuarios import service as cuentas_service  # noqa: E402

CORREO = "PIDEUTB_USUARIO_INICIAL_CORREO"
CONTRASENA = "PIDEUTB_USUARIO_INICIAL_CONTRASENA"
ESTABLECIMIENTO = "PIDEUTB_USUARIO_INICIAL_ESTABLECIMIENTO"


def _aviso(evento: str, **extra) -> None:
    """Una línea JSON a stdout, como el resto del sistema.

    Se serializa con `json.dumps` y no interpolando: el primer intento usaba
    `repr`, que escribe las cadenas entre comillas **simples** y produce algo
    que parece JSON y no lo es. El laboratorio recoge estos logs esperando
    JSON, así que habrían llegado como texto suelto.

    **Nunca incluye la contraseña**, ni su longitud. El log del despliegue lo
    lee cualquiera con acceso al panel, y un secreto en un log es un secreto
    publicado.
    """
    print(json.dumps(
        {"level": "INFO", "service": "api", "event": evento, **extra},
        ensure_ascii=False,
    ))


def main() -> int:
    """Siembra si corresponde, y deja el pool cerrado pase lo que pase."""
    try:
        return _sembrar()
    finally:
        # Mismo motivo que en `crear_usuario.py`: sin esto, `psycopg_pool` se
        # queja al apagar el intérprete con cuatro `couldn't stop thread ...`.
        # Aquí sería peor que allí — esas líneas saldrían en el registro de cada
        # despliegue, justo detrás del aviso de que la cuenta se creó, y quien
        # lo lea no sabrá si algo quedó a medias.
        base_de_datos.cerrar_pool()


def _sembrar() -> int:
    correo = os.getenv(CORREO, "").strip()
    contrasena = os.getenv(CONTRASENA, "")
    establecimiento = os.getenv(ESTABLECIMIENTO, "").strip()

    if not correo or not contrasena:
        _aviso("usuario_inicial_omitido", motivo="sin variables")
        return 0

    # La comprobación que convierte esto en un arranque y no en una puerta.
    if repository.hay_usuarios():
        _aviso("usuario_inicial_omitido", motivo="ya hay cuentas")
        return 0

    if not establecimiento.isdigit():
        print(
            f"{ESTABLECIMIENTO} tiene que ser el número de un establecimiento.",
            file=sys.stderr,
        )
        return 2

    try:
        usuario = cuentas_service.crear_usuario(
            correo=correo,
            contrasena=contrasena,
            rol="personal_establecimiento",
            establecimiento_id=int(establecimiento),
        )
    except cuentas_service.ContrasenaDebilError as error:
        # Se falla en vez de crear una cuenta débil. El arranque se detiene y el
        # despliegue queda en rojo, que es visible; una cuenta con contraseña
        # corta en un sistema en marcha no lo es.
        print(str(error), file=sys.stderr)
        return 2
    except cuentas_service.CorreoYaRegistradoError as error:
        print(str(error), file=sys.stderr)
        return 1

    _aviso("usuario_inicial_creado", correo=usuario.correo,
           establecimiento=usuario.establecimiento_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
