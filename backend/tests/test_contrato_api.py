"""Prueba de contrato · conformidad entre el contrato y la implementación.

`test_compatibilidad_contrato.py` compara dos versiones del contrato entre sí.
Esta compara el contrato con **el código que dice cumplirlo**, que es una
pregunta distinta: un contrato puede ser perfectamente compatible con su
versión anterior y aun así no describir lo que la aplicación hace.

Es la diferencia que la semana señala entre prueba de contrato y prueba de
integración: aquí no se comprueba que el sistema *funcione*, se comprueba que
**sigue cumpliendo lo pactado**. Una aplicación que devuelve todos los campos
correctos más uno que nunca declaró supera cualquier prueba de integración y
falla esta, con razón: el consumidor no puede depender de lo que no está
escrito, y el proveedor no puede retirar lo que ya emite sin avisar.

La comparación es **bidireccional** a propósito:

- Lo que el contrato promete y la app no implementa → el consumidor falla al
  usarlo.
- Lo que la app expone y el contrato no declara → API no documentada, que
  alguien acabará usando y que nadie podrá retirar sin romperlo.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable

import pytest

from app.main import app
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pedidos.contracts import EstadoPedido
from scripts.comparar_contratos import cargar, operaciones, resolver
from tests.conftest import mutar

RAIZ = Path(__file__).resolve().parents[2]
CONTRATO = RAIZ / "docs" / "api" / "openapi.yaml"
CONTRATO_EVENTOS = RAIZ / "docs" / "api" / "asyncapi.yaml"

PROFUNDIDAD_MAXIMA = 12


@pytest.fixture(scope="module")
def contrato() -> dict:
    return cargar(CONTRATO)


@pytest.fixture(scope="module")
def generado() -> dict:
    """Lo que la aplicación declara de sí misma en tiempo de ejecución."""
    return app.openapi()


# --------------------------------------------------------------------------
# Normalización
#
# Las dos partes describen lo mismo con sintaxis distinta: el contrato está
# escrito a mano en OpenAPI 3.1 y el otro lado lo genera Pydantic. Comparar
# los diccionarios en crudo produciría cientos de diferencias falsas por
# `title`, `description` y azúcar sintáctica. Se comparan solo los tres rasgos
# de los que un consumidor puede depender: qué campos hay, cuáles están
# garantizados y qué valores admiten.
# --------------------------------------------------------------------------

def _tipos(documento: dict, esquema: dict, profundidad: int = 0) -> set[str]:
    """Conjunto de tipos, unificando `type: [a, b]` y `anyOf: [{...}, {...}]`."""
    if profundidad > PROFUNDIDAD_MAXIMA:
        return set()

    tipos: set[str] = set()
    tipo = esquema.get("type")
    if isinstance(tipo, list):
        tipos |= {str(t) for t in tipo}
    elif tipo:
        tipos.add(str(tipo))

    for clave in ("anyOf", "oneOf"):
        for sub in esquema.get(clave) or []:
            tipos |= _tipos(documento, resolver(documento, sub), profundidad + 1)

    return tipos


def _valores(esquema: dict) -> set[str] | None:
    """Valores admitidos, unificando `enum: [x]` y `const: x`.

    Pydantic emite `const` para un `Literal` de un solo valor donde el contrato
    escribe `enum` de un elemento. Significan lo mismo.
    """
    if "enum" in esquema:
        return {repr(v) for v in esquema["enum"]}
    if "const" in esquema:
        return {repr(esquema["const"])}
    return None


def _comparar_esquemas(
    doc_esperado: dict,
    doc_real: dict,
    esperado: Any,
    real: Any,
    ubicacion: str,
    divergencias: list[str],
    profundidad: int = 0,
) -> None:
    if profundidad > PROFUNDIDAD_MAXIMA:
        return

    esperado = resolver(doc_esperado, esperado)
    real = resolver(doc_real, real)
    if not isinstance(esperado, dict) or not isinstance(real, dict):
        return

    tipos_esperados = _tipos(doc_esperado, esperado)
    tipos_reales = _tipos(doc_real, real)
    if tipos_esperados and tipos_reales and tipos_esperados != tipos_reales:
        divergencias.append(
            f"{ubicacion}: el contrato declara el tipo {sorted(tipos_esperados)} "
            f"y la aplicación emite {sorted(tipos_reales)}"
        )

    valores_esperados, valores_reales = _valores(esperado), _valores(real)
    if valores_esperados is not None and valores_reales is not None:
        if valores_esperados != valores_reales:
            divergencias.append(
                f"{ubicacion}: el contrato admite {sorted(valores_esperados)} "
                f"y la aplicación {sorted(valores_reales)}"
            )

    propiedades_esperadas = esperado.get("properties") or {}
    propiedades_reales = real.get("properties") or {}

    if propiedades_esperadas or propiedades_reales:
        faltan = set(propiedades_esperadas) - set(propiedades_reales)
        sobran = set(propiedades_reales) - set(propiedades_esperadas)

        for nombre in sorted(faltan):
            divergencias.append(
                f"{ubicacion}.{nombre}: el contrato lo declara y la aplicación no lo emite"
            )
        for nombre in sorted(sobran):
            divergencias.append(
                f"{ubicacion}.{nombre}: la aplicación lo emite sin declararlo en el contrato"
            )

        requeridos_esperados = set(esperado.get("required") or [])
        requeridos_reales = set(real.get("required") or [])
        if requeridos_esperados != requeridos_reales:
            divergencias.append(
                f"{ubicacion}: el contrato garantiza {sorted(requeridos_esperados)} "
                f"y la aplicación garantiza {sorted(requeridos_reales)}"
            )

        for nombre in sorted(set(propiedades_esperadas) & set(propiedades_reales)):
            _comparar_esquemas(
                doc_esperado, doc_real,
                propiedades_esperadas[nombre], propiedades_reales[nombre],
                f"{ubicacion}.{nombre}", divergencias, profundidad + 1,
            )

    if "items" in esperado and "items" in real:
        _comparar_esquemas(
            doc_esperado, doc_real, esperado["items"], real["items"],
            f"{ubicacion}[]", divergencias, profundidad + 1,
        )


def _esquema_de_cuerpo(documento: dict, operacion: dict) -> dict | None:
    cuerpo = resolver(documento, operacion.get("requestBody") or {})
    medio = ((cuerpo or {}).get("content") or {}).get("application/json")
    return resolver(documento, medio["schema"]) if medio and "schema" in medio else None


def _esquemas_de_respuesta(documento: dict, operacion: dict) -> dict[str, dict | None]:
    respuestas: dict[str, dict | None] = {}
    for codigo, respuesta in (operacion.get("responses") or {}).items():
        respuesta = resolver(documento, respuesta)
        medio = ((respuesta or {}).get("content") or {}).get("application/json")
        respuestas[str(codigo)] = (
            resolver(documento, medio["schema"]) if medio and "schema" in medio else None
        )
    return respuestas


def divergencias(contrato: dict, generado: dict) -> list[str]:
    """Todo aquello en lo que el contrato y la aplicación no dicen lo mismo."""
    encontradas: list[str] = []

    version_contrato = contrato.get("info", {}).get("version")
    version_app = generado.get("info", {}).get("version")
    if version_contrato != version_app:
        encontradas.append(
            f"versión: el contrato declara {version_contrato!r} y la aplicación "
            f"anuncia {version_app!r}. Un despliegue que anuncia una versión "
            "distinta de la que cumple engaña a quien la consume."
        )

    del_contrato = operaciones(contrato)
    de_la_app = operaciones(generado)

    for ruta, metodo in sorted(set(del_contrato) - set(de_la_app)):
        encontradas.append(
            f"{metodo.upper()} {ruta}: el contrato la promete y la aplicación no la implementa"
        )
    for ruta, metodo in sorted(set(de_la_app) - set(del_contrato)):
        encontradas.append(
            f"{metodo.upper()} {ruta}: la aplicación la expone sin declararla en el contrato"
        )

    for clave in sorted(set(del_contrato) & set(de_la_app)):
        etiqueta = f"{clave[1].upper()} {clave[0]}"
        operacion_contrato, operacion_app = del_contrato[clave], de_la_app[clave]

        cuerpo_contrato = _esquema_de_cuerpo(contrato, operacion_contrato)
        cuerpo_app = _esquema_de_cuerpo(generado, operacion_app)
        if (cuerpo_contrato is None) != (cuerpo_app is None):
            encontradas.append(
                f"{etiqueta}: solo "
                f"{'el contrato' if cuerpo_app is None else 'la aplicación'} "
                "declara un cuerpo de petición"
            )
        elif cuerpo_contrato is not None and cuerpo_app is not None:
            _comparar_esquemas(
                contrato, generado, cuerpo_contrato, cuerpo_app,
                f"{etiqueta} · petición", encontradas,
            )

        respuestas_contrato = _esquemas_de_respuesta(contrato, operacion_contrato)
        respuestas_app = _esquemas_de_respuesta(generado, operacion_app)

        for codigo in sorted(set(respuestas_contrato) - set(respuestas_app)):
            encontradas.append(
                f"{etiqueta} · {codigo}: el contrato declara este código y la aplicación no"
            )
        for codigo in sorted(set(respuestas_app) - set(respuestas_contrato)):
            encontradas.append(
                f"{etiqueta} · {codigo}: la aplicación puede responderlo y el contrato no lo declara"
            )

        for codigo in sorted(set(respuestas_contrato) & set(respuestas_app)):
            esquema_contrato, esquema_app = respuestas_contrato[codigo], respuestas_app[codigo]
            if esquema_contrato is None or esquema_app is None:
                continue
            _comparar_esquemas(
                contrato, generado, esquema_contrato, esquema_app,
                f"{etiqueta} · {codigo}", encontradas,
            )

    return encontradas


# --------------------------------------------------------------------------
# La prueba que corre en el pipeline
# --------------------------------------------------------------------------

def test_la_aplicacion_cumple_el_contrato_publicado(contrato, generado):
    """El código y el contrato describen exactamente la misma API.

    Si esta prueba falla, una de dos cosas ocurrió: se cambió el código sin
    actualizar el contrato, o se actualizó el contrato sin implementarlo. Las
    dos son roturas silenciosas para quien consume la API — que es precisamente
    lo que la entrega busca hacer imposible.
    """
    encontradas = divergencias(contrato, generado)

    assert not encontradas, (
        f"La aplicación no cumple `docs/api/openapi.yaml` ({len(encontradas)} "
        "divergencia(s)).\n\nEl contrato es la fuente única de verdad: si el "
        "cambio es deliberado, actualizá el contrato y subí la versión según "
        "`docs/api/politica-versionado.md`.\n\n"
        + "\n".join(f"  - {d}" for d in encontradas)
    )


# --------------------------------------------------------------------------
# Casos negativos: la conformidad debe detectar la deriva
# --------------------------------------------------------------------------

def _prometer_un_campo_que_no_existe(doc: dict) -> None:
    pedido = doc["components"]["schemas"]["Pedido"]
    pedido["properties"]["tiempo_estimado_min"] = {"type": "integer"}
    pedido["required"].append("tiempo_estimado_min")


def _prometer_una_operacion_que_no_existe(doc: dict) -> None:
    doc["paths"]["/v1/pedidos/{pedido_id}/cancelacion"] = {
        "post": {"operationId": "cancelarPedido", "responses": {"200": {"description": "ok"}}}
    }


def _dejar_de_declarar_una_operacion(doc: dict) -> None:
    del doc["paths"]["/v1/pagos/eventos"]


def _declarar_otro_tipo_para_el_dinero(doc: dict) -> None:
    doc["components"]["schemas"]["Pedido"]["properties"]["total_centavos"]["type"] = "string"


def _olvidar_un_valor_del_enum(doc: dict) -> None:
    doc["components"]["schemas"]["EstadoPedido"]["enum"].remove("cancelado")


def _dejar_de_declarar_un_codigo_de_error(doc: dict) -> None:
    del doc["paths"]["/v1/pedidos"]["post"]["responses"]["409"]


def _cambiar_la_version_sin_desplegar(doc: dict) -> None:
    doc["info"]["version"] = "2.0.0"


DERIVAS: list[Callable[[dict], None]] = [
    _prometer_un_campo_que_no_existe,
    _prometer_una_operacion_que_no_existe,
    _dejar_de_declarar_una_operacion,
    _declarar_otro_tipo_para_el_dinero,
    _olvidar_un_valor_del_enum,
    _dejar_de_declarar_un_codigo_de_error,
    _cambiar_la_version_sin_desplegar,
]


@pytest.mark.parametrize("deriva", DERIVAS, ids=lambda f: f.__name__.strip("_"))
def test_la_conformidad_detecta_la_deriva(contrato, generado, deriva):
    """Sin estos casos, la prueba anterior podría estar comparando nada.

    Se modifica el contrato —no el código, que no se puede mutar sin reiniciar
    la aplicación— y se exige que la divergencia salga a la luz. El efecto es
    idéntico: contrato y código dejan de decir lo mismo.
    """
    mutado = mutar(contrato, deriva)

    assert divergencias(mutado, generado), (
        f"La comprobación de conformidad NO detectó la deriva introducida por "
        f"`{deriva.__name__}`. Una prueba de contrato que no falla cuando el "
        "código y el contrato se separan no está comprobando nada."
    )


# --------------------------------------------------------------------------
# Coherencia entre las tres fuentes: contrato, código y contrato de eventos
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre_en_contrato, enum_python",
    [
        ("EstadoPedido", EstadoPedido),
        ("EstadoPago", EstadoPago),
        ("MetodoDePago", MetodoDePago),
    ],
)
def test_los_enum_del_contrato_coinciden_con_los_del_codigo(
    contrato, nombre_en_contrato, enum_python
):
    """Compara contra el `Enum` de Python, no contra el esquema generado.

    El esquema generado deriva del `Enum`, así que compararlos entre sí no
    probaría gran cosa. Lo que importa es que la lista escrita a mano en el
    contrato siga coincidiendo con la fuente de verdad del código: es ahí donde
    alguien añade un estado nuevo y se olvida del contrato.
    """
    del_contrato = set(contrato["components"]["schemas"][nombre_en_contrato]["enum"])
    del_codigo = {miembro.value for miembro in enum_python}

    assert del_contrato == del_codigo, (
        f"`{nombre_en_contrato}` no coincide.\n"
        f"  solo en el contrato: {sorted(del_contrato - del_codigo)}\n"
        f"  solo en el código  : {sorted(del_codigo - del_contrato)}\n"
        "Cambiar el conjunto de valores de un enum de respuesta es un cambio "
        "incompatible (docs/api/politica-versionado.md §3.1)."
    )


def test_el_evento_de_pago_se_describe_igual_en_openapi_y_en_asyncapi(contrato):
    """El mismo mensaje está descrito en dos archivos y deben coincidir.

    `openapi.yaml` lo describe como cuerpo HTTP y `asyncapi.yaml` como mensaje
    de un canal. Se duplica a propósito, para que cada contrato pueda validarse
    por separado en el pipeline; el precio de esa duplicación es esta prueba,
    que impide que se separen sin que nadie lo note.
    """
    eventos = cargar(CONTRATO_EVENTOS)
    encontradas: list[str] = []

    _comparar_esquemas(
        contrato, eventos,
        contrato["components"]["schemas"]["EventoPago"],
        eventos["components"]["schemas"]["EventoPago"],
        "EventoPago", encontradas,
    )

    assert not encontradas, (
        "`EventoPago` difiere entre openapi.yaml y asyncapi.yaml:\n"
        + "\n".join(f"  - {d}" for d in encontradas)
    )
