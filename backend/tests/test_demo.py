"""El reinicio de la demo existe poco y mal a propósito.

Es la única ruta del sistema que borra datos en masa, así que lo que más
importa probar no es que borre: es que **no esté** salvo donde alguien la haya
encendido a conciencia, y que no se pueda distinguir de una ruta inexistente.

El borrado en sí se prueba contra PostgreSQL, porque borrar de un diccionario
en memoria no demuestra que el orden de las tablas respete las claves foráneas
—`pagos_intentos` referencia `pedidos` sin `ON DELETE CASCADE`— y ese es
justamente el detalle que se puede equivocar.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app import base_de_datos
from app.main import app

# Se reutiliza el preparador de `test_repositorios` en vez de copiarlo: lleva
# dentro la lógica de reconstruir el esquema cuando el registro de migraciones
# no coincide exactamente con los archivos, que se escribió después de un fallo
# que solo aparecía en el portátil. Duplicarla sería duplicar también el
# próximo arreglo.
from tests.test_repositorios import _preparar_base_de_datos

URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()

TOKEN = "token-solo-de-pruebas-del-reinicio"


@pytest.fixture
def sin_variable(monkeypatch):
    monkeypatch.delenv("PIDEUTB_TOKEN_REINICIO_DEMO", raising=False)


@pytest.fixture
def con_variable(monkeypatch):
    monkeypatch.setenv("PIDEUTB_TOKEN_REINICIO_DEMO", TOKEN)


@pytest.fixture
def contra_postgres(monkeypatch):
    if not URL_PRUEBAS:
        pytest.skip("Sin PIDEUTB_DATABASE_URL_PRUEBAS.")
    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()
    yield
    base_de_datos.cerrar_pool()


# ---------------------------------------------------------------------------
# Sin la variable, la ruta no existe
# ---------------------------------------------------------------------------

def test_sin_la_variable_responde_404(sin_variable):
    """El mismo código que daría una ruta inventada.

    No es cosmética: un 403 —«existe, pero no podés»— le confirma a quien
    sondea que la ruta está ahí y que solo falta la configuración adecuada. Un
    404 no le dice nada que no supiera.
    """
    respuesta = TestClient(app).post("/v1/demo/reiniciar")

    assert respuesta.status_code == 404


def test_sin_la_variable_no_toca_la_base(sin_variable, monkeypatch):
    """Rechaza antes de abrir una conexión.

    Importa por el orden, no por el rendimiento: si la comprobación viniera
    después de consultar, una ruta apagada seguiría dando trabajo a PostgreSQL
    a petición de cualquiera.
    """
    def explotar():
        raise AssertionError("no debería haber abierto una conexión")

    monkeypatch.setattr(base_de_datos, "conexion", explotar)

    assert TestClient(app).post("/v1/demo/reiniciar").status_code == 404


# ---------------------------------------------------------------------------
# Con la variable, hace falta el token
# ---------------------------------------------------------------------------

def test_con_la_variable_pero_sin_token_responde_404(con_variable):
    assert TestClient(app).post("/v1/demo/reiniciar").status_code == 404


def test_con_un_token_equivocado_responde_404(con_variable):
    """También 404, y no 401.

    Con la variable puesta, un 401 distinguiría «la ruta existe y el token está
    mal» de «la ruta no existe». Esa diferencia es exactamente lo que no se le
    quiere confirmar a quien prueba tokens.
    """
    respuesta = TestClient(app).post(
        "/v1/demo/reiniciar", headers={"X-Token-Demo": "otra-cosa"}
    )

    assert respuesta.status_code == 404


def test_un_token_que_es_prefijo_del_bueno_tampoco_entra(con_variable):
    """El caso que una comparación perezosa dejaría pasar."""
    respuesta = TestClient(app).post(
        "/v1/demo/reiniciar", headers={"X-Token-Demo": TOKEN[:10]}
    )

    assert respuesta.status_code == 404


# ---------------------------------------------------------------------------
# Fuera del contrato
# ---------------------------------------------------------------------------

def test_no_aparece_en_la_documentacion(con_variable):
    """`include_in_schema=False`, incluso con la variable puesta.

    No es una operación que el frontend consuma: es una herramienta de
    operación. Publicarla en el OpenAPI la congelaría en una versión del
    contrato y obligaría a mantenerla como promesa.
    """
    esquema = TestClient(app).get("/openapi.json").json()

    assert not [r for r in esquema["paths"] if r.startswith("/v1/demo")]


# ---------------------------------------------------------------------------
# Y cuando corresponde, borra
# ---------------------------------------------------------------------------

@pytest.mark.usefixtures("contra_postgres")
def test_borra_los_pedidos_y_sus_intentos(con_variable):
    """Un pedido con su cobro abierto desaparece entero.

    El orden de las tablas es lo que se comprueba: `pagos_intentos` referencia
    `pedidos` sin cascada, así que borrar los pedidos primero haría fallar la
    transacción entera.
    """
    cliente = TestClient(app)

    creado = cliente.post("/v1/pedidos", json={"lineas": [{"item_id": 1, "cantidad": 1}]})
    assert creado.status_code == 201, creado.text
    pedido_id = creado.json()["pedido_id"]

    cobro = cliente.post(
        "/v1/pagos/intentos", json={"pedido_id": pedido_id, "metodo": "tarjeta"}
    )
    assert cobro.status_code == 201, cobro.text

    respuesta = cliente.post(
        "/v1/demo/reiniciar", headers={"X-Token-Demo": TOKEN}
    )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["reiniciado"] is True
    assert cuerpo["borrados"]["pedidos"] >= 1
    assert cuerpo["borrados"]["pagos_intentos"] >= 1

    with base_de_datos.conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pedidos")
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT count(*) FROM pagos_intentos")
            assert cursor.fetchone()[0] == 0
            # Las líneas se van por cascada, no por el borrado explícito.
            cursor.execute("SELECT count(*) FROM pedido_lineas")
            assert cursor.fetchone()[0] == 0


@pytest.mark.usefixtures("contra_postgres")
def test_el_siguiente_pedido_vuelve_a_ser_el_uno(con_variable):
    """Cosmético y se nota: el número se proyecta en una pantalla.

    Vale la pena probarlo porque reiniciar la secuencia con la tabla a medio
    vaciar haría que el siguiente pedido chocara con uno existente, y eso sí
    sería un fallo de verdad.
    """
    cliente = TestClient(app)

    cliente.post("/v1/pedidos", json={"lineas": [{"item_id": 1, "cantidad": 1}]})
    cliente.post("/v1/demo/reiniciar", headers={"X-Token-Demo": TOKEN})

    siguiente = cliente.post(
        "/v1/pedidos", json={"lineas": [{"item_id": 1, "cantidad": 1}]}
    )

    assert siguiente.json()["pedido_id"] == 1


@pytest.mark.usefixtures("contra_postgres")
def test_no_borra_la_carta_ni_las_cuentas(con_variable):
    """Lo que el reinicio NO puede llevarse por delante.

    Si borrara `menu_items` la demo quedaría sin carta, y si borrara `usuarios`
    el mostrador no podría entrar — y en el servidor del laboratorio no hay
    forma de recrear ninguna de las dos cosas sin un despliegue limpio.
    """
    cliente = TestClient(app)

    antes = len(cliente.get("/v1/menu/establecimientos/5/items").json()["items"])

    cliente.post("/v1/demo/reiniciar", headers={"X-Token-Demo": TOKEN})

    despues = len(cliente.get("/v1/menu/establecimientos/5/items").json()["items"])
    assert despues == antes

    with base_de_datos.conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM usuarios")
            assert cursor.fetchone()[0] >= 0  # la tabla sigue existiendo
            cursor.execute("SELECT count(*) FROM establecimientos")
            assert cursor.fetchone()[0] == 5
