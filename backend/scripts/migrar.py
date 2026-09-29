"""Aplica las migraciones SQL pendientes.

    python scripts/migrar.py                 # aplica lo que falte
    python scripts/migrar.py --estado        # solo informa, no escribe

Lee `PIDEUTB_DATABASE_URL` del entorno y **no acepta la cadena por argumento**:
lo que se pasa por línea de comandos queda en el historial del shell y en la
lista de procesos de la máquina, y esa cadena lleva la contraseña dentro.

### Por qué esto y no Terraform

`infra/supabase.tf` crea el proyecto; sus tablas no. Terraform razona en
términos de estado deseado, así que una columna borrada del `.tf` es un recurso
que hay que destruir — y lo destruiría, con los datos dentro, sin preguntar. Las
migraciones son la herramienta correcta porque razonan en términos de pasos
aplicados, no de estado final.

### Por qué cada migración se registra

Sin un registro, «aplicar lo que falte» no se puede saber, y la alternativa es
reaplicarlo todo confiando en que cada archivo sea idempotente. Lo son hoy, pero
esa es una propiedad que se rompe sola en cuanto alguien añada un `ALTER TABLE`.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

MIGRACIONES = Path(__file__).resolve().parent.parent / "migraciones"

REGISTRO = """
CREATE TABLE IF NOT EXISTS migraciones_aplicadas (
    nombre      text PRIMARY KEY,
    huella      text NOT NULL,
    aplicada_en timestamptz NOT NULL DEFAULT now()
);
"""


def _huella(sql: str) -> str:
    """Identifica el contenido de la migración, no solo su nombre.

    Sirve para detectar que alguien editó un archivo ya aplicado. Ese cambio no
    se ejecutaría nunca —el registro lo da por hecho— y la base de datos
    quedaría distinta de lo que el repositorio dice que es, sin que nadie se
    entere.
    """
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _pendientes(conexion) -> list[Path]:
    archivos = sorted(MIGRACIONES.glob("*.sql"))
    with conexion.cursor() as cur:
        cur.execute(REGISTRO)
        cur.execute("SELECT nombre, huella FROM migraciones_aplicadas")
        aplicadas = dict(cur.fetchall())

    pendientes = []
    for archivo in archivos:
        sql = archivo.read_text(encoding="utf-8")
        anterior = aplicadas.get(archivo.name)
        if anterior is None:
            pendientes.append(archivo)
        elif anterior != _huella(sql):
            raise SystemExit(
                f"ERROR: '{archivo.name}' ya se aplicó pero su contenido cambió.\n"
                "Una migración aplicada no se edita: el cambio no se ejecutaría "
                "nunca y la base de datos quedaría distinta de lo que dice el "
                "repositorio. Creá una migración nueva."
            )
    return pendientes


def main() -> int:
    url = os.getenv("PIDEUTB_DATABASE_URL", "").strip()
    if not url:
        print("Falta PIDEUTB_DATABASE_URL. Exportala antes de ejecutar.", file=sys.stderr)
        return 2

    import psycopg

    solo_informar = "--estado" in sys.argv

    with psycopg.connect(url) as conexion:
        pendientes = _pendientes(conexion)

        if not pendientes:
            print("Todo aplicado. Nada que hacer.")
            return 0

        print(f"Pendientes: {len(pendientes)}")
        for archivo in pendientes:
            print(f"  - {archivo.name}")

        if solo_informar:
            return 0

        for archivo in pendientes:
            sql = archivo.read_text(encoding="utf-8")
            print(f"Aplicando {archivo.name} ...", end=" ", flush=True)
            with conexion.cursor() as cur:
                # Cada archivo trae su propio BEGIN/COMMIT, así que se ejecuta
                # tal cual: si falla a la mitad, no queda aplicado a medias.
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO migraciones_aplicadas (nombre, huella) VALUES (%s, %s)",
                    (archivo.name, _huella(sql)),
                )
            conexion.commit()
            print("ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
