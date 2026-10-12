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
HISTORIAL = RAIZ / "docs" / "api" / "historial"


def mayor_de(version: str) -> str:
    return str(version).split(".")[0]


def linea_base_de(contrato: dict) -> Path:
    """El `X.0.0` congelado de la MAYOR que el contrato declara hoy.

    Antes esto era `openapi-1.0.0.yaml`, un literal, y la prueba de abajo se
    **saltaba** cuando la MAYOR subía. Con eso, el salto a 2.0.0 habría dejado
    la comparación apagada para siempre: todo cambio posterior dentro de la 2.x
    pasaría sin que nadie lo midiera, y la prueba seguiría apareciendo en verde
    como «omitida». Un portón que se abre solo y no vuelve a cerrarse es peor
    que no tener portón, porque da la impresión contraria.

    Haciendo que la línea base siga a la MAYOR vigente, un salto de MAYOR no
    apaga la comparación: la **reapunta**. Dentro de la 2.x no se admite ninguna
    rotura frente a la 2.0.0, igual que antes no se admitía frente a la 1.0.0.
    """
    return HISTORIAL / f"openapi-{mayor_de(contrato['info']['version'])}.0.0.yaml"


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

    Compara contra el `X.0.0` de la **MAYOR vigente**, no contra la 1.0.0 para
    siempre. Es el cambio que la semana 10 obligó a hacer: con la base fija, el
    salto a 2.0.0 habría dejado esta comparación saltada indefinidamente.
    """
    base = linea_base_de(contrato)

    assert base.exists(), (
        f"El contrato declara {contrato['info']['version']} y falta su línea "
        f"base congelada `{base.name}`.\n\nUn salto de MAYOR no apaga esta "
        "comparación: la reapunta. Copiá `docs/api/openapi.yaml` a "
        f"`docs/api/historial/{base.name}` en el mismo commit que sube la "
        "versión, y a partir de ahí no se edita nunca más."
    )

    rotos = incompatibles(comparar(cargar(base), contrato))

    assert not rotos, (
        f"El contrato introduce cambios incompatibles frente a `{base.name}`, "
        "que es la MAYOR que él mismo declara cumplir.\n\nSubí `info.version` "
        "a la siguiente MAYOR y congelá su línea base "
        "(docs/api/politica-versionado.md §2 y §5 bis), o revertí el cambio:\n\n"
        + "\n".join(str(c) for c in rotos)
    )


def test_el_salto_de_mayor_esta_justificado_por_una_rotura_real(contrato):
    """Subir la MAYOR no es una decisión estética: hay que poder señalar la rotura.

    Compara el contrato vigente con la **última MENOR de la MAYOR anterior** y
    exige encontrar al menos un cambio incompatible. Sin esto, «subimos a 2.0.0»
    sería una afirmación del documento; con esto es el comparador el que dice que
    el salto hacía falta, y dice exactamente por qué.

    Es la otra mitad de I-12. Una regla de compatibilidad sirve para dos cosas
    simétricas: impedir que se rompa sin avisar, e impedir que se avise sin
    romper. La segunda parece inofensiva y no lo es: un salto de MAYOR anuncia
    trabajo a todos los consumidores, y si ese trabajo no existe, la próxima vez
    que se anuncie nadie lo va a creer.

    Se omite cuando no hay MAYOR anterior congelada, que es el caso de un
    contrato que todavía va por la 1.x.
    """
    mayor = int(mayor_de(contrato["info"]["version"]))
    if mayor <= 1:
        pytest.skip("No hay una MAYOR anterior contra la que medir el salto.")

    anteriores = sorted(HISTORIAL.glob(f"openapi-{mayor - 1}.*.yaml"))
    if not anteriores:
        pytest.skip(f"No hay ninguna {mayor - 1}.x congelada en el historial.")

    ultima = anteriores[-1]
    rotos = incompatibles(comparar(cargar(ultima), contrato))

    assert rotos, (
        f"El contrato declara {contrato['info']['version']} pero no rompe nada "
        f"frente a `{ultima.name}`. Si el cambio es compatible, corregí "
        "`info.version` a la siguiente MENOR en lugar de anunciar una rotura "
        "que no existe."
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


def _exigir_credencial_donde_no_se_pedia(doc: dict) -> None:
    """Exactamente lo que hizo el salto a 2.0.0, sobre una operación pública.

    Se elige `GET /v1/menu/items/{item_id}` y no una del panel porque las del
    panel **ya** exigen sesión en el contrato vigente: mutarlas no cambiaría
    nada y `mutar` omitiría el caso, que es la forma más silenciosa de que una
    prueba deje de probar.
    """
    operacion = doc["paths"]["/v1/menu/items/{item_id}"]["get"]
    if "security" in operacion:
        raise ValueError("esa operación ya exige credencial")
    operacion["security"] = [{"SesionDeMostrador": []}]


def _cambiar_el_tipo_de_credencial(doc: dict) -> None:
    """Quien tiene la credencial del contrato viejo se queda fuera igual."""
    operacion = doc["paths"]["/v1/pedidos"]["get"]
    if operacion.get("security") == [{"FirmaPasarela": []}]:
        raise ValueError("ya exige esa credencial")
    operacion["security"] = [{"FirmaPasarela": []}]


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
    pytest.param(_exigir_credencial_donde_no_se_pedia, "I-12",
                 id="I-12 · una operación pública pasa a exigir credencial"),
    pytest.param(_cambiar_el_tipo_de_credencial, "I-12",
                 id="I-12 · cambia el tipo de credencial exigida"),
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


def _dejar_de_exigir_credencial(doc: dict) -> None:
    """Abrir una operación cerrada no rompe a nadie.

    Quien venía mandando el `Authorization` sigue entrando: una credencial que
    ya no se pide tampoco molesta. Está aquí para que I-12 no se convierta en
    «todo lo que toque `security` es incompatible», que bloquearía la única
    dirección en la que este cambio es inofensivo.
    """
    operacion = doc["paths"]["/v1/pedidos"]["get"]
    if "security" not in operacion:
        raise ValueError("esa operación ya es pública")
    del operacion["security"]


def _quitar_valor_de_enum_de_respuesta(doc: dict) -> None:
    doc["components"]["schemas"]["EstadoPedido"]["enum"].remove("cancelado")


EVOLUCIONES = [
    pytest.param(_anadir_operacion, id="se añade un endpoint"),
    pytest.param(_anadir_campo_opcional_a_peticion, id="se añade un campo opcional a una petición"),
    pytest.param(_anadir_campo_a_respuesta, id="se añade un campo a una respuesta"),
    pytest.param(_relajar_una_restriccion, id="se relaja una restricción de petición"),
    pytest.param(_quitar_valor_de_enum_de_respuesta, id="se quita un valor de un enum de respuesta"),
    pytest.param(_dejar_de_exigir_credencial, id="se deja de exigir una credencial"),
]


@pytest.mark.parametrize("mutacion", EVOLUCIONES)
def test_la_evolucion_compatible_no_se_bloquea(contrato, mutacion):
    """Un detector que marca todo como roto obliga a ignorarlo, y entonces no sirve.

    Estos seis cambios son precisamente los que la política permite hacer sin
    subir la versión mayor.
    """
    rotos = incompatibles(comparar(contrato, mutar(contrato, mutacion)))

    assert not rotos, (
        f"`{mutacion.__name__}` es un cambio compatible según la política §2, "
        "pero el comparador lo marcó como rotura:\n"
        + "\n".join(str(c) for c in rotos)
    )


def test_la_linea_base_congelada_existe_y_declara_su_version(contrato):
    """El historial es la referencia de la promesa: sin él no hay contra qué medir.

    Comprueba además que el archivo congelado declara **por dentro** la versión
    que su nombre anuncia. Un `openapi-2.0.0.yaml` que diga `1.2.0` adentro
    convertiría toda comparación posterior en una medición contra la regla
    equivocada, y lo haría en silencio.
    """
    base = linea_base_de(contrato)

    assert base.exists(), (
        f"Falta la versión congelada {base.name}. Cada release publicada se "
        "congela en docs/api/historial/ y no se edita nunca más."
    )

    declarada = cargar(base)["info"]["version"]
    esperada = f"{mayor_de(contrato['info']['version'])}.0.0"
    assert declarada == esperada, (
        f"`{base.name}` declara adentro la versión {declarada!r} y su nombre "
        f"promete {esperada!r}."
    )
