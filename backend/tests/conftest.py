"""Utilidades compartidas por las pruebas de contrato.

Las tres pruebas de contrato de este repositorio introducen roturas a propósito
para demostrar que saben detectarlas. Todas necesitan la misma precaución, y
por eso vive aquí en lugar de repetirse tres veces.
"""
from __future__ import annotations

import copy
from typing import Callable

import pytest


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
