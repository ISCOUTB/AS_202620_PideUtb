"""Los fallos parciales de las integraciones, y qué hace el sistema con cada uno.

Cubre la tabla de [arc42 §6.7](../../docs/arc42/arc42.md#fallos-parciales).

### Qué distingue este archivo de `test_pagos.py`

`test_pagos.py` prueba el **flujo**: qué pasa cuando la pasarela rechaza, cuando
el evento no llega, cuando llega repetido. Son fallos *del otro extremo*, y el
sistema los ve como respuestas.

Aquí se prueban los fallos **a mitad de una operación nuestra**: el proceso que
muere entre dos escrituras, el suscriptor que se pierde un evento, la ventana
que queda abierta cuando una de las dos partes se escribió y la otra no. No los
causa nadie de fuera; los causa que el sistema esté hecho de piezas.

La diferencia práctica es que estos **no se ven desde fuera**. Nadie recibe un
error: el pedido queda pagado, el cliente se lleva su comida y la contabilidad
dice otra cosa. Por eso cada uno necesita algo que lo haga visible, y eso es lo
que se prueba aquí.
"""
from __future__ import annotations

import pytest

from app import eventos
from app.pagos import repository as pagos_repo
from app.pagos import service as pagos_service
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pedidos import repository as pedidos_repo
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import EstadoPedido


@pytest.fixture(autouse=True)
def almacenamiento_limpio():
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    pagos_repo._INTENTOS.clear()
    eventos.limpiar()
    yield
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    pagos_repo._INTENTOS.clear()
    eventos.limpiar()


def _pedido_con_intento() -> tuple[int, str]:
    """Un pedido con su cobro abierto, listo para recibir el aviso."""
    pedido = pedidos_service.crear_pedido([(1, 1)])
    intento = pagos_service.iniciar_intento(pedido.pedido_id, MetodoDePago.NEQUI)
    return pedido.pedido_id, intento.referencia_pago


# ---------------------------------------------------------------------------
# La ventana entre las dos escrituras de `procesar_evento`
# ---------------------------------------------------------------------------

def test_sin_fallos_la_conciliacion_no_encuentra_nada():
    """El caso sano, y el que da valor al resto.

    Sin esta prueba, una conciliación que devolviera siempre lista vacía
    —porque está rota— pasaría por un sistema impecable.
    """
    pedido_id, referencia = _pedido_con_intento()
    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert pagos_service.conciliar() == []
    assert pagos_repo.buscar_por_referencia(referencia).estado_pago is EstadoPago.APROBADO


def test_un_corte_entre_las_dos_escrituras_deja_el_intento_descolgado(monkeypatch):
    """Reproduce el fallo parcial en vez de describirlo.

    `procesar_evento` confirma el pedido y **después** marca el intento. Se
    simula que el proceso muere en medio haciendo fallar la segunda escritura.

    Lo que queda es exactamente lo que la tabla de modos de fallo anuncia: el
    pedido pagado con su código, y el intento todavía pendiente. Nadie recibe un
    error — el cliente se lleva su comida.
    """
    pedido_id, referencia = _pedido_con_intento()

    original = pagos_repo.guardar

    def muere_al_guardar(intento):
        if intento.estado_pago is EstadoPago.APROBADO:
            raise RuntimeError("el proceso murió antes de confirmar el intento")
        return original(intento)

    monkeypatch.setattr(pagos_repo, "guardar", muere_al_guardar)

    with pytest.raises(RuntimeError):
        pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    # El pedido sí se escribió: el fallo ocurrió después.
    pedido = pedidos_service.obtener_pedido(pedido_id)
    assert pedido.estado is EstadoPedido.PAGADO
    assert pedido.codigo_canje, "el cliente se quedó sin su código"

    # Y el intento no. Esa es la ventana.
    assert pagos_repo.buscar_por_referencia(referencia).estado_pago is EstadoPago.PENDIENTE


def test_la_conciliacion_ve_el_intento_descolgado(monkeypatch):
    """La mitigación: que el desajuste se pueda ver.

    No se repara solo porque sí; se **detecta**. Un desajuste que nadie puede
    enumerar es indistinguible de no tenerlo, y esta función es lo que lo
    convierte en una lista.
    """
    pedido_id, referencia = _pedido_con_intento()
    original = pagos_repo.guardar
    monkeypatch.setattr(
        pagos_repo, "guardar",
        lambda i: (_ for _ in ()).throw(RuntimeError("corte"))
        if i.estado_pago is EstadoPago.APROBADO else original(i),
    )
    with pytest.raises(RuntimeError):
        pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)
    monkeypatch.undo()

    assert pagos_service.conciliar() == [referencia]


def test_el_reintento_de_la_pasarela_cierra_la_ventana(monkeypatch):
    """Por qué la ventana es transitoria y no permanente.

    La pasarela entrega **al-menos-una-vez**: si no recibe `2xx`, reintenta. Y
    el reintento rehace las dos escrituras — `confirmar_pago` es idempotente y
    devuelve que ya estaba pagado, y el intento sí llega a marcarse.

    Es lo que convierte este fallo en uno que se cura solo **mientras el otro
    extremo reintente**. Si la pasarela se rinde, la ventana se queda abierta, y
    por eso la conciliación existe igualmente.
    """
    pedido_id, referencia = _pedido_con_intento()
    original = pagos_repo.guardar
    monkeypatch.setattr(
        pagos_repo, "guardar",
        lambda i: (_ for _ in ()).throw(RuntimeError("corte"))
        if i.estado_pago is EstadoPago.APROBADO else original(i),
    )
    with pytest.raises(RuntimeError):
        pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)
    monkeypatch.undo()

    # El reintento de la pasarela, sin nada especial.
    pedido, duplicado = pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert duplicado is True, "el segundo aviso tiene que reconocerse como repetido"
    assert pagos_service.conciliar() == []


def test_el_reintento_no_genera_un_segundo_codigo(monkeypatch):
    """Y lo más importante: curarse no puede cobrar dos veces.

    El código de canje se genera dentro de un `UPDATE ... WHERE estado =
    'pendiente_pago'`, así que el segundo intento no encuentra fila que
    actualizar. Si fuera un `if` previo, dos avisos simultáneos generarían dos
    códigos para un pedido.
    """
    pedido_id, referencia = _pedido_con_intento()
    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)
    codigo = pedidos_service.obtener_pedido(pedido_id).codigo_canje

    for _ in range(3):
        pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert pedidos_service.obtener_pedido(pedido_id).codigo_canje == codigo


# ---------------------------------------------------------------------------
# El evento en proceso: lo que se pierde y a quién no le importa
# ---------------------------------------------------------------------------

def test_el_evento_se_publica_despues_de_persistir():
    """Nunca antes, y el orden es la decisión.

    Anunciar un hecho que todavía podría no ocurrir obliga a compensarlo
    después. Publicando al final, lo peor que pasa es que el hecho ocurra y
    nadie se entere — que es recuperable consultando el pedido.
    """
    recibidos: list[dict] = []
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, recibidos.append)
    pedido_id, referencia = _pedido_con_intento()

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert len(recibidos) == 1
    # El mensaje lleva el estado ya escrito, no una promesa.
    assert pedidos_service.obtener_pedido(pedido_id).estado is EstadoPedido.PAGADO
    assert recibidos[0]["codigo_canje"] == pedidos_service.obtener_pedido(pedido_id).codigo_canje


def test_un_suscriptor_que_revienta_no_arrastra_a_los_demas():
    """Aislamiento de fallos entre suscriptores.

    Sin esto, el acoplamiento temporal volvería por la puerta de atrás: un
    suscriptor lento o roto decidiría si el cobro se completa.
    """
    recibidos: list[dict] = []
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO,
                      lambda _: (_ for _ in ()).throw(RuntimeError("suscriptor roto")))
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, recibidos.append)
    _, referencia = _pedido_con_intento()

    pagos_service.procesar_evento(referencia, EstadoPago.APROBADO)

    assert len(recibidos) == 1


def test_el_evento_se_pierde_si_no_hay_nadie_escuchando():
    """Y hoy no hay nadie, lo que acota el alcance de esta pérdida.

    El canal `pedidos-pagados` tiene contrato y publicador, y **cero
    suscriptores en producción**. Esta prueba lo deja escrito para que la
    afirmación de arc42 §6.7 no dependa de que alguien recuerde mirar.

    Es la razón por la que no se implementa un *outbox*: un mecanismo para no
    perder mensajes que nadie recibe resolvería un problema que no se tiene.
    El día que exista un suscriptor del que dependa algo, esta prueba falla y
    obliga a revisar la decisión.
    """
    _, referencia = _pedido_con_intento()

    entregados = eventos.publicar(eventos.CANAL_PEDIDO_PAGADO, {"prueba": True})

    assert entregados == 0, (
        "Apareció un suscriptor de `pedidos-pagados`. Eso cambia el análisis de "
        "arc42 §6.7: con alguien escuchando, perder el evento deja de ser "
        "inocuo y hay que decidir si hace falta un outbox."
    )
