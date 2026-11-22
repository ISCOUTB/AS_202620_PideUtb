"""Los topes del pedido: 4 por producto, y 4 comidas, 4 bebidas y 4 acompañantes.

Nacen de un pedido real de más de 800 000 pesos, que ningún mostrador prepara en
una hora de almuerzo (ADR-0014). Hasta la 5.0.0 se aceptaban 50 unidades de cada
producto y 30 productos distintos.

El tope por producto lo aplica el esquema de la petición (422). El tope por tipo
no cabe en un esquema, porque depende de qué es cada producto en el catálogo, y
lo aplica el servicio (409).
"""
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import base_de_datos
from app.main import app
from app.menu import service as catalogo_service
from app.menu.contracts import ItemDisponible, TipoDeProducto
from app.pedidos import repository as pedidos_repo
from app.pedidos import service as pedidos_service
from tests.test_repositorios import _preparar_base_de_datos

client = TestClient(app)

RAIZ = Path(__file__).resolve().parents[2]
URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()
CORREO = "cliente@example.com"


@pytest.fixture(autouse=True)
def sin_pedidos():
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    yield
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0


@pytest.fixture
def carta_con_tipos(monkeypatch):
    """Seis productos de cada tipo, y dos sin tipo, en el establecimiento 1.

    La carta en memoria tiene una sola comida; para pasar el tope de comidas
    sin pasar el de un producto hacen falta al menos dos.
    """
    productos: dict[int, ItemDisponible] = {}

    def poner(base: int, categoria: str | None, tipo: TipoDeProducto | None) -> None:
        for i in range(6):
            productos[base + i] = ItemDisponible(
                item_id=base + i,
                establecimiento_id=1,
                nombre=f"{categoria or 'Sin tipo'} {i}",
                precio_centavos=1_000_00,
                disponible=True,
                categoria=categoria,
                tipo=tipo,
            )

    poner(100, "Asados", TipoDeProducto.COMIDA)
    poner(200, "Bebidas", TipoDeProducto.BEBIDA)
    poner(300, "Adiciones", TipoDeProducto.ACOMPANANTE)
    poner(400, None, None)
    monkeypatch.setattr(catalogo_service, "obtener_item", productos.get)


def _pedir(*lineas: tuple[int, int]):
    return client.post(
        "/v1/pedidos",
        json={
            "lineas": [{"item_id": i, "cantidad": c} for i, c in lineas],
            "correo_cliente": CORREO,
        },
    )


# --- Por producto -------------------------------------------------------------


def test_hasta_cuatro_del_mismo_producto():
    assert _pedir((1, 4)).status_code == 201


def test_cinco_del_mismo_producto_se_rechazan_antes_de_guardar():
    respuesta = _pedir((1, 5))

    assert respuesta.status_code == 422
    assert pedidos_repo._PEDIDOS == {}


def test_el_servicio_tambien_aplica_el_tope_por_producto():
    """Quien llama desde dentro del proceso no pasa por el esquema."""
    with pytest.raises(pedidos_service.LimiteDelPedidoError):
        pedidos_service.crear_pedido([(1, 5)], correo_cliente=CORREO)


# --- Por tipo -----------------------------------------------------------------


def test_cuatro_comidas_repartidas_caben(carta_con_tipos):
    """2 asados + 2 hamburguesas son 4 comidas: el ejemplo del cliente."""
    assert _pedir((100, 2), (101, 2)).status_code == 201


def test_una_comida_de_mas_se_rechaza_aunque_cada_linea_quepa(carta_con_tipos):
    """4 + 1 comidas: ninguna línea pasa de 4, la suma sí."""
    respuesta = _pedir((100, 4), (101, 1))

    assert respuesta.status_code == 409
    assert "4 comidas" in respuesta.json()["detail"]
    assert pedidos_repo._PEDIDOS == {}


def test_el_pedido_mas_grande_es_cuatro_de_cada_tipo(carta_con_tipos):
    """Bebidas y acompañantes no cuentan contra las comidas."""
    respuesta = _pedir((100, 4), (200, 2), (201, 2), (300, 4))

    assert respuesta.status_code == 201


@pytest.mark.parametrize(
    ("base", "nombre"),
    [(200, "bebidas"), (300, "acompañantes")],
)
def test_bebidas_y_acompanantes_tienen_su_propio_tope(carta_con_tipos, base, nombre):
    respuesta = _pedir((base, 4), (base + 1, 1))

    assert respuesta.status_code == 409
    assert f"4 {nombre}" in respuesta.json()["detail"]


def test_un_producto_sin_tipo_solo_tiene_el_tope_por_producto(carta_con_tipos):
    assert _pedir((400, 4), (401, 4), (402, 4)).status_code == 201


# --- Lo que publica el catálogo ----------------------------------------------


def test_la_carta_publica_el_tipo_de_cada_producto():
    items = client.get("/v1/menu/establecimientos/1/items").json()["items"]
    tipos = {item["item_id"]: item["tipo"] for item in items}

    assert tipos == {1: "comida", 2: "bebida"}


@pytest.fixture
def contra_postgres(monkeypatch):
    if not URL_PRUEBAS:
        pytest.skip("Sin PIDEUTB_DATABASE_URL_PRUEBAS.")
    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()
    yield
    base_de_datos.cerrar_pool()


def test_cada_categoria_de_la_carta_tiene_tipo(contra_postgres):
    """Contra la carta real, con las migraciones aplicadas.

    Una categoría nueva que no esté en `TIPO_POR_CATEGORIA` dejaría sus productos
    sin tope de tipo, y nada fallaría: se podrían pedir 4 de cada uno sin límite
    de comidas. Esto lo convierte en una construcción roja.
    """
    items = TestClient(app).get("/v1/menu/establecimientos/5/items").json()["items"]
    sin_tipo = sorted({item["categoria"] for item in items if item["tipo"] is None})

    assert items, "La carta del establecimiento 5 vino vacía"
    assert sin_tipo == [], f"Categorías sin tipo en TIPO_POR_CATEGORIA: {sin_tipo}"


# --- El sitio apaga el «+» con los mismos números ------------------------------


def test_el_sitio_conoce_los_mismos_topes():
    """`sitio/config.js` copia los topes para apagar el «+» antes de que la API
    diga que no. Si se separan, el sitio deja pedir algo que la API rechaza, o
    apaga el botón antes de tiempo."""
    texto = (RAIZ / "sitio" / "config.js").read_text(encoding="utf-8")

    por_producto = re.search(r"\bMAXIMO_POR_PRODUCTO:\s*(\d+)", texto)
    por_tipo = re.search(r"\bMAXIMO_POR_TIPO:\s*\{([^}]*)\}", texto)
    assert por_producto and por_tipo, "Faltan los topes en sitio/config.js"

    del_sitio = {
        clave: int(valor)
        for clave, valor in re.findall(r"(\w+):\s*(\d+)", por_tipo.group(1))
    }
    de_la_api = {tipo.value: maximo for tipo, maximo in pedidos_service.MAXIMO_POR_TIPO.items()}

    assert int(por_producto.group(1)) == pedidos_service.MAXIMO_POR_PRODUCTO
    assert del_sitio == de_la_api
