"""Pruebas del corte vertical: POST /pedidos.

Cubren el escenario ESC-01 (arc42 §10.2 / fila de Usabilidad en
docs/aspectos.md): un estudiante nuevo debe poder crear un pedido con
un único request, y recibir un error claro si el ítem no existe o no
está disponible.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_crear_pedido_exitoso():
    respuesta = client.post(
        "/pedidos",
        json={"establecimiento_id": 1, "item_id": 1, "cantidad": 2},
    )
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre_item"] == "Arepa de huevo"
    assert cuerpo["total"] == 8000
    assert cuerpo["estado"] == "pendiente_pago"


def test_crear_pedido_item_no_encontrado():
    respuesta = client.post(
        "/pedidos",
        json={"establecimiento_id": 1, "item_id": 999, "cantidad": 1},
    )
    assert respuesta.status_code == 404


def test_crear_pedido_item_no_disponible():
    # item_id 3 (Empanada) está marcado como no disponible en el seed.
    respuesta = client.post(
        "/pedidos",
        json={"establecimiento_id": 2, "item_id": 3, "cantidad": 1},
    )
    assert respuesta.status_code == 409
