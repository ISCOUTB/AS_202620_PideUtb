"""Pruebas del corte vertical: POST /pedidos.

Cubren el escenario ESC-01 (arc42 §10.2 / fila ESC-01 de docs/aspectos.md):
un usuario nuevo debe poder crear un pedido con un único request y recibir
un error claro si el ítem no existe o no está disponible.

Las pruebas de propiedad de datos entre contextos están en
`test_propiedad_datos.py`.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_crear_pedido_exitoso():
    respuesta = client.post("/v1/pedidos", json={"lineas": [{"item_id": 1, "cantidad": 2}]})

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["lineas"][0]["nombre_item"] == "Arepa de huevo"
    assert cuerpo["lineas"][0]["precio_unitario_centavos"] == 400000
    assert cuerpo["lineas"][0]["cantidad"] == 2
    assert cuerpo["total_centavos"] == 800000
    assert cuerpo["estado"] == "pendiente_pago"


def test_crear_pedido_item_no_encontrado():
    respuesta = client.post("/v1/pedidos", json={"lineas": [{"item_id": 999, "cantidad": 1}]})

    assert respuesta.status_code == 404


def test_crear_pedido_item_no_disponible():
    # item_id 3 (Empanada) está marcado como no disponible en el seed.
    respuesta = client.post("/v1/pedidos", json={"lineas": [{"item_id": 3, "cantidad": 1}]})

    assert respuesta.status_code == 409


# --------------------------------------------------------------------------
# V-13 · El pedido no se lee sin su token
#
# `GET /v1/pedidos/{id}` era público y devolvía `codigo_canje`, y los
# identificadores son secuenciales: cualquiera podía recorrerlos y cosechar los
# códigos de los pedidos pagados, que es lo que se presenta en el mostrador para
# llevarse la comida.
#
# Estas pruebas comprueban lo que **no** debe poder hacerse, que es justamente lo
# que ninguna comprobaba cuando la puerta estuvo abierta.
# --------------------------------------------------------------------------

def _crear() -> dict:
    respuesta = client.post(
        "/v1/pedidos", json={"lineas": [{"item_id": 1, "cantidad": 1}]}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_al_crear_el_pedido_se_entrega_un_token():
    creado = _crear()

    assert creado["token_consulta"], "sin él no habría forma de consultar el pedido"
    assert len(creado["token_consulta"]) >= 16


def test_dos_pedidos_no_comparten_token():
    """Si lo compartieran, cada uno podría leer el otro.

    Los dos pedidos se crean en líneas aparte y no dentro de la aserción:
    comparar `_crear()[...] != _crear()[...]` se lee como una tautología y solo
    deja de serlo porque la llamada tiene efectos. Quien lo lea no debería tener
    que deducir eso.
    """
    uno = _crear()
    otro = _crear()

    assert uno["pedido_id"] != otro["pedido_id"], "son dos pedidos distintos"
    assert uno["token_consulta"] != otro["token_consulta"]


def test_sin_token_no_se_puede_consultar_un_pedido():
    """**La prueba de V-13.** Es la petición exacta que cosechaba códigos."""
    creado = _crear()

    respuesta = client.get(f"/v1/pedidos/{creado['pedido_id']}")

    assert respuesta.status_code == 404
    assert "codigo_canje" not in respuesta.text


def test_con_el_token_de_otro_pedido_tampoco():
    """Tener un pedido no da acceso a los demás.

    Sin esto, la comprobación podría estar hecha contra «algún token válido» en
    vez de contra el de este pedido, y la puerta seguiría abierta para cualquiera
    que hiciera un pedido propio.
    """
    mio = _crear()
    ajeno = _crear()

    respuesta = client.get(
        f"/v1/pedidos/{ajeno['pedido_id']}",
        headers={"X-Token-Pedido": mio["token_consulta"]},
    )

    assert respuesta.status_code == 404


def test_con_su_token_el_pedido_se_consulta_entero():
    creado = _crear()

    cuerpo = client.get(
        f"/v1/pedidos/{creado['pedido_id']}",
        headers={"X-Token-Pedido": creado["token_consulta"]},
    ).json()

    assert cuerpo["pedido_id"] == creado["pedido_id"]
    assert cuerpo["estado"] == "pendiente_pago"
    assert cuerpo["lineas"][0]["nombre_item"] == "Arepa de huevo"


def test_la_consulta_no_devuelve_otra_vez_el_token():
    """Devolverlo lo volvería inútil.

    Bastaría acertar un identificador una vez —con token o sin él, si algún día
    la respuesta cambiara— para tenerlo para siempre. Se entrega al crear y no
    se repite.
    """
    creado = _crear()

    cuerpo = client.get(
        f"/v1/pedidos/{creado['pedido_id']}",
        headers={"X-Token-Pedido": creado["token_consulta"]},
    ).json()

    assert cuerpo["token_consulta"] is None


def test_un_token_que_no_existe_da_404_y_no_otra_cosa():
    """El mismo código que un pedido inexistente.

    Un `403` diría «este pedido existe, solo te falta el token», que es
    exactamente lo que no hay que confirmarle a quien está probando números. Es
    el criterio que I-1 ya fijó para la cola del mostrador.
    """
    creado = _crear()

    con_token_falso = client.get(
        f"/v1/pedidos/{creado['pedido_id']}",
        headers={"X-Token-Pedido": "este-token-no-existe-en-ninguna-parte"},
    )
    inexistente = client.get(
        "/v1/pedidos/999999",
        headers={"X-Token-Pedido": creado["token_consulta"]},
    )

    assert con_token_falso.status_code == inexistente.status_code == 404
