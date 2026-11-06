"""La hora de recogida: opcional, futura y dentro del horario.

El reloj se fija en cada prueba. Una prueba que dependa de la hora real pasa por la
mañana y falla por la tarde, que es la peor forma de fallar.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.autenticacion import personal_de_establecimiento, usuario_actual
from app.main import app
from app.pagos import repository as pagos_repo
from app.pedidos import repository, service
from app.pedidos.contracts import EstadoPedido
from app.usuarios import service as cuentas_service
from app.usuarios.contracts import EstablecimientoPublico, RolUsuario, UsuarioAutenticado

client = TestClient(app)

BOGOTA = ZoneInfo("America/Bogota")

#: Un miércoles a las 10:00. El establecimiento 1 atiende de 07:00 a 18:00.
AHORA = datetime(2026, 11, 4, 10, 0, 20, tzinfo=BOGOTA)

MOSTRADOR = UsuarioAutenticado(
    usuario_id=1,
    correo="mostrador@utb.edu.co",
    rol=RolUsuario.PERSONAL_ESTABLECIMIENTO,
    establecimiento_id=1,
)


@pytest.fixture(autouse=True)
def reloj_y_almacenamiento(monkeypatch):
    monkeypatch.setattr(service, "_ahora", lambda: AHORA)
    repository._PEDIDOS.clear()
    repository._contador = 0
    pagos_repo._INTENTOS.clear()
    yield
    repository._PEDIDOS.clear()
    repository._contador = 0
    pagos_repo._INTENTOS.clear()


def _pedir(**campos):
    return client.post("/v1/pedidos", json={"lineas": [{"item_id": 1}], **campos})


def test_sin_hora_el_pedido_es_para_ya():
    """El comportamiento de siempre: no elegir nada sigue siendo pedir."""
    respuesta = _pedir()

    assert respuesta.status_code == 201
    assert respuesta.json()["hora_recogida"] is None


def test_una_hora_futura_dentro_del_horario_se_acepta_para_hoy():
    respuesta = _pedir(hora_recogida="14:30")

    assert respuesta.status_code == 201
    assert respuesta.json()["hora_recogida"] == "2026-11-04T14:30:00-05:00"


@pytest.mark.parametrize(
    "hora, por_que",
    [
        ("09:00", "ya pasó"),
        ("10:00", "es este mismo minuto: empezó hace veinte segundos"),
        ("06:59", "antes de abrir"),
        ("18:00", "el cierre no cuenta, igual que el final de una promoción"),
        ("23:30", "después de cerrar"),
    ],
)
def test_una_hora_que_no_vale_se_rechaza_con_409_y_no_crea_el_pedido(hora, por_que):
    respuesta = _pedir(hora_recogida=hora)

    assert respuesta.status_code == 409, por_que
    assert repository._PEDIDOS == {}


def test_la_apertura_si_cuenta(monkeypatch):
    monkeypatch.setattr(
        service, "_ahora", lambda: datetime(2026, 11, 4, 6, 0, tzinfo=BOGOTA)
    )

    assert _pedir(hora_recogida="07:00").status_code == 201


@pytest.mark.parametrize("hora", ["25:00", "14:60", "2:30", "14:30:00", "mañana", ""])
def test_una_hora_mal_escrita_es_422(hora):
    assert _pedir(hora_recogida=hora).status_code == 422


def test_sin_horario_publicado_no_se_puede_programar(monkeypatch):
    """No se inventa un horario: se dice que no hay."""
    monkeypatch.setattr(
        cuentas_service,
        "obtener_establecimiento",
        lambda _: EstablecimientoPublico(establecimiento_id=1, nombre="X", activo=True),
    )

    respuesta = _pedir(hora_recogida="14:30")

    assert respuesta.status_code == 409
    assert "horario" in respuesta.json()["detail"]


def test_el_mostrador_ve_la_hora_programada():
    app.dependency_overrides[personal_de_establecimiento] = lambda: MOSTRADOR
    app.dependency_overrides[usuario_actual] = lambda: MOSTRADOR
    try:
        programado = _pedir(hora_recogida="14:30").json()["pedido_id"]
        inmediato = _pedir().json()["pedido_id"]

        cola = {p["pedido_id"]: p for p in client.get("/v1/pedidos").json()["pedidos"]}
    finally:
        app.dependency_overrides.clear()

    assert cola[programado]["hora_recogida"] == "2026-11-04T14:30:00-05:00"
    assert cola[inmediato]["hora_recogida"] is None


def test_avanzar_el_estado_no_borra_la_hora():
    """`guardar` no toca la columna, y el modelo en memoria la conserva."""
    pedido = service.crear_pedido([(1, 1)], hora_recogida="14:30")
    service.confirmar_pago(pedido.pedido_id)

    avanzado = service.avanzar_estado(
        pedido.pedido_id, EstadoPedido.EN_PREPARACION, establecimiento_id=1
    )

    assert avanzado.hora_recogida == "2026-11-04T14:30:00-05:00"


def test_la_carta_publica_el_horario_con_el_que_se_orienta_el_sitio():
    carta = client.get("/v1/menu/establecimientos/1/items").json()

    assert (carta["hora_apertura"], carta["hora_cierre"]) == ("07:00", "18:00")


def test_un_establecimiento_sin_horario_lo_publica_nulo():
    """El 3 está «cerrado temporalmente»: no hay hora que ofrecer."""
    carta = client.get("/v1/menu/establecimientos/3/items").json()

    assert (carta["hora_apertura"], carta["hora_cierre"]) == (None, None)
