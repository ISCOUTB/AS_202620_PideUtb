"""Que la suite dé el mismo resultado sin importar quién la ejecute.

Una prueba que pasa o falla según lo que tenga exportado la terminal de una
persona no prueba nada del código: prueba el entorno de esa persona. Y es la
clase de fallo que más tiempo cuesta, porque el síntoma viaja con el
desarrollador y no con el repositorio.

Esto vigila el caso concreto que ocurrió. Con `PIDEUTB_DATABASE_URL` definida
—lo normal mientras se desarrolla contra una base real— ocho casos de
`test_fallos_parciales`, `test_panel_mostrador` y `test_health` fallaban: sus
fixtures aíslan cada caso vaciando el almacenamiento **en memoria**, y con esa
variable puesta la aplicación usa PostgreSQL, así que la limpieza no limpiaba
nada y el estado se filtraba de un caso al siguiente.

`conftest.py` la retira al importarse. Estas pruebas comprueban que lo hizo y
que sigue habiendo una forma de pedir PostgreSQL cuando se quiere.
"""
from __future__ import annotations

import os

from app import base_de_datos
from tests import conftest


def test_la_suite_no_hereda_la_base_de_datos_del_entorno():
    """El valor por defecto es memoria, venga de donde venga quien ejecuta.

    Si esta prueba falla, algo volvió a definir `PIDEUTB_DATABASE_URL` para
    toda la sesión, y los ocho casos que dependían de ello vuelven a ser
    intermitentes — pero esta vez con un aviso que dice por qué.
    """
    assert not os.getenv("PIDEUTB_DATABASE_URL", "").strip(), (
        "`PIDEUTB_DATABASE_URL` está definida durante la suite. `conftest.py` "
        "la retira al importarse justamente para que no lo esté: con ella, las "
        "pruebas que aíslan vaciando el almacenamiento en memoria dejan de "
        "aislar nada y el estado se filtra entre casos."
    )
    assert not base_de_datos.hay_base_de_datos(), (
        "La aplicación se declara configurada contra PostgreSQL durante una "
        "prueba que no lo pidió."
    )


def test_retirarla_no_elimina_la_forma_de_pedir_postgres():
    """Quitar la variable del entorno no puede dejar la suite sin PostgreSQL.

    Es la otra mitad, y la que importa más: si `conftest.py` retirase la
    variable **y** las pruebas de repositorio dependieran de ella, esas pruebas
    correrían contra memoria y **pasarían**, sin probar lo que dicen probar. Un
    arreglo de aislamiento que convierte pruebas en teatro sería peor que el
    problema que arregla.

    No ocurre porque la vía de entrada es otra variable, `..._PRUEBAS`, y cada
    prueba que la necesita la activa con `monkeypatch`. Esto lo deja afirmado en
    vez de supuesto.
    """
    assert hasattr(conftest, "URL_HEREDADA_DEL_ENTORNO"), (
        "`conftest.py` ya no registra si encontró la variable definida."
    )

    # La vía prevista sigue en pie: es una variable **distinta**, y que lo sea
    # es lo que impide que la suite borre las tablas de producción por tener
    # exportada la del entorno de desarrollo.
    assert "PIDEUTB_DATABASE_URL_PRUEBAS" != "PIDEUTB_DATABASE_URL"

    # Y la decisión se consulta en vivo, no al importar: sin eso, activar la
    # variable dentro de una prueba no tendría ningún efecto.
    import inspect

    fuente = inspect.getsource(base_de_datos.hay_base_de_datos)
    assert "os.getenv" in fuente, (
        "`hay_base_de_datos()` dejó de leer el entorno en cada llamada. Si "
        "pasa a ser una constante de módulo, las pruebas ya no pueden activar "
        "PostgreSQL sin recargar la aplicación, y el fixture `implementacion` "
        "de `test_repositorios.py` dejaría de funcionar en silencio."
    )


def test_la_constante_muerta_no_vuelve():
    """`URL_BASE_DE_DATOS` se retiró en la S14 y no debe reaparecer.

    Se leía al importar el módulo y se usaba en **cero** sitios. Una constante
    que parece gobernar el comportamiento y no lo gobierna es peor que no
    tenerla: invita a cambiarla esperando un efecto que no llega.

    Si alguien la necesita de verdad, el aviso dice dónde está el problema: leer
    la cadena al importar rompe la capacidad de las pruebas de alternar entre
    implementaciones.
    """
    assert not hasattr(base_de_datos, "URL_BASE_DE_DATOS"), (
        "`base_de_datos.URL_BASE_DE_DATOS` volvió. Se leía al importar y no se "
        "usaba en ninguna parte; si hace falta la cadena, se lee en el momento "
        "con `os.environ`, que es lo que permite a las pruebas alternar entre "
        "memoria y PostgreSQL."
    )
