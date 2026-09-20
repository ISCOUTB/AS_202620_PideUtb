"""Pruebas de propiedad de datos entre los contextos Catálogo, Pedidos y Cuentas.

Verifican las violaciones V-01, V-02, V-03 y V-06 de `docs/violaciones.md`
y la decisión de [ADR-0002](../../docs/adr/0002-propiedad-datos-establecimiento.md):
el contexto Cuentas (`usuarios`) es el único escritor de `Establecimiento`,
y Pedidos deriva el establecimiento del ítem en lugar de aceptarlo del
cliente.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_establecimiento_se_deriva_del_item_y_no_del_cliente():
    """V-01: el cliente no decide a qué establecimiento va el pedido.

    El ítem 1 pertenece al establecimiento 1. Aunque la petición incluya
    otro `establecimiento_id`, el campo se ignora.
    """
    respuesta = client.post(
        "/v1/pedidos",
        json={"item_id": 1, "cantidad": 1, "establecimiento_id": 99},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["establecimiento_id"] == 1


def test_pedido_en_establecimiento_inactivo_se_rechaza():
    """V-02: Cuentas es la fuente de verdad sobre si un punto opera.

    El ítem 4 pertenece al establecimiento 3, inactivo en el seed.
    """
    respuesta = client.post("/v1/pedidos", json={"item_id": 4, "cantidad": 1})

    assert respuesta.status_code == 409
    assert "no está recibiendo pedidos" in respuesta.json()["detail"]


def test_cantidad_fuera_de_rango_se_rechaza():
    """V-03: cantidad cero o negativa producía totales absurdos."""
    for cantidad in (0, -5, 51):
        respuesta = client.post("/v1/pedidos", json={"item_id": 1, "cantidad": cantidad})
        assert respuesta.status_code == 422, f"cantidad={cantidad} debería rechazarse"


def test_el_pedido_conserva_el_precio_aunque_cambie_el_catalogo():
    """V-06 / H-1: la instantánea es deliberada y el pedido no se revalúa."""
    from app.menu import repository as catalogo

    respuesta = client.post("/v1/pedidos", json={"item_id": 2, "cantidad": 3})
    assert respuesta.status_code == 201
    pedido = respuesta.json()
    assert pedido["precio_unitario_centavos"] == 300000
    assert pedido["total_centavos"] == 900000

    original = catalogo._ITEMS_SEED[2]
    catalogo._ITEMS_SEED[2] = original.model_copy(update={"precio_centavos": 999900})
    try:
        assert pedido["precio_unitario_centavos"] == 300000
        assert pedido["total_centavos"] == 900000
    finally:
        catalogo._ITEMS_SEED[2] = original


def test_catalogo_no_guarda_datos_del_establecimiento():
    """H-2: `menu` guarda solo la referencia, no el nombre ni el horario.

    Los datos maestros del establecimiento pertenecen a Cuentas; que
    Catálogo los duplicara sería crear un segundo escritor.
    """
    from app.menu.models import ItemMenu

    campos = set(ItemMenu.model_fields)
    assert "establecimiento_id" in campos
    assert not {"nombre_establecimiento", "ubicacion", "horario"} & campos


def test_cuentas_es_la_unica_fuente_de_los_datos_del_establecimiento():
    from app.usuarios import service as cuentas

    establecimiento = cuentas.obtener_establecimiento(1)
    assert establecimiento is not None
    assert establecimiento.nombre == "Cafetería Central"
    assert cuentas.obtener_establecimiento(999) is None
