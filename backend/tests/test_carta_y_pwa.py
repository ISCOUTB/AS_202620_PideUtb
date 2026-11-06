"""La carta nueva y lo que hace instalable al sitio. Fallan en silencio si nadie mira."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.menu import service as menu_service

client = TestClient(app)

RAIZ = Path(__file__).resolve().parents[2]
SITIO = RAIZ / "sitio"
MIGRACIONES = RAIZ / "backend" / "migraciones"


def _sql() -> str:
    return "\n".join(a.read_text(encoding="utf-8") for a in sorted(MIGRACIONES.glob("*.sql")))


# --- Sugeridos del día ------------------------------------------------------


def _sugeridos_por_defecto() -> set[int]:
    return {int(i) for i in menu_service._SUGERIDOS_POR_DEFECTO.split(",")}


def test_los_sugeridos_por_defecto_existen_y_tienen_foto():
    """El sitio omite un sugerido sin foto: uno mal escrito desaparecería sin avisar."""
    sql = _sql()
    con_foto = {int(i) for i, _ in re.findall(r"\((\d+),\s*'(fotos/[^']+)'\)", sql)}

    faltan = _sugeridos_por_defecto() - con_foto
    assert not faltan, f"Los sugeridos {sorted(faltan)} no tienen foto en ninguna migración."


def test_la_api_marca_los_sugeridos(monkeypatch):
    monkeypatch.setenv("PIDEUTB_SUGERIDOS_DEL_DIA", "2")

    items = client.get("/v1/menu/establecimientos/1/items").json()["items"]

    assert {i["item_id"]: i["sugerido"] for i in items} == {1: False, 2: True}


def test_lo_que_no_es_un_numero_se_ignora_sin_tumbar_la_carta(monkeypatch):
    monkeypatch.setenv("PIDEUTB_SUGERIDOS_DEL_DIA", "dos, 1 ,,abc")

    respuesta = client.get("/v1/menu/establecimientos/1/items")

    assert respuesta.status_code == 200
    assert [i["item_id"] for i in respuesta.json()["items"] if i["sugerido"]] == [1]


def test_una_variable_vacia_deja_los_de_siempre(monkeypatch):
    """`compose.lab.yaml` la pasa vacía cuando nadie la ha puesto en el panel."""
    monkeypatch.setenv("PIDEUTB_SUGERIDOS_DEL_DIA", "")

    assert menu_service._sugeridos() == _sugeridos_por_defecto()


# --- Gaseosas y descripciones -----------------------------------------------


@pytest.mark.parametrize("sabor", ["Coca-Cola", "Postobón Manzana", "Colombiana", "Sprite", "Fanta", "Pepsi"])
@pytest.mark.parametrize("tamano", ["400 ml", "1,5 L"])
def test_cada_sabor_de_gaseosa_viene_en_los_dos_tamanos(sabor, tamano):
    assert f"'Gaseosa {sabor} {tamano}'" in _sql()


def test_cada_producto_de_la_carta_tiene_descripcion():
    """El sitio pinta lo que haya: un producto sin texto simplemente sale sin él."""
    sql = _sql()
    carta = {int(i) for i in re.findall(r"^\s*\((\d+),\s*5,\s*'", sql, re.M)}
    migracion = (MIGRACIONES / "010_gaseosas_y_descripciones.sql").read_text(encoding="utf-8")
    con_texto = {int(i) for i in re.findall(r"^\s*\((\d+),\s*'[^']+\.'\)", migracion, re.M)}
    con_texto |= {int(i) for i in re.findall(r"^\s*\((\d+),\s*5,.*'[^']+\.'\)", migracion, re.M)}
    # El combo de la franja trae la suya desde `006`.
    con_texto.add(127)

    assert carta - con_texto == set()


# --- Instalable, y sin caché ------------------------------------------------


def test_el_service_worker_no_se_interpone_en_ninguna_peticion():
    """Es la decisión importante de `sw.js`.

    Un manejador de `fetch` o una caché traerían de vuelta el fallo del 29 de
    octubre: un `index.html` nuevo con un `app.js` viejo es una página rota.
    """
    guion = (SITIO / "sw.js").read_text(encoding="utf-8")
    codigo = re.sub(r"^\s*//.*$", "", guion, flags=re.M)

    assert 'addEventListener("push"' in codigo
    assert 'addEventListener("fetch"' not in codigo
    assert "caches." not in codigo


def test_el_manifiesto_pide_iconos_que_existen_y_abre_como_aplicacion():
    """En iPhone, sin `standalone` no hay notificaciones."""
    manifiesto = json.loads((SITIO / "manifest.json").read_text(encoding="utf-8"))

    assert manifiesto["display"] == "standalone"
    faltan = [i["src"] for i in manifiesto["icons"] if not (SITIO / i["src"]).is_file()]
    assert not faltan
    assert {"192x192", "512x512"} <= {i["sizes"] for i in manifiesto["icons"]}


def test_la_imagen_del_sitio_lleva_el_manifiesto_y_los_iconos():
    """Si el Dockerfile no los copia, funciona en local y en producción da 404."""
    imagen = (SITIO / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY manifest.json" in imagen
    assert "COPY iconos/" in imagen


def test_las_paginas_enlazan_lo_que_existe():
    index = (SITIO / "index.html").read_text(encoding="utf-8")

    for ruta in re.findall(r'<link rel="(?:manifest|apple-touch-icon)" href="([^"]+)"', index):
        assert (SITIO / ruta).is_file(), ruta

