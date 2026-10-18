"""Verifica que las citas de `docs/evidencia-s7.md` siguen siendo ciertas.

Ese documento cita archivos y números de línea concretos para que la evidencia
de la entrega se pueda comprobar sin abrir medio repositorio. El problema de
citar por número de línea es obvio: **caduca en cuanto alguien inserta una línea
más arriba**, y una cita caducada es peor que no citar, porque afirma algo falso
con apariencia de precisión.

Esta prueba convierte el documento en algo verificable. Si un `router` se
reordena o el workflow cambia, la construcción falla y obliga a actualizar la
cita en lugar de dejar que envejezca en silencio.

Es la misma idea que `test_modularidad.py` aplicada a la documentación: una
regla que solo vive en un archivo de texto no es una regla, es una intención.
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DOSSIER = RAIZ / "docs" / "evidencia-s7.md"

#: (archivo, línea 1-based, fragmento que esa línea debe contener)
#:
#: Cada entrada corresponde a una cita del dossier. Al cambiar una, hay que
#: cambiar las dos: la del código y la del documento.
CITAS = [
    # §1 — Correspondencia contrato ↔ código: prefijos de los routers
    ("backend/app/main.py", 120, '"/health"'),
    ("backend/app/main.py", 161, '"/metricas"'),
    ("backend/app/menu/router.py", 20, 'prefix="/v1/menu"'),
    ("backend/app/menu/router.py", 24, '"/items/{item_id}"'),
    ("backend/app/menu/router.py", 36, '"/establecimientos/{establecimiento_id}/items"'),
    ("backend/app/pedidos/router.py", 23, 'prefix="/v1/pedidos"'),
    ("backend/app/pedidos/router.py", 46, '"/{pedido_id}"'),
    ("backend/app/pedidos/router.py", 96, '"/{pedido_id}/estado"'),
    ("backend/app/usuarios/router.py", 16, 'prefix="/v1/sesiones"'),
    ("backend/app/pagos/router.py", 20, 'prefix="/v1/pagos"'),
    ("backend/app/pagos/router.py", 24, '"/intentos"'),
    ("backend/app/pagos/router.py", 41, '"/eventos"'),

    # §1 — Los paths del contrato
    ("docs/api/openapi.yaml", 85, "/health:"),
    ("docs/api/openapi.yaml", 144, "/v1/menu/items/{item_id}:"),
    ("docs/api/openapi.yaml", 168, "/v1/menu/establecimientos/{establecimiento_id}/items:"),
    ("docs/api/openapi.yaml", 202, "/v1/sesiones:"),
    ("docs/api/openapi.yaml", 262, "/v1/pedidos:"),
    ("docs/api/openapi.yaml", 354, "/v1/pedidos/{pedido_id}/estado:"),
    ("docs/api/openapi.yaml", 438, "/v1/pedidos/{pedido_id}:"),
    ("docs/api/openapi.yaml", 462, "/v1/pagos/intentos:"),
    ("docs/api/openapi.yaml", 495, "/v1/pagos/eventos:"),

    # §2 — El pipeline ejecuta la prueba de contrato
    (".github/workflows/ci.yml", 109, "Ejecutar pruebas"),
    (".github/workflows/ci.yml", 113, "pytest -v --junitxml"),
    (".github/workflows/ci.yml", 185, "Validar la forma de los contratos (Spectral)"),
    (".github/workflows/ci.yml", 187, "./node_modules/.bin/spectral lint"),
    (".github/workflows/ci.yml", 203, "Resolver la línea base del contrato"),
    (".github/workflows/ci.yml", 215, "Detectar cambios incompatibles (oasdiff)"),
    (".github/workflows/ci.yml", 217, "tufin/oasdiff breaking"),
    (".github/workflows/ci.yml", 220, "--fail-on ERR"),

    # §7 — SonarCloud en el pipeline
    (".github/workflows/ci.yml", 274, "Medir cobertura"),
    (".github/workflows/ci.yml", 277, "pytest --cov=app"),
    (".github/workflows/ci.yml", 282, "Analizar con SonarCloud"),
    (".github/workflows/ci.yml", 284, "sonarqube-scan-action@ba9859ea"),
    (".github/workflows/ci.yml", 291, "Esperar el veredicto del Quality Gate"),
    (".github/workflows/ci.yml", 293, "sonarqube-quality-gate-action@7a5fffe8"),

    # §5 — C4 nivel 2: cada flecha con protocolo, formato y modo
    ("docs/c4/nivel2-contenedores.md", 31, "HTTPS · JSON (REST) · síncrono"),
    ("docs/c4/nivel2-contenedores.md", 32, "PostgreSQL sobre un pool reutilizado · síncrono · ~1 ms"),
    ("docs/c4/nivel2-contenedores.md", 33, "HTTPS · JSON · síncrono"),
    ("docs/c4/nivel2-contenedores.md", 34, "HTTPS · JSON + HMAC · ASÍNCRONO"),

    # §4 — arc42 sección 6
    ("docs/arc42/arc42.md", 453, "## 6. Vista de tiempo de ejecución"),
    ("docs/arc42/arc42.md", 468, "### 6.1 Resumen de los flujos"),
    ("docs/arc42/arc42.md", 489, "### 6.2 Crear un pedido"),
    ("docs/arc42/arc42.md", 554, "### 6.3 Pagar un pedido"),
    ("docs/arc42/arc42.md", 636, "### 6.4 Consultar el estado"),
    ("docs/arc42/arc42.md", 669, "### 6.5 Modos de fallo"),
    ("docs/arc42/arc42.md", 837, "### 6.6 Deuda conocida"),
]


@pytest.mark.parametrize(
    "archivo, linea, fragmento", CITAS, ids=[f"{a}:{n}" for a, n, _ in CITAS]
)
def test_la_cita_del_dossier_apunta_a_lo_que_dice(archivo, linea, fragmento):
    lineas = (RAIZ / archivo).read_text(encoding="utf-8").splitlines()

    assert linea <= len(lineas), (
        f"`docs/evidencia-s7.md` cita {archivo}:{linea}, pero el archivo tiene "
        f"{len(lineas)} líneas. Actualizá la cita."
    )

    real = lineas[linea - 1]
    assert fragmento in real, (
        f"La cita {archivo}:{linea} de `docs/evidencia-s7.md` ya no es cierta.\n"
        f"  esperaba contener: {fragmento}\n"
        f"  la línea dice    : {real.strip()}\n"
        "Una cita caducada afirma algo falso con apariencia de precisión: "
        "corregí el número de línea en el dossier y en la lista de esta prueba."
    )


def test_el_dossier_existe_y_cabe_entero(sin_usar=None):
    """El dossier existe para ser leído entero por una revisión automática.

    `docs/arc42/arc42.md` supera las mil líneas y se trunca en cualquier lectura
    con límite —fue exactamente lo que ocurrió en la revisión anterior—. Este
    documento tiene que quedarse pequeño para no heredar el mismo problema.
    """
    assert DOSSIER.exists(), "Falta docs/evidencia-s7.md"

    tamano = DOSSIER.stat().st_size
    assert tamano < 24_000, (
        f"El dossier creció hasta {tamano} bytes. Si sigue engordando dejará de "
        "poder leerse de una sola vez, que es la única razón por la que existe "
        "separado del resto de la documentación."
    )


def test_el_dossier_cita_las_lineas_que_esta_prueba_verifica():
    """Las dos listas no pueden separarse sin que alguien se entere.

    Si esta prueba verificara citas que el dossier ya no hace, estaría en verde
    sin proteger nada.
    """
    texto = DOSSIER.read_text(encoding="utf-8")
    ausentes = [
        f"{archivo}:{linea}"
        for archivo, linea, _ in CITAS
        if str(linea) not in texto
    ]

    assert not ausentes, (
        "Esta prueba verifica citas que el dossier ya no contiene:\n"
        + "\n".join(f"  - {c}" for c in ausentes)
    )
