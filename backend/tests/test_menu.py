"""Pruebas del contexto Catálogo expuesto por HTTP.

Cubren la consulta de la carta, que es el primer paso de
[ESC-01](../../docs/arc42/arc42.md#esc-01): antes de pedir algo hay que poder
ver qué hay.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_consultar_un_item_devuelve_el_precio_en_centavos():
    respuesta = client.get("/v1/menu/items/1")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Arepa de huevo"
    assert cuerpo["precio_centavos"] == 400000, "4 000 COP expresados en centavos"
    assert cuerpo["establecimiento_id"] == 1


def test_consultar_un_item_inexistente_responde_404():
    assert client.get("/v1/menu/items/999").status_code == 404


def test_listar_la_carta_de_un_establecimiento():
    respuesta = client.get("/v1/menu/establecimientos/1/items")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["establecimiento_id"] == 1
    assert [item["item_id"] for item in cuerpo["items"]] == [1, 2], (
        "el orden debe ser estable entre llamadas idénticas: el contrato no "
        "promete ningún criterio, así que el repositorio fija uno"
    )


def test_la_respuesta_es_un_sobre_y_no_una_lista_desnuda():
    """Decisión de evolvabilidad, no de estilo.

    Con el sobre, añadir paginación mañana es un campo nuevo en una respuesta
    —cambio compatible—. Con una lista en la raíz sería cambiar el tipo del
    cuerpo entero, que obliga a una versión mayor nueva.
    """
    cuerpo = client.get("/v1/menu/establecimientos/1/items").json()

    assert isinstance(cuerpo, dict)
    assert "items" in cuerpo


def test_filtrar_por_disponibles_omite_los_agotados():
    # El único ítem del establecimiento 2 está marcado como no disponible.
    completo = client.get("/v1/menu/establecimientos/2/items").json()
    filtrado = client.get(
        "/v1/menu/establecimientos/2/items", params={"solo_disponibles": True}
    ).json()

    assert len(completo["items"]) == 1
    assert completo["items"][0]["disponible"] is False
    assert filtrado["items"] == []


def test_un_establecimiento_sin_carta_responde_200_y_lista_vacia():
    """Distingue «no tiene nada» de «no existe», que no son lo mismo.

    Devolver 404 en ambos casos obligaría al frontend a adivinar si mostrar un
    error o un mensaje de «aún sin productos».
    """
    respuesta = client.get("/v1/menu/establecimientos/4/items")

    assert respuesta.status_code == 200
    assert respuesta.json()["items"] == []


def test_un_establecimiento_inexistente_responde_404():
    respuesta = client.get("/v1/menu/establecimientos/999/items")

    assert respuesta.status_code == 404


def test_el_catalogo_pregunta_a_cuentas_en_vez_de_guardar_una_copia():
    """ADR-0002: Cuentas es el único escritor de `Establecimiento`.

    Que Catálogo sepa responder 404 para un establecimiento inexistente sin
    guardar ninguna lista propia solo es posible porque lo consulta.
    """
    from app.menu import repository as catalogo

    ids_en_el_catalogo = {item.establecimiento_id for item in catalogo._ITEMS_SEED.values()}
    assert 4 not in ids_en_el_catalogo, (
        "el establecimiento 4 no aparece en el catálogo y aun así se puede "
        "consultar: la fuente de verdad es Cuentas"
    )
