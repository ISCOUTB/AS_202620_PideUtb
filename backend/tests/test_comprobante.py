"""El comprobante por correo: qué dice, cuándo sale, y que nunca estorbe al pedido."""
import logging
import smtplib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app import comprobante, correo, eventos
from app.main import app
from app.pagos import repository as pagos_repo
from app.pagos import service as pagos_service
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pedidos import repository as pedidos_repo
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import ComprobanteDePedido, EstadoPedido, LineaPublicada
from app.usuarios.contracts import EstablecimientoPublico

client = TestClient(app)

BOGOTA = ZoneInfo("America/Bogota")
CORREO = "ana@example.com"


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    """Sin hilos en las pruebas: lo que se manda, se manda antes de seguir."""
    monkeypatch.setattr(eventos, "en_segundo_plano", lambda funcion, *a: funcion(*a))
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    pagos_repo._INTENTOS.clear()
    eventos.limpiar()
    comprobante.suscribir()
    yield
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    pagos_repo._INTENTOS.clear()
    eventos.limpiar()


@pytest.fixture
def buzon(monkeypatch):
    """Lo que se habría enviado. Con servidor configurado, sin red."""
    enviados: list[dict] = []
    monkeypatch.setenv("PIDEUTB_SMTP_HOST", "correo.example.com")
    monkeypatch.setattr(correo, "enviar", lambda **campos: enviados.append(campos))
    return enviados


def _datos(**cambios) -> ComprobanteDePedido:
    campos = {
        "pedido_id": 12,
        "establecimiento_id": 5,
        "lineas": [
            LineaPublicada(
                item_id=101,
                nombre_item="Costillitas de cerdo ahumadas",
                precio_unitario_centavos=2980000,
                cantidad=2,
                total_linea_centavos=5960000,
            ),
        ],
        "total_centavos": 5960000,
        "codigo_canje": "K7M2X9",
        "numero_comprobante": 37,
        "pagado_en": datetime(2026, 11, 4, 19, 35, tzinfo=timezone.utc),
        "hora_recogida": None,
        "nombre_cliente": "Ana",
        "correo_cliente": CORREO,
    }
    return ComprobanteDePedido(**{**campos, **cambios})


ESTABLECIMIENTO = EstablecimientoPublico(
    establecimiento_id=5, nombre="El Asao", activo=True, ubicacion="Cafetería central"
)


def _redactar(**cambios):
    return comprobante.redactar(_datos(**cambios), ESTABLECIMIENTO, MetodoDePago.NEQUI)


def _pedido_con_cobro(**datos_cliente) -> tuple[int, str]:
    pedido = pedidos_service.crear_pedido([(1, 2)], **datos_cliente)
    intento = pagos_service.iniciar_intento(pedido.pedido_id, MetodoDePago.NEQUI)
    return pedido.pedido_id, intento.referencia_pago


# --- Qué dice ---------------------------------------------------------------


@pytest.mark.parametrize(
    "dato",
    [
        "PideUTB",
        "El Asao",
        "Cafetería central",
        "K7M2X9",
        "PU-000037",
        "04/11/2026 14:35",
        "Ana",
        CORREO,
        "Costillitas de cerdo ahumadas",
        "$29.800",
        "$59.600",
        "Nequi",
    ],
)
def test_el_comprobante_trae_lo_que_tiene_que_traer(dato):
    """En las dos versiones, y con la hora en Bogotá aunque se guarde en UTC."""
    _, texto, html = _redactar()

    assert dato in html
    assert dato in texto


def test_la_hora_de_recogida_solo_aparece_si_se_programo():
    _, texto_sin, html_sin = _redactar()
    _, texto_con, html_con = _redactar(
        hora_recogida=datetime(2026, 11, 4, 14, 30, tzinfo=BOGOTA)
    )

    assert "Hora de recogida" not in html_sin and "Hora de recogida" not in texto_sin
    assert "Hora de recogida" in html_con and "14:30" in html_con
    assert "14:30" in texto_con


def test_lo_que_escribe_el_cliente_no_entra_como_html():
    """El nombre lo teclea cualquiera, y el comprobante lo abre su buzón."""
    _, _, html = _redactar(nombre_cliente='<img src=x onerror="alert(1)">')

    assert "<img" not in html
    assert "&lt;img" in html


def test_no_se_presenta_como_factura_electronica_de_la_dian():
    """Parecerse sí; afirmarlo sería decir algo falso en un papel de dinero."""
    _, texto, html = _redactar()

    assert "COMPROBANTE DE PAGO" in html
    assert "no reemplaza una factura electrónica" in html
    assert "no reemplaza una factura electrónica" in texto


def test_el_html_sirve_en_un_cliente_de_correo():
    """Gmail y Outlook descartan hojas de estilo: todo va en cada etiqueta."""
    _, _, html = _redactar()

    assert "<style" not in html
    assert "<link" not in html
    assert "<script" not in html
    assert 'role="presentation"' in html


# --- Cuándo sale ------------------------------------------------------------


def test_al_confirmarse_el_pago_sale_uno_al_correo_del_cliente(buzon):
    _, referencia = _pedido_con_cobro(correo_cliente=CORREO, nombre_cliente="Ana")

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert len(buzon) == 1
    assert buzon[0]["para"] == CORREO
    assert "Nequi" in buzon[0]["html"]


def test_un_aviso_repetido_de_la_pasarela_no_manda_otro(buzon):
    """La pasarela entrega al menos una vez, y el correo no se puede repetir."""
    _, referencia = _pedido_con_cobro(correo_cliente=CORREO)

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)
    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert len(buzon) == 1


def test_un_pago_rechazado_no_manda_nada(buzon):
    _, referencia = _pedido_con_cobro(correo_cliente=CORREO)

    pagos_service.procesar_evento(referencia, EstadoPago.RECHAZADO)

    assert buzon == []


def test_sin_correo_no_se_manda_nada_y_el_pedido_sigue_igual(buzon):
    pedido_id, referencia = _pedido_con_cobro()

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert buzon == []
    assert pedidos_service.obtener_pedido(pedido_id).estado is EstadoPedido.PAGADO


def test_sin_servidor_de_correo_ni_se_intenta(monkeypatch):
    monkeypatch.delenv("PIDEUTB_SMTP_HOST", raising=False)
    monkeypatch.setattr(
        correo, "enviar", lambda **_: pytest.fail("Se intentó enviar sin servidor")
    )
    _, referencia = _pedido_con_cobro(correo_cliente=CORREO)

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)


def test_cada_comprobante_lleva_su_consecutivo(buzon):
    for _ in range(2):
        _, referencia = _pedido_con_cobro(correo_cliente=CORREO)
        pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    numeros = {p.numero_comprobante for p in pedidos_repo._PEDIDOS.values()}
    assert len(numeros) == 2


# --- Que nunca estorbe ------------------------------------------------------


def test_un_correo_que_falla_no_toca_el_pedido(monkeypatch, caplog):
    """Es la promesa entera: se registra sin el correo, y el pago sigue valiendo."""
    monkeypatch.setenv("PIDEUTB_SMTP_HOST", "correo.example.com")

    def explota(**_):
        raise smtplib.SMTPRecipientsRefused({CORREO: (550, b"no existe")})

    monkeypatch.setattr(correo, "enviar", explota)
    pedido_id, referencia = _pedido_con_cobro(correo_cliente=CORREO)

    with caplog.at_level(logging.WARNING, logger="pideutb"):
        pedido, duplicado = pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert duplicado is False
    assert pedido.estado is EstadoPedido.PAGADO
    assert pedido.codigo_canje
    assert "comprobante_no_enviado" in caplog.text
    assert CORREO not in caplog.text


def test_el_trabajo_en_segundo_plano_no_deja_escapar_nada(monkeypatch):
    """La versión de verdad, con su hilo: un fallo ahí no le llega a nadie."""
    monkeypatch.undo()

    def explota():
        raise RuntimeError("fallo")

    eventos.en_segundo_plano(explota)
    eventos._HILOS.submit(lambda: None).result(timeout=5)


# --- Los datos no salen por la API ------------------------------------------


def test_ninguna_respuesta_publica_los_datos_del_cliente():
    """Ni al crear, ni al consultar. Son para mandar el correo y para nada más."""
    respuesta = client.post(
        "/v1/pedidos",
        json={
            "lineas": [{"item_id": 1}],
            "correo_cliente": CORREO,
            "nombre_cliente": "Ana Secreta",
        },
    )
    creado = respuesta.json()
    consultado = client.get(
        f"/v1/pedidos/{creado['pedido_id']}",
        headers={"X-Token-Pedido": creado["token_consulta"]},
    )

    for cuerpo in (respuesta.text, consultado.text):
        assert CORREO not in cuerpo
        assert "Ana Secreta" not in cuerpo


@pytest.mark.parametrize(
    "malo",
    ["sin-arroba", "a@b", "a b@c.co", "ana@example.com\nBcc: otro@example.com", "@b.co"],
)
def test_un_correo_mal_formado_se_rechaza_antes_de_guardarlo(malo):
    """Los saltos de línea son los que permitirían colar otra cabecera."""
    respuesta = client.post(
        "/v1/pedidos", json={"lineas": [{"item_id": 1}], "correo_cliente": malo}
    )

    assert respuesta.status_code == 422


# --- El transporte ----------------------------------------------------------


class _ServidorFalso:
    """Un `smtplib.SMTP` que recuerda lo que le hicieron."""

    def __init__(self, *_, starttls=True, **__):
        self._starttls = starttls
        self.llamadas: list[str] = []
        self.mensaje = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def ehlo(self):
        self.llamadas.append("ehlo")

    def has_extn(self, nombre):
        return nombre == "starttls" and self._starttls

    def starttls(self, **_):
        self.llamadas.append("starttls")

    def login(self, *_):
        self.llamadas.append("login")

    def send_message(self, mensaje):
        self.llamadas.append("enviar")
        self.mensaje = mensaje


def _enviar_con(monkeypatch, servidor, usuario="cuenta"):
    monkeypatch.setenv("PIDEUTB_SMTP_HOST", "correo.example.com")
    monkeypatch.setenv("PIDEUTB_SMTP_USUARIO", usuario)
    monkeypatch.setenv("PIDEUTB_SMTP_CONTRASENA", "x")
    monkeypatch.setenv("PIDEUTB_SMTP_REMITENTE", "PideUTB <no-responder@example.com>")
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: servidor)
    correo.enviar(para=CORREO, asunto="Asunto", texto="texto", html="<p>html</p>")


def test_cifra_antes_de_mandar_las_credenciales(monkeypatch):
    servidor = _ServidorFalso()

    _enviar_con(monkeypatch, servidor)

    assert servidor.llamadas.index("starttls") < servidor.llamadas.index("login")
    assert servidor.mensaje["To"] == CORREO
    assert servidor.mensaje["From"] == "PideUTB <no-responder@example.com>"
    assert servidor.mensaje.get_body(("html",)) is not None
    assert servidor.mensaje.get_body(("plain",)) is not None


def test_sin_cifrado_las_credenciales_no_salen(monkeypatch):
    """Un servidor que no ofrece STARTTLS puede ser alguien en medio."""
    servidor = _ServidorFalso(starttls=False)

    with pytest.raises(smtplib.SMTPNotSupportedError):
        _enviar_con(monkeypatch, servidor)

    assert "login" not in servidor.llamadas
    assert "enviar" not in servidor.llamadas
