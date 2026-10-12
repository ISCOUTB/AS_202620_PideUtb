"""Crea un usuario del panel. La contraseña se pide, nunca se pasa por argumento.

    python scripts/crear_usuario.py

### Por qué no hay usuarios en una migración

Sembrarlos exigiría poner una contraseña —o su derivación— en el repositorio.
Eso es exactamente [V-11](../../docs/violaciones.md): un valor «de desarrollo»
que nadie trata como secreto porque no lo parece, y que acaba vivo en
producción. La lección de la semana 9 fue justamente esa, así que no se repite.

### Por qué se pide y no se pasa por argumento

Lo que va en la línea de comandos queda en el historial del shell y en la lista
de procesos de la máquina. `getpass` además no hace eco, así que tampoco queda
en la pantalla de quien esté mirando.

### Por qué cierra el pool a mano

`usuarios.repository` habla por el pool de `app.base_de_datos`, que levanta hilos
en segundo plano. Un guion que termina sin cerrarlo deja que `psycopg_pool` se
queje al apagar el intérprete con cuatro líneas de `couldn't stop thread ...`.

No rompe nada —la cuenta ya está escrita y confirmada— y precisamente por eso
importa: aparece **después** del mensaje de éxito, y quien acaba de tocar la base
de datos de producción lee «no pude parar» y se pregunta si algo quedó a medias.
Un mensaje alarmante tras una operación correcta enseña a ignorar los mensajes.
"""
from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import base_de_datos  # noqa: E402
from app.usuarios import service as cuentas_service  # noqa: E402

LONGITUD_MINIMA = 12


def main() -> int:
    """Pide los datos, crea la cuenta y deja el pool cerrado al salir."""
    if not os.getenv("PIDEUTB_DATABASE_URL", "").strip():
        print("Falta PIDEUTB_DATABASE_URL.", file=sys.stderr)
        return 2

    try:
        return _crear()
    finally:
        # En `finally` y no al final del camino feliz: si algo falla a mitad,
        # los hilos del pool quedarían igualmente colgando y el error de verdad
        # se perdería entre las quejas del apagado.
        base_de_datos.cerrar_pool()


def _crear() -> int:
    correo = input("Correo: ").strip()
    if "@" not in correo:
        print("Eso no parece un correo.", file=sys.stderr)
        return 2

    rol = input("Rol [personal_establecimiento / administrador]: ").strip()
    if rol not in ("personal_establecimiento", "administrador"):
        print("Rol desconocido.", file=sys.stderr)
        return 2

    establecimiento_id: int | None = None
    if rol == "personal_establecimiento":
        bruto = input("Establecimiento (id): ").strip()
        if not bruto.isdigit():
            print("El establecimiento tiene que ser un número.", file=sys.stderr)
            return 2
        establecimiento_id = int(bruto)

    contrasena = getpass.getpass("Contraseña: ")
    if len(contrasena) < LONGITUD_MINIMA:
        # El mínimo se comprueba aquí y también en el servicio. Aquí es
        # amabilidad —avisar antes de pedir la confirmación—; allí es la regla.
        print(f"Mínimo {LONGITUD_MINIMA} caracteres.", file=sys.stderr)
        return 2
    if contrasena != getpass.getpass("Repetila: "):
        print("No coinciden.", file=sys.stderr)
        return 2

    try:
        usuario = cuentas_service.crear_usuario(
            correo=correo,
            contrasena=contrasena,
            rol=rol,
            establecimiento_id=establecimiento_id,
        )
    except cuentas_service.CorreoYaRegistradoError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Usuario {usuario.usuario_id} creado: {usuario.correo} ({usuario.rol.value})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
