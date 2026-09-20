"""Prueba de contrato · expectativas declaradas por el consumidor.

Es la forma de prueba de contrato que describe el material de la semana: *el
consumidor declara qué campos necesita; el pipeline del proveedor falla si deja
de emitirlos*.

Las otras dos pruebas de contrato de este repositorio miran el contrato desde
dentro —¿es compatible consigo mismo?, ¿lo cumple el código?—. Esta lo mira
desde fuera, que es la única perspectiva desde la que se puede responder a la
pregunta que de verdad importa: **¿este cambio rompe a alguien?**

Un campo puede estar perfectamente declarado en el contrato, perfectamente
implementado, y aun así ser retirable sin daño si ningún consumidor lo lee. Y
al revés: un campo que parece interno puede ser de lo que depende toda una
pantalla. La única forma de saberlo es que el consumidor lo escriba, y
`contracts/consumidor-web.yaml` es donde lo escribe.

Cómo se lee un fallo aquí: **no es el consumidor el que está mal**. Es el
proveedor, que retiró algo que había prometido.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.comparar_contratos import cargar, resolver
from tests.conftest import mutar

RAIZ = Path(__file__).resolve().parents[2]
CONTRATO = RAIZ / "docs" / "api" / "openapi.yaml"
EXPECTATIVAS = RAIZ / "contracts" / "consumidor-web.yaml"

METODOS_HTTP = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


@pytest.fixture(scope="module")
def contrato() -> dict:
    return cargar(CONTRATO)


@pytest.fixture(scope="module")
def expectativas() -> dict:
    return cargar(EXPECTATIVAS)


# --------------------------------------------------------------------------
# Navegación por el contrato
# --------------------------------------------------------------------------

def _por_operation_id(contrato: dict) -> dict[str, dict]:
    encontradas: dict[str, dict] = {}
    for item in (contrato.get("paths") or {}).values():
        for metodo, operacion in item.items():
            if metodo.lower() in METODOS_HTTP and "operationId" in operacion:
                encontradas[operacion["operationId"]] = operacion
    return encontradas


def _respuesta_exitosa(contrato: dict, operacion: dict) -> dict | None:
    """Esquema del primer código 2xx declarado."""
    for codigo, respuesta in sorted((operacion.get("responses") or {}).items()):
        if not str(codigo).startswith("2"):
            continue
        respuesta = resolver(contrato, respuesta)
        medio = ((respuesta or {}).get("content") or {}).get("application/json")
        if medio and "schema" in medio:
            return resolver(contrato, medio["schema"])
    return None


def _esquema_de_peticion(contrato: dict, operacion: dict) -> dict | None:
    cuerpo = resolver(contrato, operacion.get("requestBody") or {})
    medio = ((cuerpo or {}).get("content") or {}).get("application/json")
    return resolver(contrato, medio["schema"]) if medio and "schema" in medio else None


def _existe_campo(contrato: dict, esquema: dict | None, ruta: str) -> bool:
    """Resuelve rutas como `items[].nombre` dentro de un esquema."""
    actual = esquema
    for tramo in ruta.split("."):
        if actual is None:
            return False
        entrar_en_lista = tramo.endswith("[]")
        nombre = tramo[:-2] if entrar_en_lista else tramo

        propiedades = (resolver(contrato, actual) or {}).get("properties") or {}
        if nombre not in propiedades:
            return False
        actual = resolver(contrato, propiedades[nombre])

        if entrar_en_lista:
            if actual.get("type") != "array" or "items" not in actual:
                return False
            actual = resolver(contrato, actual["items"])

    return True


# --------------------------------------------------------------------------
# Lo que el pipeline del proveedor comprueba en cada push
# --------------------------------------------------------------------------

def test_toda_operacion_que_el_consumidor_usa_sigue_existiendo(contrato, expectativas):
    del_contrato = _por_operation_id(contrato)
    usadas = set(expectativas["operaciones"])

    desaparecidas = sorted(usadas - set(del_contrato))

    assert not desaparecidas, (
        f"El contrato ya no ofrece {desaparecidas}, y el consumidor "
        f"'{expectativas['consumidor']}' las usa. Retirar una operación de la "
        "que alguien depende es un cambio incompatible (regla I-1)."
    )


def test_todo_campo_que_el_consumidor_lee_sigue_emitiendose(contrato, expectativas):
    """La prueba central: el proveedor no puede dejar de emitir lo prometido."""
    del_contrato = _por_operation_id(contrato)
    ausentes: list[str] = []

    for nombre, declaracion in expectativas["operaciones"].items():
        operacion = del_contrato.get(nombre)
        if operacion is None:
            continue  # lo reporta la prueba anterior

        esquema = _respuesta_exitosa(contrato, operacion)
        for campo in declaracion.get("campos_leidos") or []:
            if not _existe_campo(contrato, esquema, campo):
                ausentes.append(f"{nombre} → {campo}")

    assert not ausentes, (
        f"El contrato dejó de emitir campos que '{expectativas['consumidor']}' "
        "lee:\n"
        + "\n".join(f"  - {c}" for c in ausentes)
        + "\n\nNo es el consumidor el que está mal: es el proveedor, que retiró "
        "algo que había prometido (regla I-2)."
    )


def test_todo_campo_que_el_consumidor_envia_sigue_aceptandose(contrato, expectativas):
    del_contrato = _por_operation_id(contrato)
    rechazados: list[str] = []

    for nombre, declaracion in expectativas["operaciones"].items():
        operacion = del_contrato.get(nombre)
        if operacion is None:
            continue

        esquema = _esquema_de_peticion(contrato, operacion)
        for campo in declaracion.get("campos_enviados") or []:
            if not _existe_campo(contrato, esquema, campo):
                rechazados.append(f"{nombre} → {campo}")

    assert not rechazados, (
        "El contrato ya no acepta campos que el consumidor envía:\n"
        + "\n".join(f"  - {c}" for c in rechazados)
    )


def test_no_aparecen_campos_obligatorios_nuevos_en_las_peticiones(contrato, expectativas):
    """Regla I-4 desde la perspectiva de quien la sufre.

    El consumidor declara qué envía. Si el contrato empieza a exigir algo que
    no está en esa lista, las peticiones que hoy funcionan pasarán a `422`.
    """
    del_contrato = _por_operation_id(contrato)
    problemas: list[str] = []

    for nombre, declaracion in expectativas["operaciones"].items():
        operacion = del_contrato.get(nombre)
        if operacion is None:
            continue

        esquema = _esquema_de_peticion(contrato, operacion)
        if esquema is None:
            continue

        exigidos = set(esquema.get("required") or [])
        enviados = {c.split(".")[0].removesuffix("[]") for c in (declaracion.get("campos_enviados") or [])}
        for campo in sorted(exigidos - enviados):
            problemas.append(f"{nombre} exige '{campo}', que el consumidor no envía")

    assert not problemas, (
        "Aparecieron campos obligatorios nuevos en peticiones (regla I-4):\n"
        + "\n".join(f"  - {p}" for p in problemas)
    )


def test_el_consumidor_maneja_todos_los_codigos_que_puede_recibir(contrato, expectativas):
    """Al revés que las anteriores: aquí el que va por detrás es el consumidor.

    Si el contrato declara un código que el consumidor no contempla, el usuario
    verá una pantalla en blanco ante una respuesta perfectamente legítima. No
    es una rotura del proveedor, pero es igual de real.
    """
    del_contrato = _por_operation_id(contrato)
    sin_manejar: list[str] = []

    for nombre, declaracion in expectativas["operaciones"].items():
        operacion = del_contrato.get(nombre)
        if operacion is None:
            continue

        declarados = {str(c) for c in (operacion.get("responses") or {})}
        manejados = {str(c) for c in (declaracion.get("codigos_manejados") or [])}
        for codigo in sorted(declarados - manejados):
            # 422 solo puede darse si el consumidor envía cuerpo o parámetros
            # que el contrato valide; para las operaciones que solo leen, es
            # ruido del framework y no algo que el frontend deba tratar.
            if codigo == "422" and not declaracion.get("campos_enviados"):
                continue
            sin_manejar.append(f"{nombre} puede responder {codigo} y el consumidor no lo trata")

    assert not sin_manejar, "\n".join(f"  - {p}" for p in sin_manejar)


@pytest.mark.parametrize(
    "esquema_contrato, clave_expectativas",
    [
        ("EstadoPedido", "estados_pedido_interpretados"),
        ("EstadoPago", "estados_pago_interpretados"),
    ],
)
def test_el_consumidor_interpreta_todos_los_estados_posibles(
    contrato, expectativas, esquema_contrato, clave_expectativas
):
    """Hace comprobable la regla I-8: añadir un valor a un enum de respuesta rompe.

    Mientras «añadir un estado es incompatible» viva solo en un documento, el
    día que alguien añada uno nadie se enterará. Aquí el CI se pone en rojo y
    obliga a decidir qué hace el frontend con el valor nuevo antes de
    publicarlo.
    """
    del_contrato = set(contrato["components"]["schemas"][esquema_contrato]["enum"])
    interpretados = set(expectativas[clave_expectativas])

    sin_interpretar = sorted(del_contrato - interpretados)

    assert not sin_interpretar, (
        f"El contrato puede devolver {sin_interpretar} y el consumidor no sabe "
        f"qué hacer con esos valores de `{esquema_contrato}`.\n"
        "Añadir un valor a un enum de respuesta es un cambio incompatible "
        "(docs/api/politica-versionado.md §3.1): o se declara aquí qué hace el "
        "consumidor con él, o se publica bajo una versión mayor nueva."
    )


def test_los_metodos_de_pago_que_ofrece_el_consumidor_siguen_aceptandose(
    contrato, expectativas
):
    admitidos = set(contrato["components"]["schemas"]["MetodoDePago"]["enum"])
    ofrecidos = set(expectativas["metodos_de_pago_ofrecidos"])

    retirados = sorted(ofrecidos - admitidos)

    assert not retirados, (
        f"El consumidor ofrece {retirados} y el contrato ya no los admite. "
        "Quitar un valor de un enum de petición es incompatible (regla I-7)."
    )


# --------------------------------------------------------------------------
# Caso negativo
# --------------------------------------------------------------------------

def _retirar_un_campo_que_el_consumidor_lee(doc: dict) -> None:
    pedido = doc["components"]["schemas"]["Pedido"]
    del pedido["properties"]["total_centavos"]
    pedido["required"].remove("total_centavos")


def _retirar_un_campo_anidado_en_la_lista(doc: dict) -> None:
    item = doc["components"]["schemas"]["ItemMenu"]
    del item["properties"]["precio_centavos"]
    item["required"].remove("precio_centavos")


def _retirar_una_operacion_en_uso(doc: dict) -> None:
    del doc["paths"]["/v1/pedidos/{pedido_id}"]


@pytest.mark.parametrize(
    "rotura",
    [
        _retirar_un_campo_que_el_consumidor_lee,
        _retirar_un_campo_anidado_en_la_lista,
        _retirar_una_operacion_en_uso,
    ],
    ids=lambda f: f.__name__.strip("_"),
)
def test_retirar_algo_que_el_consumidor_usa_rompe_la_construccion(
    contrato, expectativas, rotura
):
    """La comprobación de arriba solo vale si de verdad falla cuando debe."""
    mutado = mutar(contrato, rotura)

    with pytest.raises(AssertionError):
        test_toda_operacion_que_el_consumidor_usa_sigue_existiendo(mutado, expectativas)
        test_todo_campo_que_el_consumidor_lee_sigue_emitiendose(mutado, expectativas)
