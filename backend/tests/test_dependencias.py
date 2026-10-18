"""Que lo que se embarca y lo que se instala en la imagen sigan cuadrando.

La S13 encontró que la imagen de producción instalaba el lock de CI, así que
llevaba dentro **ocho paquetes que ningún código de la aplicación importa**:
`pytest`, `httpx` y seis dependencias exclusivas de los dos. Uno de ellos,
`pytest<=9.0.2`, con una vulnerabilidad conocida (GHSA-6w46-j5rx-g56g) que
nunca se podría explotar porque ese código no se ejecuta allí.

La corrección fue derivar `requirements-prod.txt` con los 22 paquetes
alcanzables desde `fastapi`, `uvicorn` y `psycopg`. Estas pruebas vigilan la
deriva en las **dos direcciones**, que es lo que hace que la corrección no se
deshaga sola:

- Que no vuelva a entrar en el lock de producción nada que solo sirva a las
  pruebas.
- Que ningún archivo que la imagen copia importe algo que ese lock no instala.

La segunda es la que más vale. Un `import httpx` en `app/` sería razonable de
escribir —ya está en el entorno de desarrollo, y la suite pasaría— y reventaría
en el arranque del contenedor con `ModuleNotFoundError`. Es exactamente el fallo
de la semana 8 con `psycopg`, en la dirección contraria.

No se comprueba construyendo la imagen porque no hay Docker en la máquina de
desarrollo (deuda D-01 de arc42 §11). El job `dependencias` del pipeline sí
instala el lock en Linux y lo importa; esto es la mitad que se puede ejecutar
sin salir del portátil.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
LOCK_PRODUCCION = BACKEND / "requirements-prod.txt"
LOCK_CI = BACKEND / "requirements-ci.txt"
DOCKERFILE = BACKEND / "Dockerfile"

#: Paquetes retirados del lock de producción en la S13.
RETIRADOS = frozenset({
    "certifi", "httpcore", "httpx", "iniconfig",
    "packaging", "pluggy", "pygments", "pytest",
})

#: Nombre de distribución → módulo que se importa, cuando no coinciden.
#:
#: Solo las que hacen falta. Inventar un mapa exhaustivo sería adivinar: lo que
#: importa es que las que el código usa de verdad estén resueltas.
MODULO_DE_LA_DISTRIBUCION = {
    "pyyaml": "yaml",
    "psycopg-binary": None,  # Ruedas de psycopg: no se importa por su nombre.
    "typing-extensions": "typing_extensions",
    "psycopg-pool": "psycopg_pool",
    "annotated-types": "annotated_types",
    "annotated-doc": "annotated_doc",
    "pydantic-core": "pydantic_core",
    "python-dotenv": "dotenv",
    "typing-inspection": "typing_inspection",
    "uvicorn[standard]": "uvicorn",
}

NOMBRE_FIJADO = re.compile(r"^([A-Za-z0-9._+-]+(?:\[[^\]]*\])?)==", re.M)


def _distribuciones(lock: Path) -> set[str]:
    """Nombres de distribución fijados en un lock, normalizados."""
    texto = lock.read_text(encoding="utf-8")
    return {
        re.sub(r"\[[^\]]*\]", "", n).lower().replace("_", "-")
        for n in NOMBRE_FIJADO.findall(texto)
    }


def _modulos_instalables(lock: Path) -> set[str]:
    """Módulos de primer nivel que un lock pone a disposición."""
    modulos = set()
    for dist in _distribuciones(lock):
        alias = MODULO_DE_LA_DISTRIBUCION.get(dist, dist.replace("-", "_"))
        if alias:
            modulos.add(alias)
    return modulos


def _archivos_que_viajan_a_la_imagen() -> list[Path]:
    """Los `.py` que el Dockerfile copia, leídos del propio Dockerfile.

    Se derivan de él y no de una lista escrita aquí: una lista paralela se
    desincroniza en silencio, que es la clase de defecto que esta suite existe
    para evitar.
    """
    texto = DOCKERFILE.read_text(encoding="utf-8")
    archivos: list[Path] = []

    for linea in texto.splitlines():
        if not linea.startswith("COPY ") or "--from=" in linea:
            continue
        # `COPY origen... destino`: el último token es el destino.
        partes = linea.split()[1:-1]
        for origen in partes:
            ruta = BACKEND / origen
            if ruta.is_dir():
                archivos.extend(sorted(ruta.rglob("*.py")))
            elif ruta.suffix == ".py" and ruta.is_file():
                archivos.append(ruta)

    return archivos


def _importaciones(ruta: Path) -> set[str]:
    """Módulos de primer nivel que un archivo importa."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos = set()

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            modulos.add(nodo.module.split(".")[0])

    return modulos


def test_el_dockerfile_instala_el_lock_de_produccion():
    """La imagen no puede volver al lock de CI sin que esto se entere.

    Es una sola línea del Dockerfile, y volver a `requirements-ci.txt` dejaría
    la imagen funcionando igual de bien — con ocho paquetes de más dentro y sin
    ningún síntoma. Los defectos que no dan error son los que duran.
    """
    texto = DOCKERFILE.read_text(encoding="utf-8")
    instalaciones = re.findall(r"-r\s+(requirements[\w.-]*\.txt)", texto)

    assert instalaciones, "El Dockerfile ya no instala ningún requirements"
    assert set(instalaciones) == {"requirements-prod.txt"}, (
        f"El Dockerfile instala {sorted(set(instalaciones))}. La imagen debe "
        "instalar solo `requirements-prod.txt`: el lock de CI añade `pytest`, "
        "`httpx` y seis dependencias suyas que la aplicación no importa."
    )


def test_el_lock_de_produccion_no_trae_instrumental_de_pruebas():
    """Los ocho retirados no pueden volver a entrar."""
    presentes = sorted(RETIRADOS & _distribuciones(LOCK_PRODUCCION))

    assert not presentes, (
        f"`requirements-prod.txt` volvió a traer {presentes}. Si alguno hace "
        "falta de verdad en producción, hay que decir dónde se importa y "
        "quitarlo de la lista de retirados con ese motivo escrito."
    )


def test_el_lock_de_ci_si_trae_el_instrumental():
    """El complemento: la suite necesita lo que producción no.

    Sin esta prueba, alguien podría «arreglar» la auditoría retirando `pytest`
    de los dos locks, y el pipeline dejaría de poder ejecutar las pruebas. La
    decisión fue separar los entornos, no empobrecer el de CI.
    """
    faltan = sorted(RETIRADOS - _distribuciones(LOCK_CI))

    assert not faltan, (
        f"`requirements-ci.txt` ya no fija {faltan}. El lock del pipeline tiene "
        "que seguir trayendo el instrumental de pruebas: lo que se separó son "
        "los entornos, no las capacidades."
    )


def test_los_dos_locks_solo_difieren_en_el_instrumental():
    """Ninguna dependencia de producción puede existir solo en uno de los dos.

    Es la prueba que habría evitado el fallo de la semana 8, cuando `psycopg`
    estaba en el lock de CI y no en lo que instalaba el despliegue: las pruebas
    pasaron en verde y producción arrancó sin la librería.

    Con dos locks ese riesgo vuelve a existir, y esta es la red: la diferencia
    entre ellos tiene que ser **exactamente** los ocho paquetes retirados, ni
    uno más.
    """
    produccion = _distribuciones(LOCK_PRODUCCION)
    ci = _distribuciones(LOCK_CI)

    solo_en_ci = ci - produccion
    solo_en_produccion = produccion - ci

    assert solo_en_produccion == set(), (
        f"`requirements-prod.txt` fija {sorted(solo_en_produccion)}, que el "
        "lock de CI no tiene. La suite correría contra un árbol distinto del "
        "que se despliega, que es precisamente lo que no debe pasar."
    )
    assert solo_en_ci == RETIRADOS, (
        f"La diferencia entre los locks es {sorted(solo_en_ci)} y debería ser "
        f"{sorted(RETIRADOS)}. Si se añadió una dependencia, hay que decidir si "
        "es de producción —y entonces va en los dos— o instrumental."
    )


@pytest.mark.parametrize(
    "archivo",
    _archivos_que_viajan_a_la_imagen(),
    ids=lambda p: str(p.relative_to(BACKEND)).replace("\\", "/"),
)
def test_lo_que_viaja_a_la_imagen_solo_importa_lo_que_la_imagen_instala(archivo):
    """Un import que el lock de producción no satisface revienta el contenedor.

    Y lo hace **en el arranque**, no en CI: la suite tiene `httpx` instalado,
    así que un `import httpx` en `app/` pasaría en verde aquí y fallaría con
    `ModuleNotFoundError` al desplegar. Es el fallo de la semana 8 en la
    dirección contraria.

    Se comprueba solo sobre los archivos que el Dockerfile copia. Los que no
    viajan —`comparar_contratos.py`, por ejemplo, que importa `yaml` y corre en
    el pipeline— pueden importar lo que el pipeline tenga.
    """
    disponibles = _modulos_instalables(LOCK_PRODUCCION) | {"app"}
    faltantes = sorted(
        m for m in _importaciones(archivo)
        if m not in disponibles and m not in sys.stdlib_module_names
    )

    assert not faltantes, (
        f"{archivo.relative_to(BACKEND)} importa {faltantes}, que "
        "`requirements-prod.txt` no instala. En la imagen eso es un "
        "`ModuleNotFoundError` en el arranque. Si la dependencia es legítima, "
        "va en `requirements.in`, se regenera el lock de CI **en Linux** y se "
        "vuelve a derivar el de producción."
    )
