"""Nada que cambie el sistema entra por `GET`.

En la sustentación final del 25/11/2026 se pidió que los llamados que cambian el
estado del sistema —crear un pedido, moverlo, canjearlo, pagar— fueran por `POST`
y no por `GET`. Ya era así desde la primera versión del contrato, y esta prueba
existe para que lo siga siendo cuando alguien añada la ruta que falta a las
cinco de la tarde.

### Por qué importa que sea una prueba y no una costumbre

Un `GET` que escribe se cachea, se prefetcha, se repite al recargar y lo sigue un
rastreador. Un enlace `GET /v1/pedidos/41/estado?nuevo=entregado` en un correo
entregaría el pedido con solo abrirlo. Nada de eso lo detecta el contrato: OpenAPI
permite declarar un `GET` con efectos, y la prueba de conformidad solo mira que el
código haga lo que el contrato dice.

Se comprueba por los dos lados, como el resto de las pruebas de contrato:

1. **En la API.** Toda ruta `GET` tiene que estar en la lista de lecturas de abajo.
   Añadir un `GET` nuevo obliga a añadirlo aquí, y añadirlo aquí es prometer que no
   escribe.
2. **En el sitio.** Toda llamada de `app.js`, `panel.js` y `pasarela.js` que no
   declare método —y por tanto sea `GET`— tiene que apuntar a una de esas lecturas.
   Un guion no puede inventarse una escritura por `GET` aunque la API no la tenga,
   porque el día que la tuviera ya estaría usándola.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.main import app

RAIZ = Path(__file__).resolve().parents[2]
SITIO = RAIZ / "sitio"

#: Las únicas rutas que se leen con `GET`. Cada una devuelve estado y no lo toca.
#:
#: Es una lista cerrada a propósito: una ruta `GET` que no esté aquí hace fallar
#: la primera prueba, y quien la añada tiene que mirar si de verdad no escribe.
LECTURAS = {
    "/health",
    "/metricas",
    "/v1/menu/items/{item_id}",
    "/v1/menu/establecimientos/{establecimiento_id}/items",
    "/v1/pedidos",
    "/v1/pedidos/{pedido_id}",
    "/v1/pagos/intentos/{referencia_pago}",
    "/v1/avisos/clave-publica",
}

#: Métodos con los que se escribe. `PUT` y `PATCH` no están porque no se usan:
#: el mostrador cambia un solo campo a la vez y cada uno es un sub-recurso con
#: nombre (`/estado`, `/aviso-push`), que es lo que dice la ruta qué se puede tocar.
ESCRITURAS = {"post", "delete"}


def _rutas():
    for ruta, metodos in app.openapi()["paths"].items():
        for metodo in metodos:
            yield ruta, metodo.lower()


def test_toda_ruta_get_es_una_lectura_declarada():
    sin_declarar = sorted(
        ruta for ruta, metodo in _rutas() if metodo == "get" and ruta not in LECTURAS
    )
    assert not sin_declarar, (
        f"Estas rutas responden a GET y no están en LECTURAS: {sin_declarar}. "
        "Si de verdad no escriben nada, añádelas a la lista. Si escriben, son "
        "POST: un GET con efectos se cachea, se prefetcha y se repite al recargar."
    )


def test_toda_escritura_va_por_post_o_delete():
    """Lo que no es lectura escribe, y lo que escribe no admite otro verbo."""
    raras = sorted(
        (ruta, metodo) for ruta, metodo in _rutas()
        if ruta not in LECTURAS and metodo not in ESCRITURAS
    )
    assert not raras, (
        f"Estas rutas escriben con un método que esta suite no contempla: {raras}. "
        "Si es GET, es un error. Si es PUT o PATCH, hay que decidirlo y ampliar "
        "ESCRITURAS, no colarlo."
    )


def test_toda_lectura_declarada_sigue_existiendo():
    """Una lectura que desaparece también es un cambio incompatible (I-1)."""
    existentes = {ruta for ruta, metodo in _rutas() if metodo == "get"}
    desaparecidas = sorted(LECTURAS - existentes)
    assert not desaparecidas, (
        f"LECTURAS promete rutas GET que la API ya no tiene: {desaparecidas}."
    )


# ---------------------------------------------------------------------------
# El sitio
# ---------------------------------------------------------------------------

#: Cada llamada `api(...)` de un guion: la ruta y el texto que la sigue, que es
#: donde iría `method:`. Se corta en la siguiente llamada o a los 400 caracteres,
#: que es más que cualquier cuerpo de petición del sitio.
_LLAMADA = re.compile(r"\bapi\(\s*[`\"']([^`\"']*)[`\"']")
_METODO = re.compile(r"method:\s*[\"'](\w+)[\"']")


def _llamadas_del_sitio(nombre: str):
    fuente = (SITIO / nombre).read_text(encoding="utf-8")
    posiciones = [m.start() for m in _LLAMADA.finditer(fuente)] + [len(fuente)]
    for inicio, fin in zip(posiciones, posiciones[1:]):
        trozo = fuente[inicio:min(fin, inicio + 400)]
        ruta = _LLAMADA.match(trozo).group(1)
        metodo = _METODO.search(trozo)
        yield ruta, (metodo.group(1).lower() if metodo else "get")


def _coincide(ruta_del_sitio: str, patron: str) -> bool:
    """`/v1/pedidos/${encodeURIComponent(id)}` casa con `/v1/pedidos/{pedido_id}`."""
    expresion = re.sub(r"\{[^}]+\}", r"[^/]+", re.escape(patron).replace(r"\{", "{").replace(r"\}", "}"))
    ruta = re.sub(r"\$\{[^}]*\}", "x", ruta_del_sitio)
    return re.fullmatch(expresion, ruta) is not None


def test_el_sitio_no_lee_con_get_nada_que_no_sea_una_lectura():
    for nombre in ("app.js", "panel.js", "pasarela.js"):
        for ruta, metodo in _llamadas_del_sitio(nombre):
            if metodo != "get":
                assert metodo in ESCRITURAS, (
                    f"sitio/{nombre} llama a `{ruta}` con {metodo.upper()}, que la "
                    "API no usa."
                )
                continue
            assert any(_coincide(ruta, patron) for patron in LECTURAS), (
                f"sitio/{nombre} pide `{ruta}` sin método —es decir, con GET— y esa "
                "ruta no es una de las lecturas de la API. Si escribe, lleva "
                "`method: \"POST\"`."
            )


def test_el_sitio_nunca_escribe_get_a_mano():
    """`method: "GET"` explícito no aparece: si alguien lo escribe, es que dudó."""
    for nombre in ("app.js", "panel.js", "pasarela.js"):
        fuente = (SITIO / nombre).read_text(encoding="utf-8")
        assert not re.search(r"method:\s*[\"']GET[\"']", fuente), (
            f"sitio/{nombre} declara `method: \"GET\"`. GET es lo que se usa cuando "
            "no se declara nada; declararlo sugiere que se quería otra cosa."
        )
