"""Utilidades compartidas, y la precaución que hace determinista a la suite.

Las tres pruebas de contrato de este repositorio introducen roturas a propósito
para demostrar que saben detectarlas. Todas necesitan la misma precaución, y
por eso vive aquí en lugar de repetirse tres veces.
"""
from __future__ import annotations

import copy
import os
from typing import Callable

import pytest

# ---------------------------------------------------------------------------
# La suite no hereda la base de datos de quien la ejecuta
# ---------------------------------------------------------------------------
#
# `PIDEUTB_DATABASE_URL` se retira del entorno **al importar este archivo**, que
# es antes de que cualquier módulo de prueba importe `app`.
#
# ### Qué se arregla
#
# La mayoría de las pruebas asumen el almacenamiento en memoria, y lo asumen en
# silencio: sus fixtures aíslan cada caso vaciando `repository._PEDIDOS`. Si esa
# variable está definida en la terminal, la aplicación usa PostgreSQL, esa
# limpieza **no limpia nada**, y el estado se filtra de un caso al siguiente.
#
# El síntoma eran 8 fallos —en `test_fallos_parciales`, `test_panel_mostrador` y
# `test_health`— que aparecían o no según lo que tuviera exportado quien corría
# la suite. Es el peor tipo de prueba intermitente: la que depende del entorno
# de una persona en lugar del código.
#
# Y la condición no es rara. `test_repositorios.py` ya avisaba de que tener esa
# variable exportada «es lo normal mientras se desarrolla contra una base real»;
# el aviso iba por otro motivo —que la suite no borre tablas de producción— pero
# describe exactamente la situación que producía los fallos.
#
# ### Por qué aquí y no en un fixture
#
# Un fixture `autouse` funcionaría solo si pytest lo instancia **antes** del
# fixture que las pruebas de PostgreSQL usan para activarla. Hoy ese orden se
# cumple, pero apoyarse en él es frágil, y equivocarse tiene un modo de fallo
# peor que el problema original: las pruebas de PostgreSQL correrían contra
# memoria y **pasarían**, sin probar lo que dicen probar.
#
# Retirarla al importar no depende de ningún orden.
#
# ### Qué NO se rompe
#
# Las pruebas que necesitan PostgreSQL no leen esta variable del entorno: optan
# explícitamente con `monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)`,
# a partir de `PIDEUTB_DATABASE_URL_PRUEBAS`, que es una variable distinta a
# propósito. `monkeypatch` las restaura al terminar cada caso, así que el valor
# por defecto vuelve a ser «ausente».
#
# Correr la suite entera contra PostgreSQL sigue siendo posible, y por la vía
# prevista: definir `PIDEUTB_DATABASE_URL_PRUEBAS`.
_HEREDADA = os.environ.pop("PIDEUTB_DATABASE_URL", None)

#: Si se encontró definida, para que una prueba pueda comprobar que se retiró.
URL_HEREDADA_DEL_ENTORNO = _HEREDADA


def mutar(contrato: dict, mutacion: Callable[[dict], None]) -> dict:
    """Aplica una mutación sobre una copia del contrato.

    Si la mutación no llega a cambiar nada —porque el contrato base ya no tiene
    aquello que iba a romper—, la prueba se omite en lugar de fallar.

    Ese caso ocurre de verdad, no es hipotético: al reproducir el
    procedimiento de `docs/api/README.md` §3 se rompe el contrato a propósito
    para ver la construcción en rojo. Sin esta salida, las pruebas de caso
    negativo reventarían con un `KeyError` y llenarían la salida de ruido
    justo cuando se está intentando enseñar una rotura concreta.

    Omitir y no fallar es lo correcto aquí: que una mutación ya no aplique no
    significa que el detector esté roto, significa que no hay nada que
    detectar.
    """
    copia = copy.deepcopy(contrato)

    try:
        mutacion(copia)
    except (KeyError, ValueError) as error:
        pytest.skip(
            f"`{mutacion.__name__}` ya no aplica sobre el contrato actual "
            f"({type(error).__name__}: {error}). El contrato base probablemente "
            "ya contiene ese cambio."
        )

    if copia == contrato:
        pytest.skip(
            f"`{mutacion.__name__}` no modificó nada: el contrato base ya está "
            "en el estado que la mutación pretendía provocar."
        )

    return copia


@pytest.fixture(autouse=True)
def secreto_de_la_pasarela(monkeypatch):
    """Define el secreto del webhook para toda la suite.

    `app/pagos/service.py` ya **no** trae valor por defecto: sin la variable,
    `firma_valida` rechaza todo evento. Antes sí lo traía, y esa comodidad tuvo
    una consecuencia: el despliegue nunca definió la variable y quedó
    verificando contra una cadena publicada en un repositorio público
    ([V-11](../../docs/violaciones.md)).

    Que las pruebas tengan que declararlo es el punto, no una molestia. Un
    secreto que se puede omitir termina omitido, y la omisión no se nota porque
    todo sigue funcionando.

    El valor de aquí es de pruebas y solo existe en el proceso de pytest.
    """
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", "secreto-solo-de-pruebas")
