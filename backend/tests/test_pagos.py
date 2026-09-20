"""Pruebas del contexto Pagos y del flujo asíncrono de confirmación.

Cubren lo que la integración asíncrona **obliga** a garantizar y que una
integración síncrona no necesitaría: idempotencia ante reintentos, tolerancia a
que el aviso no llegue nunca, y aislamiento de los fallos del suscriptor.

Cada prueba corresponde a una afirmación concreta de
[ADR-0003](../../docs/adr/0003-estrategia-integracion.md) o del contrato de
eventos `docs/api/asyncapi.yaml`. Si el ADR dice que el sistema tolera X, aquí
está la prueba de que lo tolera.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app import eventos
from app.main import app
from app.pagos import service as pagos_service

client = TestClient(app)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def _crear_pedido(item_id: int = 1, cantidad: int = 1) -> dict:
    respuesta = client.post("/v1/pedidos", json={"item_id": item_id, "cantidad": cantidad})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _abrir_intento(pedido_id: int, metodo: str = "tarjeta") -> dict:
    respuesta = client.post(
        "/v1/pagos/intentos", json={"pedido_id": pedido_id, "metodo": metodo}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _enviar_evento(referencia: str, estado: str, firma: str | None = "válida"):
    """Envía un webhook tal como lo haría la pasarela.

    El cuerpo se serializa una sola vez y se firma **esos mismos bytes**: es
    como funciona la verificación real, y usar el atajo `json=` haría que
    httpx reserializara y la firma dejara de corresponder.
    """
    cuerpo = json.dumps(
        {
            "evento": "transaccion.actualizada",
            "referencia_pago": referencia,
            "estado_pago": estado,
        }
    ).encode()

    cabeceras = {"Content-Type": "application/json"}
    if firma == "válida":
        cabeceras["X-Firma-Evento"] = pagos_service.firmar(cuerpo)
    elif firma is not None:
        cabeceras["X-Firma-Evento"] = firma

    return client.post("/v1/pagos/eventos", content=cuerpo, headers=cabeceras)


# --------------------------------------------------------------------------
# Operación síncrona
# --------------------------------------------------------------------------

def test_iniciar_el_pago_devuelve_a_donde_ir_pero_no_el_resultado():
    """La operación síncrona promete lo que puede prometer, y nada más.

    En el instante en que responde, el cobro todavía no ha ocurrido. Devolver
    `estado_pago: pendiente` no es una carencia: es la descripción honesta del
    estado del mundo en ese momento.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    assert intento["estado_pago"] == "pendiente"
    assert intento["monto_centavos"] == pedido["total_centavos"]
    assert intento["url_checkout"].startswith("https://")


def test_abrir_el_pago_dos_veces_no_genera_dos_cobros():
    """Idempotencia de la operación síncrona.

    Sin esto, pulsar «Pagar» dos veces —o un reintento del navegador— dejaría
    dos transacciones vivas sobre el mismo pedido, y solo una acabaría
    reconciliada.
    """
    pedido = _crear_pedido()

    primero = _abrir_intento(pedido["pedido_id"])
    segundo = _abrir_intento(pedido["pedido_id"])

    assert primero["referencia_pago"] == segundo["referencia_pago"]


def test_no_se_puede_cobrar_un_pedido_ya_pagado():
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(intento["referencia_pago"], "aprobado")

    respuesta = client.post(
        "/v1/pagos/intentos", json={"pedido_id": pedido["pedido_id"], "metodo": "pse"}
    )

    assert respuesta.status_code == 409


def test_cobrar_un_pedido_inexistente_responde_404():
    respuesta = client.post(
        "/v1/pagos/intentos", json={"pedido_id": 999999, "metodo": "tarjeta"}
    )
    assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# Punto de entrada asíncrono
# --------------------------------------------------------------------------

def test_el_evento_aprobado_confirma_el_pedido_y_genera_el_codigo():
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = _enviar_evento(intento["referencia_pago"], "aprobado")

    assert respuesta.status_code == 202, "el webhook acusa recibo, no confirma efecto"
    acuse = respuesta.json()
    assert acuse["estado"] == "pagado"
    assert acuse["duplicado"] is False

    consultado = client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()
    assert consultado["estado"] == "pagado"
    assert consultado["codigo_canje"] is not None
    assert len(consultado["codigo_canje"]) == 6


def test_el_mismo_evento_repetido_no_genera_un_segundo_codigo():
    """La garantía que la entrega al-menos-una-vez hace obligatoria.

    La pasarela reintenta si no recibe `2xx` dentro de su plazo, así que el
    mismo aviso llegará repetido. Si cada llegada generase un código nuevo, el
    usuario tendría en pantalla uno que ya no sirve.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    primera = _enviar_evento(intento["referencia_pago"], "aprobado")
    segunda = _enviar_evento(intento["referencia_pago"], "aprobado")
    tercera = _enviar_evento(intento["referencia_pago"], "aprobado")

    assert primera.json()["duplicado"] is False
    assert segunda.json()["duplicado"] is True
    assert tercera.json()["duplicado"] is True

    assert all(r.status_code == 202 for r in (primera, segunda, tercera)), (
        "un duplicado no es un error del emisor: se responde 202 igualmente"
    )

    codigo = client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()["codigo_canje"]
    assert codigo is not None


def test_el_codigo_de_canje_no_cambia_entre_reintentos():
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    _enviar_evento(intento["referencia_pago"], "aprobado")
    primero = client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()["codigo_canje"]

    _enviar_evento(intento["referencia_pago"], "aprobado")
    segundo = client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()["codigo_canje"]

    assert primero == segundo


def test_un_pago_rechazado_conserva_el_pedido():
    """ESC-05: ante un error de pago, el pedido debe conservarse.

    El usuario no pierde lo que había elegido; puede reintentar con otro
    método sin volver a armar el pedido.
    """
    pedido = _crear_pedido(item_id=2, cantidad=2)
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = _enviar_evento(intento["referencia_pago"], "rechazado")

    assert respuesta.status_code == 202
    conservado = client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()
    assert conservado["estado"] == "pendiente_pago"
    assert conservado["total_centavos"] == pedido["total_centavos"]
    assert conservado["codigo_canje"] is None


def test_si_el_evento_no_llega_nunca_el_pedido_queda_consultable():
    """El modo de fallo que ADR-0003 acepta a cambio de desacoplar.

    No se simula «que no llegue» con un temporizador: simplemente no se envía
    el evento. Lo que se comprueba es que el usuario no queda sin información
    —el estado es consultable y es el correcto—, que es la diferencia entre una
    degradación y un cuelgue.
    """
    pedido = _crear_pedido()
    _abrir_intento(pedido["pedido_id"])

    consultado = client.get(f"/v1/pedidos/{pedido['pedido_id']}")

    assert consultado.status_code == 200
    assert consultado.json()["estado"] == "pendiente_pago"


# --------------------------------------------------------------------------
# Seguridad del canal de entrada
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "firma, motivo",
    [
        (None, "sin cabecera de firma"),
        ("", "firma vacía"),
        ("0" * 64, "firma con la longitud correcta pero incorrecta"),
    ],
)
def test_un_evento_sin_firma_valida_se_rechaza(firma, motivo):
    """Sin esto, el webhook sería un punto público para marcar pedidos pagados.

    Es la consecuencia directa de exponer un endpoint que cualquiera puede
    invocar: en la integración síncrona el interlocutor es nuestro propio
    frontend, aquí es Internet.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = _enviar_evento(intento["referencia_pago"], "aprobado", firma=firma)

    assert respuesta.status_code == 401, motivo
    assert client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()["estado"] == "pendiente_pago"


def test_un_evento_con_referencia_desconocida_responde_404():
    """La referencia la generamos nosotros, así que una que no conocemos es falsa.

    Si la generase la pasarela no habría forma de distinguir un aviso legítimo
    de uno inventado.
    """
    respuesta = _enviar_evento("pago-inexistente-000000", "aprobado")
    assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# Canal interno de eventos
# --------------------------------------------------------------------------

def test_confirmar_el_pago_publica_el_evento_interno_una_sola_vez():
    """El contrato de `pideutb.pedidos.pagados` promete uno por pedido."""
    recibidos: list[dict] = []
    eventos.limpiar()
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, recibidos.append)

    try:
        pedido = _crear_pedido()
        intento = _abrir_intento(pedido["pedido_id"])

        _enviar_evento(intento["referencia_pago"], "aprobado")
        _enviar_evento(intento["referencia_pago"], "aprobado")

        assert len(recibidos) == 1, (
            "un reintento de la pasarela no puede producir un segundo "
            "`pedido.pagado`: el panel prepararía el pedido dos veces"
        )
        assert recibidos[0]["pedido_id"] == pedido["pedido_id"]
        assert recibidos[0]["establecimiento_id"] == pedido["establecimiento_id"]
        assert recibidos[0]["codigo_canje"] is not None
    finally:
        eventos.limpiar()


def test_un_suscriptor_que_falla_no_tumba_el_cobro():
    """La propiedad que distingue publicar de llamar.

    Si el panel del establecimiento revienta, el cobro ya ocurrió y sigue
    siendo válido. Hacer que el pago dependa de que el panel funcione
    recrearía el acoplamiento temporal que la decisión evita — con la
    diferencia de que ahora estaría escondido.
    """
    def suscriptor_roto(_mensaje):
        raise RuntimeError("el panel del establecimiento está caído")

    recibidos: list[dict] = []
    eventos.limpiar()
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, suscriptor_roto)
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, recibidos.append)

    try:
        pedido = _crear_pedido()
        intento = _abrir_intento(pedido["pedido_id"])

        respuesta = _enviar_evento(intento["referencia_pago"], "aprobado")

        assert respuesta.status_code == 202
        assert client.get(f"/v1/pedidos/{pedido['pedido_id']}").json()["estado"] == "pagado"
        assert len(recibidos) == 1, (
            "el fallo de un suscriptor tampoco puede impedir que los demás "
            "reciban el evento"
        )
    finally:
        eventos.limpiar()
