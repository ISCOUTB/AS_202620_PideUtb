"""Prueba de contrato · compatibilidad entre versiones.

Comprueba que el contrato vigente no rompe a un cliente escrito contra la
versión congelada anterior, y —lo que de verdad da valor a lo anterior— que el
detector **falla cuando debe**.

Una validación que nunca puede ponerse en rojo no demuestra nada: solo confirma
que el archivo existe. Por eso la mitad de este módulo introduce roturas a
propósito y exige que cada una sea detectada, con la misma disciplina de caso
negativo que `test_modularidad.py`.

Reglas y su justificación: `docs/api/politica-versionado.md` §3.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.comparar_contratos import Cambio, cargar, comparar, incompatibles
from tests.conftest import mutar

RAIZ = Path(__file__).resolve().parents[2]
CONTRATO_VIGENTE = RAIZ / "docs" / "api" / "openapi.yaml"
LINEA_BASE = RAIZ / "docs" / "api" / "historial" / "openapi-1.0.0.yaml"


@pytest.fixture(scope="module")
def contrato() -> dict:
    return cargar(CONTRATO_VIGENTE)


def _reglas(cambios: list[Cambio]) -> set[str]:
    return {c.regla for c in cambios}


# --------------------------------------------------------------------------
# El contrato vigente frente a la línea base congelada
# --------------------------------------------------------------------------

def test_el_contrato_vigente_no_rompe_la_linea_base(contrato):
    """Lo que ejecuta el pipeline en cada push.

    Si alguien edita `openapi.yaml` de forma incompatible sin subir la versión
    mayor, esta prueba pone la construcción en rojo con el detalle exacto.
    """
    rotos = incompatibles(comparar(cargar(LINEA_BASE), contrato))

    mayor_vigente = contrato["info"]["version"].split(".")[0]
    mayor_base = cargar(LINEA_BASE)["info"]["version"].split(".")[0]

    if mayor_vigente != mayor_base:
        pytest.skip(
            f"La versión mayor subió de {mayor_base} a {mayor_vigente}: los "
            "cambios incompatibles están permitidos bajo un prefijo de ruta nuevo."
        )

    assert not rotos, (
        "El contrato introduce cambios incompatibles sin subir la versión mayor.\n"
        "Subí `info.version` a la siguiente MAYOR y publicá la API bajo `/v2` "
        "(docs/api/politica-versionado.md §2), o revertí el cambio:\n\n"
        + "\n".join(str(c) for c in rotos)
    )


def test_el_comparador_no_inventa_diferencias(contrato):
    """Un contrato comparado consigo mismo no puede producir ni una diferencia.

    Sin esta prueba, un comparador roto que marcase todo como incompatible
    pasaría inadvertido: las demás pruebas seguirían en verde porque también
    esperan incompatibilidades.
    """
    assert comparar(contrato, copy.deepcopy(contrato)) == []


# --------------------------------------------------------------------------
# Casos negativos: cada rotura de la política debe detectarse
# --------------------------------------------------------------------------

def _quitar_operacion(doc: dict) -> None:
    del doc["paths"]["/v1/pedidos/{pedido_id}"]


def _quitar_campo_de_respuesta(doc: dict) -> None:
    pedido = doc["components"]["schemas"]["Pedido"]
    del pedido["properties"]["total_centavos"]
    pedido["required"].remove("total_centavos")


def _volver_obligatorio_un_opcional(doc: dict) -> None:
    doc["components"]["schemas"]["CrearPedidoRequest"]["required"].append("cantidad")


def _anadir_campo_obligatorio_a_peticion(doc: dict) -> None:
    peticion = doc["components"]["schemas"]["CrearPedidoRequest"]
    peticion["properties"]["token_promocional"] = {"type": "string"}
    peticion["required"].append("token_promocional")


def _cambiar_el_tipo_del_dinero(doc: dict) -> None:
    doc["components"]["schemas"]["ItemMenu"]["properties"]["precio_centavos"]["type"] = "number"


def _quitar_valor_de_enum_de_peticion(doc: dict) -> None:
    doc["components"]["schemas"]["MetodoDePago"]["enum"].remove("nequi")


def _anadir_valor_a_enum_de_respuesta(doc: dict) -> None:
    doc["components"]["schemas"]["EstadoPedido"]["enum"].append("reembolsado")


def _estrechar_una_restriccion(doc: dict) -> None:
    doc["components"]["schemas"]["CrearPedidoRequest"]["properties"]["cantidad"]["maximum"] = 10


def _quitar_un_codigo_de_respuesta(doc: dict) -> None:
    del doc["paths"]["/v1/pedidos"]["post"]["responses"]["409"]


def _volver_anulable_una_respuesta(doc: dict) -> None:
    doc["components"]["schemas"]["Pedido"]["properties"]["nombre_item"]["type"] = ["string", "null"]


ROTURAS = [
    pytest.param(_quitar_operacion, "I-1",
                 id="I-1 · se elimina un endpoint"),
    pytest.param(_quitar_campo_de_respuesta, "I-2",
                 id="I-2 · se elimina un campo requerido de una respuesta"),
    pytest.param(_volver_obligatorio_un_opcional, "I-3",
                 id="I-3 · un campo opcional de petición pasa a obligatorio"),
    pytest.param(_anadir_campo_obligatorio_a_peticion, "I-4",
                 id="I-4 · se añade un campo obligatorio a una petición"),
    pytest.param(_cambiar_el_tipo_del_dinero, "I-5",
                 id="I-5 · cambia el tipo de un campo"),
    pytest.param(_quitar_valor_de_enum_de_peticion, "I-7",
                 id="I-7 · se quita un valor de un enum de petición"),
    pytest.param(_anadir_valor_a_enum_de_respuesta, "I-8",
                 id="I-8 · se añade un valor a un enum de respuesta"),
    pytest.param(_estrechar_una_restriccion, "I-9",
                 id="I-9 · se estrecha una restricción de petición"),
    pytest.param(_quitar_un_codigo_de_respuesta, "I-10",
                 id="I-10 · se elimina un código de respuesta documentado"),
    pytest.param(_volver_anulable_una_respuesta, "I-5",
                 id="I-5 · una respuesta pasa a poder ser null"),
]


@pytest.mark.parametrize("mutacion, regla_esperada", ROTURAS)
def test_cada_cambio_incompatible_se_detecta(contrato, mutacion, regla_esperada):
    """Si alguno de estos casos deja de fallar, la prueba de contrato es decorativa."""
    rotos = incompatibles(comparar(contrato, mutar(contrato, mutacion)))

    assert rotos, (
        f"El comparador NO detectó la rotura {regla_esperada} introducida por "
        f"`{mutacion.__name__}`. Una prueba de contrato que no falla ante un "
        "cambio incompatible no es una prueba de contrato."
    )
    assert regla_esperada in _reglas(rotos), (
        f"Se detectó una rotura, pero clasificada como {sorted(_reglas(rotos))} "
        f"en lugar de {regla_esperada}. El diagnóstico importa tanto como el "
        "fallo: es lo que le dice al autor del cambio qué hizo mal."
    )


# --------------------------------------------------------------------------
# Casos positivos: la evolución legítima no debe bloquearse
# --------------------------------------------------------------------------

def _anadir_operacion(doc: dict) -> None:
    doc["paths"]["/v1/pedidos/{pedido_id}/cancelacion"] = {
        "post": {
            "operationId": "cancelarPedido",
            "responses": {
                "200": {
                    "description": "Pedido cancelado.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Pedido"}
                        }
                    },
                }
            },
        }
    }


def _anadir_campo_opcional_a_peticion(doc: dict) -> None:
    doc["components"]["schemas"]["CrearPedidoRequest"]["properties"]["nota"] = {
        "type": "string", "maxLength": 200,
    }


def _anadir_campo_a_respuesta(doc: dict) -> None:
    doc["components"]["schemas"]["Pedido"]["properties"]["creado_en"] = {
        "type": "string", "format": "date-time",
    }


def _relajar_una_restriccion(doc: dict) -> None:
    doc["components"]["schemas"]["CrearPedidoRequest"]["properties"]["cantidad"]["maximum"] = 99


def _quitar_valor_de_enum_de_respuesta(doc: dict) -> None:
    doc["components"]["schemas"]["EstadoPedido"]["enum"].remove("cancelado")


EVOLUCIONES = [
    pytest.param(_anadir_operacion, id="se añade un endpoint"),
    pytest.param(_anadir_campo_opcional_a_peticion, id="se añade un campo opcional a una petición"),
    pytest.param(_anadir_campo_a_respuesta, id="se añade un campo a una respuesta"),
    pytest.param(_relajar_una_restriccion, id="se relaja una restricción de petición"),
    pytest.param(_quitar_valor_de_enum_de_respuesta, id="se quita un valor de un enum de respuesta"),
]


@pytest.mark.parametrize("mutacion", EVOLUCIONES)
def test_la_evolucion_compatible_no_se_bloquea(contrato, mutacion):
    """Un detector que marca todo como roto obliga a ignorarlo, y entonces no sirve.

    Estos cinco cambios son precisamente los que la política permite hacer sin
    subir la versión mayor.
    """
    rotos = incompatibles(comparar(contrato, mutar(contrato, mutacion)))

    assert not rotos, (
        f"`{mutacion.__name__}` es un cambio compatible según la política §2, "
        "pero el comparador lo marcó como rotura:\n"
        + "\n".join(str(c) for c in rotos)
    )


def test_la_linea_base_congelada_existe_y_declara_su_version():
    """El historial es la referencia de la promesa: sin él no hay contra qué medir."""
    assert LINEA_BASE.exists(), (
        f"Falta la versión congelada {LINEA_BASE.name}. Cada release publicada "
        "se congela en docs/api/historial/ y no se edita nunca más."
    )
    assert cargar(LINEA_BASE)["info"]["version"] == "1.0.0"
