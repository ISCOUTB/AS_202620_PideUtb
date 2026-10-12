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
"""
from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.usuarios import service as cuentas_service  # noqa: E402

LONGITUD_MINIMA = 12


def main() -> int:
    if not os.getenv("PIDEUTB_DATABASE_URL", "").strip():
        print("Falta PIDEUTB_DATABASE_URL.", file=sys.stderr)
        return 2

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

    print(f"Usuario {usuario.id} creado: {usuario.correo} ({usuario.rol.value})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
