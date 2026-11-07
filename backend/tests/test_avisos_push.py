"""El aviso de que el pedido está listo: quién puede pedirlo, a dónde sale y cuántas veces."""
import base64
import http.client
import json
import time

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from fastapi.testclient import TestClient

from app import avisos, eventos
from app.main import app
from app.pedidos import repository as pedidos_repo
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import EstadoPedido

client = TestClient(app)

#: Una clave de prueba: 32 bytes en base64url. No sirve para nada fuera de aquí.
CLAVE = base64.urlsafe_b64encode(bytes(range(1, 33))).rstrip(b"=").decode()

ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123?x=1"


def _de_base64url(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


class _ConexionFalsa:
    """Un `HTTPSConnection` sin red, que guarda lo que le pidieron."""

    peticiones: list[dict] = []
    estado = 201

    def __init__(self, anfitrion, timeout=None):
        self.anfitrion = anfitrion

    def request(self, metodo, ruta, headers=None):
        _ConexionFalsa.peticiones.append(
            {"anfitrion": self.anfitrion, "metodo": metodo, "ruta": ruta, "cabeceras": headers}
        )

    def getresponse(self):
        return type("Respuesta", (), {"status": _ConexionFalsa.estado})

    def close(self):
        pass


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("PIDEUTB_VAPID_CLAVE_PRIVADA", CLAVE)
    monkeypatch.setattr(eventos, "en_segundo_plano", lambda funcion, *a: funcion(*a))
    monkeypatch.setattr(http.client, "HTTPSConnection", _ConexionFalsa)
    _ConexionFalsa.peticiones = []
    _ConexionFalsa.estado = 201
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    eventos.limpiar()
    avisos.suscribir()
    yield
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    eventos.limpiar()


def _pedido_pagado() -> tuple[int, str]:
    creado = pedidos_service.crear_pedido([(1, 1)])
    pedidos_service.confirmar_pago(creado.pedido_id)
    return creado.pedido_id, creado.token_consulta


def _registrar(pedido_id: int, token: str | None, endpoint: str = ENDPOINT):
    cabeceras = {"X-Token-Pedido": token} if token else {}
    return client.post(
        f"/v1/pedidos/{pedido_id}/aviso-push", json={"endpoint": endpoint}, headers=cabeceras
    )


def _avanzar(pedido_id: int, *estados: EstadoPedido):
    for estado in estados:
        pedidos_service.avanzar_estado(pedido_id, estado, establecimiento_id=1)


# --- La clave ---------------------------------------------------------------


def test_sin_clave_el_despliegue_no_manda_avisos(monkeypatch):
    monkeypatch.delenv("PIDEUTB_VAPID_CLAVE_PRIVADA")

    assert client.get("/v1/avisos/clave-publica").status_code == 404


@pytest.mark.parametrize("mala", ["PIDEUTB_VAPID_CLAVE_PRIVADA=abc", "AAAA", "no*es*base64!"])
def test_una_clave_mal_pegada_se_ignora_sin_dar_un_500(monkeypatch, mala):
    monkeypatch.setenv("PIDEUTB_VAPID_CLAVE_PRIVADA", mala)

    assert client.get("/v1/avisos/clave-publica").status_code == 404


def test_la_clave_publica_es_un_punto_de_la_curva_sin_comprimir():
    respuesta = client.get("/v1/avisos/clave-publica")

    crudo = _de_base64url(respuesta.json()["clave_publica"])
    assert respuesta.status_code == 200
    assert len(crudo) == 65 and crudo[0] == 4


def test_la_firma_es_un_jwt_es256_que_se_puede_verificar():
    """Si esto falla, ningún servicio de push acepta nada, y no se vería en otro sitio."""
    autorizacion = avisos.firmar("https://fcm.googleapis.com")

    assert autorizacion.startswith("vapid t=")
    jwt, clave = autorizacion.removeprefix("vapid t=").split(", k=")
    cabecera, cuerpo, firma = jwt.split(".")

    assert json.loads(_de_base64url(cabecera)) == {"typ": "JWT", "alg": "ES256"}
    afirmaciones = json.loads(_de_base64url(cuerpo))
    assert afirmaciones["aud"] == "https://fcm.googleapis.com"
    assert afirmaciones["sub"].startswith(("https://", "mailto:"))
    assert time.time() < afirmaciones["exp"] <= time.time() + 3600

    crudo = _de_base64url(firma)
    assert len(crudo) == 64
    publica = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), _de_base64url(clave))
    publica.verify(
        utils.encode_dss_signature(
            int.from_bytes(crudo[:32], "big"), int.from_bytes(crudo[32:], "big")
        ),
        f"{cabecera}.{cuerpo}".encode(),
        ec.ECDSA(hashes.SHA256()),
    )


# --- Quién puede pedirlo ----------------------------------------------------


def test_con_el_token_del_pedido_se_registra():
    pedido_id, token = _pedido_pagado()

    assert _registrar(pedido_id, token).status_code == 204


@pytest.mark.parametrize("token", [None, "x" * 32])
def test_sin_el_token_es_como_si_el_pedido_no_existiera(token):
    pedido_id, _ = _pedido_pagado()

    assert _registrar(pedido_id, token).status_code == 404
    assert pedidos_repo._PEDIDOS[pedido_id].aviso_push_endpoint is None


@pytest.mark.parametrize(
    "direccion",
    [
        "http://fcm.googleapis.com/fcm/send/a",
        "https://localhost/interno",
        "https://127.0.0.1:8000/v1/demo/reiniciar",
        "https://169.254.169.254/latest/meta-data",
        "https://fcm.googleapis.com.atacante.com/a",
        "https://atacantefcm.googleapis.com/a",
        "https://usuario@fcm.googleapis.com/a",
        "https://fcm.googleapis.com:8443/a",
        "https://atacante.com/.push.apple.com",
        "no es una url",
    ],
)
def test_solo_se_acepta_un_servicio_de_push_conocido(direccion):
    """Es nuestro servidor quien hace la petición: sin esto, llamaría a cualquier sitio."""
    pedido_id, token = _pedido_pagado()

    assert _registrar(pedido_id, token, direccion).status_code == 422


@pytest.mark.parametrize(
    "direccion",
    [
        "https://fcm.googleapis.com/fcm/send/a",
        "https://web.push.apple.com/a",
        "https://updates.push.services.mozilla.com/wpush/v2/a",
        "https://wns2-par02p.notify.windows.com/w/?token=a",
    ],
)
def test_se_aceptan_los_de_los_navegadores_de_verdad(direccion):
    pedido_id, token = _pedido_pagado()

    assert _registrar(pedido_id, token, direccion).status_code == 204


def test_un_pedido_ya_listo_no_tiene_nada_que_avisar():
    pedido_id, token = _pedido_pagado()
    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert _registrar(pedido_id, token).status_code == 409


# --- A dónde sale y cuántas veces -------------------------------------------


def test_al_quedar_listo_sale_un_aviso_vacio_y_firmado():
    pedido_id, token = _pedido_pagado()
    _registrar(pedido_id, token)

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION)
    assert _ConexionFalsa.peticiones == [], "Todavía no está listo."

    _avanzar(pedido_id, EstadoPedido.LISTO_PARA_RECOGER)

    assert len(_ConexionFalsa.peticiones) == 1
    peticion = _ConexionFalsa.peticiones[0]
    assert peticion["anfitrion"] == "fcm.googleapis.com"
    assert peticion["metodo"] == "POST"
    assert peticion["ruta"] == "/fcm/send/abc123?x=1"
    assert peticion["cabeceras"]["Authorization"].startswith("vapid t=")
    assert peticion["cabeceras"]["Content-Length"] == "0"
    assert int(peticion["cabeceras"]["TTL"]) > 0


def test_la_direccion_se_borra_al_usarla():
    pedido_id, token = _pedido_pagado()
    _registrar(pedido_id, token)

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert pedidos_repo._PEDIDOS[pedido_id].aviso_push_endpoint is None


def test_sin_registrar_nada_no_sale_nada():
    pedido_id, _ = _pedido_pagado()

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert _ConexionFalsa.peticiones == []


def test_un_pedido_cancelado_olvida_la_direccion_sin_avisar():
    pedido_id, token = _pedido_pagado()
    _registrar(pedido_id, token)

    _avanzar(pedido_id, EstadoPedido.CANCELADO)

    assert _ConexionFalsa.peticiones == []
    assert pedidos_repo._PEDIDOS[pedido_id].aviso_push_endpoint is None


@pytest.mark.parametrize("estado", [404, 410, 500])
def test_un_servicio_que_rechaza_el_aviso_no_afecta_al_pedido(estado):
    _ConexionFalsa.estado = estado
    pedido_id, token = _pedido_pagado()
    _registrar(pedido_id, token)

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert pedidos_repo._PEDIDOS[pedido_id].estado is EstadoPedido.LISTO_PARA_RECOGER


def test_una_red_caida_no_afecta_al_pedido(monkeypatch, caplog):
    def sin_red(*_, **__):
        raise OSError("sin red")

    monkeypatch.setattr(http.client, "HTTPSConnection", sin_red)
    pedido_id, token = _pedido_pagado()
    _registrar(pedido_id, token)

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert pedidos_repo._PEDIDOS[pedido_id].estado is EstadoPedido.LISTO_PARA_RECOGER
    assert "aviso_no_enviado" in caplog.text
    assert "abc123" not in caplog.text, "La dirección permite escribirle a ese teléfono."


def test_una_direccion_rara_en_la_base_tampoco_sale(monkeypatch):
    """Lo guardado entró validado, y se vuelve a mirar antes de llamarla."""
    pedido_id, _ = _pedido_pagado()
    pedidos_repo.guardar_aviso_push(pedido_id, "https://169.254.169.254/x")

    _avanzar(pedido_id, EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER)

    assert _ConexionFalsa.peticiones == []
