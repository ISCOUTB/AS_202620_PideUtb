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
    respuesta = client.post("/v1/pedidos", json={"lineas": [{"item_id": item_id, "cantidad": cantidad}]})
    assert respuesta.status_code == 201, respuesta.text
    return _recordar(respuesta.json())

# --------------------------------------------------------------------------
# El token de consulta
#
# Desde el contrato 4.0.0, `GET /v1/pedidos/{id}` exige el token que se entregó
# al crear el pedido: los identificadores son secuenciales y sin token
# cualquiera podía recorrerlos y cosechar los códigos de canje.
#
# Las pruebas lo guardan como lo guarda el cliente —quien crea el pedido se
# queda con su token— en vez de buscarlo en la base, que sería probar otra cosa.
# --------------------------------------------------------------------------

_TOKENS: dict[int, str] = {}


def _recordar(creado: dict) -> dict:
    """Anota el token de un pedido recién creado y devuelve la respuesta."""
    _TOKENS[creado["pedido_id"]] = creado["token_consulta"]
    return creado


def _consultar(pedido_id: int):
    """`GET /v1/pedidos/{id}` con el token de ese pedido."""
    return client.get(
        f"/v1/pedidos/{pedido_id}",
        headers={"X-Token-Pedido": _TOKENS.get(pedido_id, "sin-token")},
    )



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


PASARELA_SIMULADA = "http://127.0.0.1:8080/pasarela.html"


@pytest.fixture
def con_pasarela_simulada(monkeypatch):
    """Enciende la pasarela de mentira para una prueba."""
    monkeypatch.setenv("PIDEUTB_URL_PASARELA_SIMULADA", PASARELA_SIMULADA)


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

    consultado = _consultar(pedido["pedido_id"]).json()
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

    codigo = _consultar(pedido["pedido_id"]).json()["codigo_canje"]
    assert codigo is not None


def test_el_codigo_de_canje_no_cambia_entre_reintentos():
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    _enviar_evento(intento["referencia_pago"], "aprobado")
    primero = _consultar(pedido["pedido_id"]).json()["codigo_canje"]

    _enviar_evento(intento["referencia_pago"], "aprobado")
    segundo = _consultar(pedido["pedido_id"]).json()["codigo_canje"]

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
    conservado = _consultar(pedido["pedido_id"]).json()
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

    consultado = _consultar(pedido["pedido_id"])

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
    assert _consultar(pedido["pedido_id"]).json()["estado"] == "pendiente_pago"


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
        assert _consultar(pedido["pedido_id"]).json()["estado"] == "pagado"
        assert len(recibidos) == 1, (
            "el fallo de un suscriptor tampoco puede impedir que los demás "
            "reciban el evento"
        )
    finally:
        eventos.limpiar()


# --------------------------------------------------------------------------
# La pasarela simulada
#
# Existe para poder recorrer el flujo entero sin una cuenta de comercio. Lo que
# estas pruebas vigilan no es que funcione —eso es lo fácil— sino las dos cosas
# que la harían peligrosa o inútil:
#
# 1. Que **no exista** donde no está configurada. Es la única barrera entre un
#    despliegue de producción y cualquiera que pueda dar un pedido por pagado.
# 2. Que **no se salte el canal asíncrono**. Si la respuesta del botón trajera
#    el pedido ya pagado, la demostración enseñaría una arquitectura distinta
#    de la que ADR-0003 describe, y el sondeo y la idempotencia dejarían de
#    ejercitarse justo donde se miran.
# --------------------------------------------------------------------------

def test_sin_configurar_el_simulador_no_existe():
    """`404`, el mismo que daría una ruta inexistente.

    Un `403` confirmaría que la ruta está ahí y que solo falta la
    configuración adecuada, que es más información de la que hace falta dar.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = client.post(
        f"/v1/pagos/simulador/{intento['referencia_pago']}",
        json={"estado_pago": "aprobado"},
    )

    assert respuesta.status_code == 404
    assert _consultar(pedido["pedido_id"]).json()["estado"] == (
        "pendiente_pago"
    ), "un simulador apagado no puede haber cambiado nada"


def test_sin_configurar_se_cobra_por_la_pasarela_de_verdad():
    """Sin la variable, `url_checkout` sigue apuntando fuera."""
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    assert intento["url_checkout"].startswith("https://sandbox.wompi.co/")


def test_configurada_manda_a_pagar_a_la_pasarela_simulada(con_pasarela_simulada):
    """Y lleva el importe y el método, que es lo que la página tiene que pintar."""
    pedido = _crear_pedido(item_id=1, cantidad=2)
    intento = _abrir_intento(pedido["pedido_id"], metodo="nequi")

    url = intento["url_checkout"]
    assert url.startswith(PASARELA_SIMULADA + "?")
    assert f"referencia={intento['referencia_pago']}" in url
    assert f"monto={pedido['total_centavos']}" in url
    assert "metodo=nequi" in url


def test_el_simulador_no_devuelve_el_pedido_pagado_a_quien_pulsa(
    con_pasarela_simulada,
):
    """**La prueba que protege ADR-0003.**

    Quien pulsa «Pagar» en la pasarela recibe un acuse de recibo, igual que lo
    recibiría la pasarela real. No recibe el código de canje: ese viaja por el
    otro canal, y para verlo hay que consultar el pedido.

    Si alguien «simplifica» el simulador para que devuelva el pedido ya pagado
    —que es la forma más natural de hacerlo si no se piensa en el ADR—, esta
    prueba falla.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = client.post(
        f"/v1/pagos/simulador/{intento['referencia_pago']}",
        json={"estado_pago": "aprobado"},
    )

    assert respuesta.status_code == 202, "acuse de recibo, no resultado"
    assert "codigo_canje" not in respuesta.json()

    # El código existe, pero hay que ir a buscarlo.
    consultado = _consultar(pedido["pedido_id"]).json()
    assert consultado["estado"] == "pagado"
    assert consultado["codigo_canje"]


def test_el_simulador_rechaza_igual_que_la_pasarela(con_pasarela_simulada):
    """Un rechazo deja el pedido esperando pago, no lo cancela."""
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    respuesta = client.post(
        f"/v1/pagos/simulador/{intento['referencia_pago']}",
        json={"estado_pago": "rechazado"},
    )

    assert respuesta.status_code == 202
    consultado = _consultar(pedido["pedido_id"]).json()
    assert consultado["estado"] == "pendiente_pago"
    assert consultado["codigo_canje"] is None


def test_pulsar_dos_veces_no_genera_dos_codigos(con_pasarela_simulada):
    """Entra por `procesar_evento`, así que hereda su idempotencia.

    No es una garantía nueva: es la comprobación de que el simulador usa la
    misma puerta y no una propia.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])
    ruta = f"/v1/pagos/simulador/{intento['referencia_pago']}"

    primera = client.post(ruta, json={"estado_pago": "aprobado"})
    segunda = client.post(ruta, json={"estado_pago": "aprobado"})

    assert primera.json()["duplicado"] is False
    assert segunda.json()["duplicado"] is True

    codigo = _consultar(pedido["pedido_id"]).json()["codigo_canje"]
    assert codigo, "el código se generó una vez"


def test_una_referencia_inventada_no_crea_nada(con_pasarela_simulada):
    respuesta = client.post(
        "/v1/pagos/simulador/pago-inventado", json={"estado_pago": "aprobado"}
    )
    assert respuesta.status_code == 404


def test_el_simulador_no_aparece_en_la_documentacion(con_pasarela_simulada):
    """No es parte del contrato: es un doble del sistema externo.

    Publicarlo lo congelaría en una versión del contrato y obligaría a
    mantenerlo como si alguien de fuera pudiera depender de él.
    """
    rutas = client.get("/openapi.json").json()["paths"]
    assert not [r for r in rutas if "simulador" in r]


# --------------------------------------------------------------------------
# R-11: un rechazo tiene que poder distinguirse de «todavía no»
#
# El pedido queda en `pendiente_pago` en los dos casos, y es lo correcto: un
# cobro rechazado no cancela un pedido, permite reintentarlo. Lo que faltaba era
# que el cliente pudiera enterarse, y por eso se publica el estado del cobro.
# --------------------------------------------------------------------------

def test_tras_un_rechazo_el_pedido_y_el_cobro_dicen_cosas_distintas():
    """**La prueba del hueco.** Es la pareja que lo definía.

    Si el intento dejara de guardar el rechazo, o si el pedido empezara a
    cancelarse por un cobro rechazado, esta prueba falla por un lado o por el
    otro.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(intento["referencia_pago"], "rechazado")

    consultado = _consultar(pedido["pedido_id"]).json()
    cobro = client.get(f"/v1/pagos/intentos/{intento['referencia_pago']}").json()

    assert consultado["estado"] == "pendiente_pago", "el pedido sigue en pie"
    assert consultado["codigo_canje"] is None
    assert cobro["estado_pago"] == "rechazado", "y el cobro dice por qué"


def test_mientras_nadie_confirma_los_dos_dicen_pendiente():
    """El otro lado de la pareja: sin evento, nada ha pasado.

    Sin esta, la de arriba pasaría con un endpoint que devolviera `rechazado`
    siempre.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])

    consultado = _consultar(pedido["pedido_id"]).json()
    cobro = client.get(f"/v1/pagos/intentos/{intento['referencia_pago']}").json()

    assert consultado["estado"] == "pendiente_pago"
    assert cobro["estado_pago"] == "pendiente"


def test_consultar_un_cobro_aprobado():
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(intento["referencia_pago"], "aprobado")

    cobro = client.get(f"/v1/pagos/intentos/{intento['referencia_pago']}").json()

    assert cobro["estado_pago"] == "aprobado"
    assert cobro["pedido_id"] == pedido["pedido_id"]


def test_consultar_un_cobro_no_revela_el_codigo_de_canje():
    """La referencia solo lleva seis dígitos hexadecimales aleatorios.

    No es un secreto fuerte, así que esta respuesta no puede contener nada que
    necesite uno. El código de canje es lo que vale dinero: se presenta en el
    mostrador para llevarse la comida.
    """
    pedido = _crear_pedido()
    intento = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(intento["referencia_pago"], "aprobado")

    cobro = client.get(f"/v1/pagos/intentos/{intento['referencia_pago']}").json()

    assert "codigo_canje" not in cobro
    codigo = _consultar(pedido["pedido_id"]).json()["codigo_canje"]
    assert codigo, "existe, pero no por esta puerta"
    assert codigo not in str(cobro)


def test_consultar_una_referencia_inventada_responde_404():
    assert client.get("/v1/pagos/intentos/pago-inventado").status_code == 404


def test_tras_un_rechazo_se_puede_abrir_otro_cobro_del_mismo_pedido():
    """Reintentar no crea un pedido nuevo: abre otro cobro del que ya existe.

    Es lo que hace útil enterarse del rechazo. El cobro anterior conserva su
    estado —no se reescribe la historia— y el nuevo nace pendiente.
    """
    pedido = _crear_pedido()
    primero = _abrir_intento(pedido["pedido_id"], metodo="tarjeta")
    _enviar_evento(primero["referencia_pago"], "rechazado")

    segundo = _abrir_intento(pedido["pedido_id"], metodo="nequi")

    assert segundo["referencia_pago"] != primero["referencia_pago"]
    assert segundo["pedido_id"] == pedido["pedido_id"], "el mismo pedido"
    assert segundo["estado_pago"] == "pendiente"

    viejo = client.get(f"/v1/pagos/intentos/{primero['referencia_pago']}").json()
    assert viejo["estado_pago"] == "rechazado", "el intento rechazado no se toca"


def test_el_segundo_cobro_aprobado_genera_el_codigo_una_sola_vez():
    """Y el reintento termina donde tenía que terminar."""
    pedido = _crear_pedido()
    primero = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(primero["referencia_pago"], "rechazado")

    segundo = _abrir_intento(pedido["pedido_id"])
    _enviar_evento(segundo["referencia_pago"], "aprobado")

    consultado = _consultar(pedido["pedido_id"]).json()
    assert consultado["estado"] == "pagado"
    assert consultado["codigo_canje"]
