"""Auditoría automática de modularidad: reglas de dependencia entre contextos.

ADR-0001 establece que un módulo de dominio solo puede invocar la interfaz
pública de otro. Hasta esta entrega la regla existía únicamente en la
documentación: nada impedía escribir `from app.menu.repository import
buscar_por_id` dentro de `pedidos` y dejar el CI en verde.

Esta prueba convierte la regla en algo verificable. Recorre el árbol de
sintaxis de cada archivo de `app/` y falla si un módulo importa de otro
algo que no sea su lenguaje publicado.

Ver `docs/ddd-contextos.md` §4 y `docs/violaciones.md` (V-04).
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

MODULOS_DE_DOMINIO = {"menu", "pedidos", "pagos", "usuarios"}

#: Lo único que puede cruzar la frontera de un contexto.
SUPERFICIE_PUBLICA = {"service", "contracts"}


def _modulo_de(archivo: Path) -> str | None:
    """Devuelve el módulo de dominio al que pertenece un archivo, si aplica."""
    relativa = archivo.relative_to(APP)
    if len(relativa.parts) < 2:
        return None
    return relativa.parts[0] if relativa.parts[0] in MODULOS_DE_DOMINIO else None


def _imports_de(archivo: Path) -> list[tuple[str, int]]:
    """Extrae los objetivos `app.<modulo>.<submodulo>` de cada import.

    Hay que normalizar dos formas equivalentes: en
    `from app.menu import service` el submódulo viaja en el nombre
    importado, mientras que en `from app.menu.service import obtener_item`
    viaja en el módulo. Mirar solo una de las dos deja pasar la mitad de
    los casos.
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    objetivos: list[tuple[str, int]] = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            objetivos.extend((alias.name, nodo.lineno) for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            if len(nodo.module.split(".")) <= 2:
                # `from app.menu import service, contracts`
                objetivos.extend(
                    (f"{nodo.module}.{alias.name}", nodo.lineno) for alias in nodo.names
                )
            else:
                # `from app.menu.service import obtener_item`
                objetivos.append((nodo.module, nodo.lineno))

    return [(nombre, linea) for nombre, linea in objetivos if nombre.startswith("app.")]


def _violaciones() -> list[str]:
    infracciones: list[str] = []

    for archivo in sorted(APP.rglob("*.py")):
        propio = _modulo_de(archivo)
        if propio is None:
            continue

        for importado, linea in _imports_de(archivo):
            partes = importado.split(".")
            if len(partes) < 2 or partes[1] not in MODULOS_DE_DOMINIO:
                continue

            ajeno = partes[1]
            if ajeno == propio:
                continue  # dentro del mismo contexto todo está permitido

            submodulo = partes[2] if len(partes) > 2 else ""
            if submodulo not in SUPERFICIE_PUBLICA:
                infracciones.append(
                    f"{archivo.relative_to(APP.parent)}:{linea} — el módulo "
                    f"'{propio}' importa '{importado}'. Solo se permite "
                    f"{sorted(SUPERFICIE_PUBLICA)} de otro contexto (ADR-0001)."
                )

    return infracciones


def test_ningun_modulo_cruza_la_frontera_de_otro_contexto():
    infracciones = _violaciones()

    assert not infracciones, "Violaciones de la regla de dependencia:\n" + "\n".join(
        f"  - {v}" for v in infracciones
    )


def test_la_auditoria_detecta_una_violacion_introducida(tmp_path, monkeypatch):
    """La prueba anterior solo vale si de verdad falla cuando debe.

    Se construye un árbol falso con una violación evidente y se comprueba
    que el detector la encuentra.
    """
    falso = tmp_path / "app"
    (falso / "pedidos").mkdir(parents=True)
    (falso / "pedidos" / "service.py").write_text(
        "from app.menu.repository import buscar_por_id\n", encoding="utf-8"
    )

    monkeypatch.setattr("tests.test_modularidad.APP", falso)
    infracciones = _violaciones()

    assert len(infracciones) == 1
    assert "app/menu/repository" in infracciones[0].replace(".", "/")
