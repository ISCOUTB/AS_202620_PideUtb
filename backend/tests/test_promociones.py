"""Promociones válidas solo dentro de una franja horaria.

El Asao tiene dos, ambas de 2:30 a 3:30 de la tarde, y son de dos formas
distintas:

- el combo de hamburguesa de pollo **baja de precio** dentro de la franja;
- el combo de perro con gaseosa **solo existe** dentro de la franja.

### Dónde se prueba cada cosa

La regla es una función de dos datos —el ítem y la hora— y se prueba como tal,
construyendo el ítem a mano. Así se pueden recorrer los bordes del intervalo sin
base de datos y sin tocar el reloj de la máquina, que es lo que permite que
estas pruebas corran en cualquier parte y no fallen a las 2:30 de la tarde.

Al final hay un bloque contra PostgreSQL que comprueba **los dos productos
reales**, con sus precios y su franja de verdad. La regla puede estar bien y la
carga mal; son dos defectos distintos y hacen falta dos pruebas.
"""
from __future__ import annotations

import os
from datetime import time

import pytest
from fastapi.testclient import TestClient

from app import base_de_datos
from app.main import app
from app.menu import service as catalogo_service
from app.menu.models import ItemMenu
from app.pedidos import service as pedidos_service

URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()
sin_postgres = pytest.mark.skipif(
    not URL_PRUEBAS,
    reason="Sin PIDEUTB_DATABASE_URL_PRUEBAS: la carta real solo vive en PostgreSQL.",
)


def _con_descuento(**extra) -> ItemMenu:
    """Un producto que se vende todo el día y baja de precio en la franja."""
    campos = dict(
        id=120,
        establecimiento_id=5,
        nombre="Combo hamburguesa pollo",
        precio_centavos=2420000,
        disponible=True,
        precio_promocional_centavos=1650000,
        promocion_desde=time(14, 30),
        promocion_hasta=time(15, 30),
    )
    campos.update(extra)
    return ItemMenu(**campos)


def _solo_en_la_franja(**extra) -> ItemMenu:
    """Un producto que no se vende fuera de la franja."""
    campos = dict(
        id=127,
        establecimiento_id=5,
        nombre="Combo perro sencillo + gaseosa 400 ml",
        precio_centavos=1190000,
        disponible=True,
        promocion_desde=time(14, 30),
        promocion_hasta=time(15, 30),
        solo_en_promocion=True,
    )
    campos.update(extra)
    return ItemMenu(**campos)


# ---------------------------------------------------------------------------
# La regla: un ítem y una hora
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "hora, dentro",
    [
        (time(14, 29, 59), False),
        (time(14, 30, 0), True),    # el inicio entra
        (time(15, 0), True),
        (time(15, 29, 59), True),
        (time(15, 30, 0), False),   # el final NO entra
        (time(2, 30), False),       # 2:30 de la madrugada no es 2:30 de la tarde
        (time(23, 59), False),
    ],
)
def test_los_bordes_de_la_franja(hora, dentro):
    """`desde` incluido, `hasta` excluido.

    A las 15:30 en punto la promoción ya terminó. El intervalo medio abierto es
    lo que hace que dos franjas consecutivas no se pisen en el instante que
    comparten, y está decidido en un solo sitio en vez de en cada consulta.

    El caso de las 2:30 de la madrugada está porque la promoción se anuncia como
    «2:30», y un `time` de 12 horas mal interpretado la abriría de noche.
    """
    publicado = catalogo_service._publicar(_con_descuento(), hora)

    if dentro:
        assert publicado.precio_centavos == 1650000
        assert publicado.precio_antes_centavos == 2420000
    else:
        assert publicado.precio_centavos == 2420000
        assert publicado.precio_antes_centavos is None


def test_fuera_de_la_franja_no_hay_nada_que_tachar():
    publicado = catalogo_service._publicar(_con_descuento(), time(9, 0))

    assert publicado.precio_antes_centavos is None
    assert publicado.promocion_hasta is None
    assert publicado.disponible is True, "se sigue vendiendo, al precio normal"


def test_dentro_de_la_franja_se_dice_hasta_cuando():
    publicado = catalogo_service._publicar(_con_descuento(), time(15, 0))

    assert publicado.promocion_hasta == "15:30"


def test_el_producto_de_solo_promocion_desaparece_fuera_de_su_franja():
    fuera = catalogo_service._publicar(_solo_en_la_franja(), time(9, 0))
    dentro = catalogo_service._publicar(_solo_en_la_franja(), time(15, 0))

    assert fuera.disponible is False
    assert dentro.disponible is True


def test_el_producto_de_solo_promocion_no_tiene_un_precio_antes():
    """11 900 no es un descuento sobre nada: es su único precio.

    Publicar un «antes» inventado haría que la carta tachara una cifra que
    nunca se cobró.
    """
    dentro = catalogo_service._publicar(_solo_en_la_franja(), time(15, 0))

    assert dentro.precio_centavos == 1190000
    assert dentro.precio_antes_centavos is None


def test_agotado_sigue_agotado_dentro_de_la_franja():
    """La franja y el agotado son dos cosas distintas.

    Un combo que el mostrador marcó agotado a las 2:45 no se puede pedir aunque
    la promoción esté abierta. Si la franja pisara a `disponible`, abrir la
    promoción resucitaría productos que no hay.
    """
    publicado = catalogo_service._publicar(
        _solo_en_la_franja(disponible=False), time(15, 0)
    )
    assert publicado.disponible is False

    con_descuento = catalogo_service._publicar(
        _con_descuento(disponible=False), time(15, 0)
    )
    assert con_descuento.disponible is False
    assert con_descuento.precio_centavos == 1650000, "el precio sí se resuelve"


def test_un_producto_sin_promocion_no_cambia_a_ninguna_hora():
    """La inmensa mayoría de la carta no tiene franja, y no debe notarlo."""
    normal = ItemMenu(
        id=101,
        establecimiento_id=5,
        nombre="Costillitas de cerdo ahumadas",
        precio_centavos=2980000,
    )

    for hora in (time(9, 0), time(14, 30), time(15, 0), time(15, 30)):
        publicado = catalogo_service._publicar(normal, hora)
        assert publicado.precio_centavos == 2980000
        assert publicado.precio_antes_centavos is None
        assert publicado.promocion_hasta is None
        assert publicado.disponible is True


def test_la_hora_se_toma_de_bogota_y_no_del_sistema():
    """La franja es hora local del establecimiento, fija en el código.

    El contenedor corre en UTC y el portátil de quien desarrolla no. Leyendo la
    zona del entorno, «de 2:30 a 3:30» significaría dos cosas distintas en dos
    máquinas, y la que se vería mal es producción.
    """
    assert str(catalogo_service._ZONA) == "America/Bogota"


# ---------------------------------------------------------------------------
# Los dos productos reales, contra la carta cargada
# ---------------------------------------------------------------------------

@pytest.fixture
def contra_postgres(monkeypatch):
    if not URL_PRUEBAS:
        pytest.skip("Sin PIDEUTB_DATABASE_URL_PRUEBAS.")
    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    yield
    base_de_datos.cerrar_pool()


@pytest.fixture
def a_las_tres(monkeypatch, contra_postgres):
    """Congela el reloj del catálogo dentro de la franja."""
    monkeypatch.setattr(catalogo_service, "_ahora", lambda: time(15, 0))


@pytest.fixture
def a_las_nueve(monkeypatch, contra_postgres):
    """Congela el reloj del catálogo fuera de la franja."""
    monkeypatch.setattr(catalogo_service, "_ahora", lambda: time(9, 0))


@sin_postgres
def test_el_combo_de_pollo_cuesta_16500_en_la_franja(a_las_tres):
    cuerpo = TestClient(app).get("/v1/menu/items/120").json()

    assert cuerpo["nombre"] == "Combo hamburguesa pollo"
    assert cuerpo["precio_centavos"] == 1650000
    assert cuerpo["precio_antes_centavos"] == 2420000
    assert cuerpo["promocion_hasta"] == "15:30"


@sin_postgres
def test_el_combo_de_pollo_cuesta_24200_fuera_de_la_franja(a_las_nueve):
    cuerpo = TestClient(app).get("/v1/menu/items/120").json()

    assert cuerpo["precio_centavos"] == 2420000
    assert cuerpo["precio_antes_centavos"] is None
    assert cuerpo["promocion_hasta"] is None


@sin_postgres
def test_el_combo_de_perro_no_sale_en_la_carta_fuera_de_su_franja(a_las_nueve):
    """Pedir solo los disponibles tiene que esconderlo.

    El filtro se aplica sobre la disponibilidad **ya resuelta**, no sobre la
    columna: filtrando por la columna, un producto fuera de su franja seguiría
    apareciendo en la carta y solo fallaría al intentar pedirlo.
    """
    cliente = TestClient(app)

    todos = cliente.get("/v1/menu/establecimientos/5/items").json()["items"]
    disponibles = cliente.get(
        "/v1/menu/establecimientos/5/items?solo_disponibles=true"
    ).json()["items"]

    assert any(i["item_id"] == 127 for i in todos), "existe"
    assert not any(i["item_id"] == 127 for i in disponibles), "pero no se puede pedir"


@sin_postgres
def test_el_combo_de_perro_si_sale_dentro_de_su_franja(a_las_tres):
    disponibles = TestClient(app).get(
        "/v1/menu/establecimientos/5/items?solo_disponibles=true"
    ).json()["items"]

    combo = next(i for i in disponibles if i["item_id"] == 127)
    assert combo["precio_centavos"] == 1190000
    assert combo["precio_antes_centavos"] is None


@sin_postgres
def test_el_pedido_cobra_el_precio_de_la_franja(a_las_tres):
    """**La prueba que importa.** Lo que la carta muestra es lo que se cobra.

    `pedidos.service` no sabe nada de franjas horarias: lee el precio del ítem
    que le da el catálogo. Que la promoción se resuelva en un solo sitio es lo
    que hace imposible que la carta diga 16 500 y el pedido cobre 24 200.
    """
    pedido = pedidos_service.crear_pedido([(120, 2)])

    assert pedido.lineas[0].precio_unitario_centavos == 1650000
    assert pedido.total_centavos == 3300000


@sin_postgres
def test_fuera_de_la_franja_el_pedido_cobra_el_precio_normal(a_las_nueve):
    pedido = pedidos_service.crear_pedido([(120, 1)])

    assert pedido.lineas[0].precio_unitario_centavos == 2420000


@sin_postgres
def test_no_se_puede_pedir_el_combo_de_perro_fuera_de_su_franja(a_las_nueve):
    """Se rechaza por la misma puerta que un producto agotado.

    Es el caso de quien lo añadió al carrito a las 15:29 y pulsa «Pagar» a las
    15:31. El pedido no se crea a medias: se rechaza entero.
    """
    with pytest.raises(pedidos_service.ItemNoDisponibleError):
        pedidos_service.crear_pedido([(127, 1)])
