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


#: Nombre que se da a los archivos sueltos en `app/`: main, salud,
#: observabilidad, base_de_datos, eventos, esquemas_comunes.
#:
#: No pertenecen a ningún contexto, así que **todos** los contextos les son
#: ajenos y solo pueden tocar su superficie pública.
TRANSVERSAL = "(transversal)"


def _modulo_de(archivo: Path) -> str | None:
    """Devuelve el módulo al que pertenece un archivo.

    Los archivos sueltos en `app/` devuelven `TRANSVERSAL` y **sí se auditan**.
    Antes devolvían `None` y se saltaban por completo, y ese fue el punto ciego
    por el que entró la erosión de la semana 8: `app/salud.py`, generado con
    IA, importaba `app.menu.repository` —el repositorio de otro contexto— y la
    construcción siguió en verde.

    Una regla automatizada que no cubre todo el árbol da una seguridad que no
    tiene, y es peor que no tenerla: nadie vuelve a mirar a mano.
    """
    relativa = archivo.relative_to(APP)
    if len(relativa.parts) < 2:
        return TRANSVERSAL
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

            # `main.py` es la raíz de composición: su trabajo es montar los
            # routers de cada contexto, y no puede hacerlo sin importarlos.
            #
            # La excepción es deliberadamente estrecha —un archivo concreto y un
            # submódulo concreto— y no un ensanchamiento de la regla. Que un
            # módulo de dominio importe el `router` de otro seguiría siendo una
            # violación: saltarse el servicio para hablar por HTTP interno es
            # justo lo que ADR-0001 prohíbe.
            if propio is TRANSVERSAL and archivo.name == "main.py" and submodulo == "router":
                continue

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


def test_la_auditoria_ve_los_archivos_sueltos_en_app(tmp_path, monkeypatch):
    """El punto ciego por el que entró la erosión de la semana 8.

    `app/salud.py`, generado con IA, importaba `app.menu.repository` y la
    construcción siguió en verde durante toda una entrega: `_modulo_de`
    devolvía `None` para los archivos sueltos en `app/` y `_violaciones` los
    saltaba.

    Esta prueba reproduce exactamente ese caso. Sin la corrección, pasa sin
    detectar nada —que es el fallo— y por eso tiene que existir: una regla
    automatizada que no cubre todo el árbol da una seguridad que no tiene.
    """
    falso = tmp_path / "app"
    falso.mkdir(parents=True)
    (falso / "menu").mkdir()
    (falso / "salud.py").write_text(
        "from app.menu import repository as repositorio_catalogo\n", encoding="utf-8"
    )

    monkeypatch.setattr("tests.test_modularidad.APP", falso)
    infracciones = _violaciones()

    assert len(infracciones) == 1, (
        "El archivo suelto en app/ no se auditó. Es el punto ciego que dejó "
        "pasar la violación de salud.py durante toda la semana 8."
    )
    assert "salud.py" in infracciones[0]


def test_la_excepcion_de_la_raiz_de_composicion_no_se_extiende(tmp_path, monkeypatch):
    """`main.py` puede importar routers; nadie más.

    La excepción se añadió porque la raíz de composición no puede montar los
    routers sin importarlos. Esta prueba comprueba que quedó acotada: si se
    hubiera ensanchado la regla en vez de hacer una excepción concreta, un
    módulo de dominio podría saltarse el servicio de otro hablándole por su
    router, que es justo lo que ADR-0001 prohíbe.
    """
    falso = tmp_path / "app"
    (falso / "pedidos").mkdir(parents=True)
    (falso / "menu").mkdir()

    # La raíz de composición: permitido.
    (falso / "main.py").write_text(
        "from app.menu.router import router as menu_router\n", encoding="utf-8"
    )
    # Otro archivo transversal haciendo lo mismo: NO permitido.
    (falso / "observabilidad.py").write_text(
        "from app.menu.router import router\n", encoding="utf-8"
    )
    # Un módulo de dominio haciendo lo mismo: NO permitido.
    (falso / "pedidos" / "service.py").write_text(
        "from app.menu.router import router\n", encoding="utf-8"
    )

    monkeypatch.setattr("tests.test_modularidad.APP", falso)
    infracciones = _violaciones()

    culpables = sorted(i.split(":")[0].replace("\\", "/").split("/")[-1] for i in infracciones)
    assert culpables == ["observabilidad.py", "service.py"], (
        "La excepción tiene que cubrir main.py y solo main.py. "
        f"Infracciones encontradas: {infracciones}"
    )
