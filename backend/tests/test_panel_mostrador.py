"""El panel del mostrador: cola de pedidos y máquina de estados.

Cubre [ESC-03](../../docs/arc42/arc42.md#esc-03) — el establecimiento gestiona
el estado de sus pedidos.

Lo que más se prueba aquí no es lo que el mostrador **puede** hacer, sino lo
que **no puede**: marcar un pedido como pagado sin que la pasarela lo confirme,
saltarse estados, o ver los pedidos de otro establecimiento. Como todavía no
hay autenticación ([V-10](../../docs/violaciones.md)), esas prohibiciones son
la única barrera que existe.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pedidos import repository, service
from app.pedidos.contracts import EstadoPedido, EstadoSolicitable

client = TestClient(app)


@pytest.fixture(autouse=True)
def repositorio_limpio():
    """Aísla cada prueba.

    El estado vive en memoria del proceso (V-09), así que sin esto un pedido
    creado en una prueba aparecería en la cola de la siguiente y el orden de
    ejecución cambiaría los resultados.
    """
    repository._PEDIDOS.clear()
    repository._contador = 0
    yield
    repository._PEDIDOS.clear()


def _pedido_pagado(item_id: int = 1) -> int:
    """Crea un pedido y lo lleva a `pagado` por la vía legítima."""
    pedido_id = client.post("/v1/pedidos", json={"item_id": item_id, "cantidad": 1}).json()["pedido_id"]
    service.confirmar_pago(pedido_id)
    return pedido_id


# ---------------------------------------------------------------------------
# Lo que el mostrador NO puede hacer
# ---------------------------------------------------------------------------

def test_el_mostrador_no_puede_marcar_un_pedido_como_pagado():
    """La prueba que justifica todo el diseño de la máquina de estados.

    Si esta transición estuviera permitida, cualquiera con un navegador podría
    marcar su pedido como pagado y retirar la comida sin pagarla: no hay
    autenticación que lo impida. Solo la dispara el webhook firmado de la
    pasarela, a través de `confirmar_pago`.
    """
    pedido_id = client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1}).json()["pedido_id"]

    respuesta = client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "pagado"})

    # 422 y no 409: `pagado` ni siquiera es un valor que se pueda pedir, así
    # que lo rechaza el esquema antes de llegar a la lógica de negocio.
    assert respuesta.status_code == 422
    assert client.get(f"/v1/pedidos/{pedido_id}").json()["estado"] == "pendiente_pago"


def test_tampoco_puede_devolverlo_a_pendiente_de_pago():
    """Revertir un pago desde el mostrador dejaría el código de canje emitido."""
    pedido_id = _pedido_pagado()

    assert client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "pendiente_pago"}).status_code == 422


def test_no_se_pueden_saltar_estados():
    """Un pedido no se entrega sin haberse preparado.

    Permitirlo haría inútil el estado intermedio: nadie podría saber, mirando
    la cola, qué hay realmente en la cocina.
    """
    pedido_id = _pedido_pagado()

    respuesta = client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "entregado"})

    assert respuesta.status_code == 409
    # El mensaje dice el estado actual, no solo que se rechazó: quien atiende
    # suele tener la pantalla desactualizada porque otro ya movió el pedido.
    assert "pagado" in respuesta.json()["detail"]


def test_los_estados_finales_son_finales():
    """Un pedido entregado que vuelve atrás es un error de registro.

    Permitirlo haría imposible contar cuántos pedidos se sirvieron de verdad.
    """
    pedido_id = _pedido_pagado()
    for estado in ("en_preparacion", "listo_para_recoger", "entregado"):
        assert client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": estado}).status_code == 200

    assert client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "en_preparacion"}).status_code == 409


def test_un_pedido_inexistente_da_404_y_no_409():
    """Distinguirlos importa: uno es un error del cliente, el otro del estado."""
    assert client.post("/v1/pedidos/9999/estado", json={"estado": "en_preparacion"}).status_code == 404


# ---------------------------------------------------------------------------
# El recorrido completo
# ---------------------------------------------------------------------------

def test_el_recorrido_completo_del_mostrador():
    pedido_id = _pedido_pagado()

    for estado in ("en_preparacion", "listo_para_recoger", "entregado"):
        respuesta = client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": estado})
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == estado


def test_cancelar_es_posible_mientras_no_se_haya_entregado():
    for estado_intermedio in ("pagado", "en_preparacion"):
        repository._PEDIDOS.clear()
        pedido_id = _pedido_pagado()
        if estado_intermedio == "en_preparacion":
            client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "en_preparacion"})

        assert client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "cancelado"}).status_code == 200


def test_el_codigo_de_canje_sobrevive_al_cambio_de_estado():
    """Avanzar el pedido no puede borrar lo que el usuario necesita para recoger."""
    pedido_id = _pedido_pagado()
    codigo = client.get(f"/v1/pedidos/{pedido_id}").json()["codigo_canje"]
    assert codigo

    respuesta = client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": "en_preparacion"})
    assert respuesta.json()["codigo_canje"] == codigo


# ---------------------------------------------------------------------------
# La cola del mostrador
# ---------------------------------------------------------------------------

def test_la_cola_solo_muestra_los_pedidos_del_establecimiento():
    """Sin autenticación, el aislamiento por establecimiento es lo único que hay.

    El ítem 1 pertenece al establecimiento 1 y el 4 al establecimiento 3.
    """
    client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1})
    client.post("/v1/pedidos", json={"item_id": 4, "cantidad": 1})

    cola = client.get("/v1/pedidos", params={"establecimiento_id": 1}).json()

    assert cola["establecimiento_id"] == 1
    assert [p["establecimiento_id"] for p in cola["pedidos"]] == [1]


def test_el_establecimiento_es_obligatorio():
    """Sin él, esta ruta devolvería los pedidos de todo el campus."""
    assert client.get("/v1/pedidos").status_code == 422


def test_la_cola_llega_del_mas_reciente_al_mas_antiguo():
    """Quien atiende necesita ver arriba lo que acaba de entrar."""
    ids = [client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1}).json()["pedido_id"]
           for _ in range(3)]

    cola = client.get("/v1/pedidos", params={"establecimiento_id": 1}).json()["pedidos"]

    assert [p["pedido_id"] for p in cola] == sorted(ids, reverse=True)


def test_la_cola_incluye_los_pedidos_ya_entregados():
    """Ocultarlos obligaría a recordar qué se acaba de entregar para corregirse.

    ESC-03 pide resolver en tres interacciones, no recordar.
    """
    pedido_id = _pedido_pagado()
    for estado in ("en_preparacion", "listo_para_recoger", "entregado"):
        client.post(f"/v1/pedidos/{pedido_id}/estado", json={"estado": estado})

    cola = client.get("/v1/pedidos", params={"establecimiento_id": 1}).json()["pedidos"]
    assert [p["estado"] for p in cola] == ["entregado"]


def test_un_establecimiento_sin_pedidos_devuelve_lista_vacia_y_no_404():
    """No tener pedidos no es un error: es el estado normal fuera de hora pico."""
    respuesta = client.get("/v1/pedidos", params={"establecimiento_id": 2})

    assert respuesta.status_code == 200
    assert respuesta.json()["pedidos"] == []


# ---------------------------------------------------------------------------
# Que las dos declaraciones de la regla no se separen
# ---------------------------------------------------------------------------

def test_el_enum_de_peticion_coincide_con_la_maquina_de_estados():
    """`EstadoSolicitable` y `TRANSICIONES_DEL_MOSTRADOR` dicen la misma regla.

    Una en el contrato y otra en el servicio. Si se separaran, el contrato
    anunciaría un estado que la lógica rechaza siempre —o al revés, aceptaría
    uno que el esquema ya filtró—, y el `409` dejaría de significar lo que dice
    la documentación.
    """
    alcanzables = set()
    for destinos in service.TRANSICIONES_DEL_MOSTRADOR.values():
        alcanzables |= {e.value for e in destinos}

    assert {e.value for e in EstadoSolicitable} == alcanzables


def test_ningun_estado_solicitable_deja_el_pedido_sin_pagar():
    """Ninguna transición del mostrador puede devolver un pedido a sin pagar."""
    prohibidos = {EstadoPedido.PENDIENTE_PAGO.value, EstadoPedido.PAGADO.value}

    assert prohibidos.isdisjoint({e.value for e in EstadoSolicitable})
