"""El inventario del día: no vender lo que no hay.

Nace de la sustentación del 25/11/2026, donde se señaló que nada impedía pagar
diez arepas cuando quedaban tres: `disponible` era un sí o un no que el mostrador
marcaba a mano, y la app no sabía cuántas había (ADR-0015).

Lo que protege, en orden de lo que más duele perder:

1. **Un pedido no se guarda sin sus unidades.** Se reservan antes de guardar, y
   un carrito en el que algo no alcanza no descuenta nada, ni de ese producto ni
   de los demás.
2. **La última unidad se vende una sola vez.** Dos pedidos a la vez por ella, y
   solo uno la obtiene; se ejecuta con dos hilos contra PostgreSQL.
3. **Lo que se cancela vuelve a la carta**, y lo que nadie paga se queda
   retenido: es una decisión, y la prueba la fija para que no se «arregle».
4. **Quien no cuenta vende como siempre.** Con `unidades_hoy` nulo, que es el
   valor de toda la carta, nada cambia.
5. **Quién puede fijar el conteo:** solo con sesión, solo lo suyo, y solo
   números que un mostrador puede tener.
"""
import os
import threading

import pytest
from fastapi.testclient import TestClient

from app import base_de_datos
from app.autenticacion import personal_de_establecimiento, usuario_actual
from app.main import app
from app.menu import repository as menu_repo
from app.menu import service as catalogo_service
from app.pedidos import repository as pedidos_repo
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import EstadoPedido
from app.usuarios.contracts import RolUsuario, UsuarioAutenticado
from tests.test_repositorios import _preparar_base_de_datos

client = TestClient(app)

URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()
CORREO = "cliente@example.com"

#: Quien atiende el mostrador del establecimiento 1 en estas pruebas.
MOSTRADOR = UsuarioAutenticado(
    usuario_id=1,
    correo="mostrador@utb.edu.co",
    rol=RolUsuario.PERSONAL_ESTABLECIMIENTO,
    establecimiento_id=1,
)


@pytest.fixture(autouse=True)
def sin_pedidos():
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0
    yield
    pedidos_repo._PEDIDOS.clear()
    pedidos_repo._contador = 0


@pytest.fixture(autouse=True)
def semilla_intacta():
    """Deja la carta en memoria como estaba: ningún producto con cuenta.

    `fijar_unidades` reemplaza el objeto del diccionario en vez de mutarlo, así
    que basta con guardar las referencias y devolverlas. Sin esto, el conteo que
    una prueba fija se filtraría a la siguiente y «sin conteo todo sigue igual»
    dejaría de probar nada.
    """
    original = dict(menu_repo._ITEMS_SEED)
    yield
    menu_repo._ITEMS_SEED.clear()
    menu_repo._ITEMS_SEED.update(original)


@pytest.fixture
def sesion_de_mostrador():
    """Sustituye la autenticación por un usuario conocido, como el panel.

    El mecanismo real se prueba en `test_autenticacion.py`; aquí lo que se prueba
    es qué puede hacer quien ya entró.
    """
    app.dependency_overrides[personal_de_establecimiento] = lambda: MOSTRADOR
    app.dependency_overrides[usuario_actual] = lambda: MOSTRADOR
    yield
    app.dependency_overrides.clear()


def _fijar(item_id: int, unidades: int | None, establecimiento_id: int = 1) -> None:
    catalogo_service.fijar_unidades_del_dia(
        item_id, unidades, establecimiento_id=establecimiento_id
    )


def _quedan(item_id: int) -> int | None:
    return client.get(f"/v1/menu/items/{item_id}").json()["unidades_hoy"]


def _pedir(*lineas: tuple[int, int]):
    return client.post(
        "/v1/pedidos",
        json={
            "lineas": [{"item_id": i, "cantidad": c} for i, c in lineas],
            "correo_cliente": CORREO,
        },
    )


# --- Sin conteo, nada cambia -------------------------------------------------


def test_sin_conteo_la_carta_se_vende_como_siempre():
    """Toda la carta arranca sin cuenta: ni la semilla ni `017` ponen un número.

    Un pedido no toca nada y la carta publica `null`, que el sitio lee como «no
    anunciar». Es lo que hace que la 6.1.0 sea compatible: petición por
    petición, quien no cuenta recibe lo mismo que en la 6.0.0.
    """
    assert _quedan(1) is None

    assert _pedir((1, 4)).status_code == 201

    assert _quedan(1) is None
    assert all(
        item["unidades_hoy"] is None
        for item in client.get("/v1/menu/establecimientos/1/items").json()["items"]
    )


# --- Reservar al crear -------------------------------------------------------


def test_crear_un_pedido_descuenta_lo_que_pide():
    _fijar(1, 5)

    assert _pedir((1, 2)).status_code == 201

    assert _quedan(1) == 3


def test_pedir_mas_de_lo_que_queda_responde_409_y_no_descuenta_nada():
    """Todo o nada, con dos productos.

    La arepa alcanza y el jugo no. Si el descuento fuera línea a línea, la arepa
    quedaría descontada para un pedido que no existe, y la siguiente persona
    vería «quedan 1» de algo que nadie compró. El mensaje dice qué faltó y
    cuánto queda, porque es lo que la persona necesita para arreglar su carrito.
    """
    _fijar(1, 3)
    _fijar(2, 1)

    respuesta = _pedir((1, 2), (2, 2))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Solo queda 1 de 'Jugo de mango'"
    assert (_quedan(1), _quedan(2)) == (3, 1), "no se descontó ninguna línea"
    assert pedidos_repo._PEDIDOS == {}, "no se guardó ningún pedido"


def test_el_mensaje_distingue_agotado_de_quedan_pocas():
    """Tres mensajes, según lo que quede: cero, una, o varias.

    El de cero solo se ve en la carrera —con cero la carta ya publica el ítem
    como no disponible y `crear_pedido` lo rechaza antes de reservar—, así que
    se pide directamente al Catálogo, que es quien lo escribe.
    """
    _fijar(1, 0)
    _fijar(2, 2)

    with pytest.raises(catalogo_service.UnidadesInsuficientesError) as agotado:
        catalogo_service.reservar_unidades([(1, 1)])
    assert str(agotado.value) == "'Arepa de huevo' se agotó"

    assert _pedir((2, 3)).json()["detail"] == "Solo quedan 2 de 'Jugo de mango'"


def test_el_servicio_tambien_reserva_para_quien_no_entra_por_http():
    _fijar(1, 1)

    with pytest.raises(pedidos_service.ItemNoDisponibleError):
        pedidos_service.crear_pedido([(1, 2)], correo_cliente=CORREO)

    assert menu_repo.buscar_por_id(1).unidades_hoy == 1


def test_si_guardar_el_pedido_falla_las_unidades_vuelven(monkeypatch):
    """La compensación entre dos contextos que no comparten transacción.

    Reservar y guardar son dos escrituras de dos repositorios. Si la segunda
    falla, la primera ya pasó, y lo único que impide que la arepa quede retenida
    para siempre es que Pedidos la devuelva antes de propagar el error.
    """
    _fijar(1, 5)

    def guardar_que_falla(**_):
        raise RuntimeError("la base no responde")

    monkeypatch.setattr(pedidos_repo, "crear", guardar_que_falla)

    with pytest.raises(RuntimeError):
        pedidos_service.crear_pedido([(1, 2)], correo_cliente=CORREO)

    assert menu_repo.buscar_por_id(1).unidades_hoy == 5


def test_un_carrito_rechazado_por_otro_motivo_no_toca_el_inventario():
    """La reserva va después de todas las validaciones, no antes.

    Un pedido que la hora o un producto ajeno van a rechazar no debe pasar por
    el inventario ni un instante: aunque se compensara, dos personas mirando la
    carta en ese instante verían una unidad menos que no se vendió.
    """
    _fijar(1, 5)

    # El ítem 4 es del establecimiento 3, que está inactivo: 409 por Cuentas.
    assert _pedir((1, 1), (4, 1)).status_code == 409

    assert _quedan(1) == 5


# --- Cero es agotado ---------------------------------------------------------


def test_cero_unidades_publica_no_disponible_y_la_carta_lo_omite():
    _fijar(2, 0)

    item = client.get("/v1/menu/items/2").json()
    assert item["disponible"] is False
    assert item["unidades_hoy"] == 0

    carta = client.get(
        "/v1/menu/establecimientos/1/items", params={"solo_disponibles": True}
    ).json()["items"]
    assert [i["item_id"] for i in carta] == [1]

    respuesta = _pedir((2, 1))
    assert respuesta.status_code == 409
    assert "no está disponible" in respuesta.json()["detail"]


def test_volver_a_contar_lo_resucita():
    """Cero no es `disponible = false`: el mostrador no tiene que tocar dos cosas."""
    _fijar(2, 0)
    _fijar(2, 4)

    assert client.get("/v1/menu/items/2").json()["disponible"] is True


# --- Devolver al cancelar ----------------------------------------------------


def test_cancelar_devuelve_las_unidades():
    _fijar(1, 5)
    pedido_id = _pedir((1, 2)).json()["pedido_id"]
    assert _quedan(1) == 3

    pedidos_service.confirmar_pago(pedido_id)
    pedidos_service.avanzar_estado(
        pedido_id, EstadoPedido.CANCELADO, establecimiento_id=1
    )

    assert _quedan(1) == 5


def test_entregar_no_devuelve_nada():
    """Solo la cancelación devuelve: un pedido entregado se comió sus unidades."""
    _fijar(1, 5)
    pedido_id = _pedir((1, 2)).json()["pedido_id"]
    pedido, _ = pedidos_service.confirmar_pago(pedido_id)

    for estado in (EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_PARA_RECOGER):
        pedidos_service.avanzar_estado(pedido_id, estado, establecimiento_id=1)
    pedidos_service.avanzar_estado(
        pedido_id,
        EstadoPedido.ENTREGADO,
        establecimiento_id=1,
        codigo_canje=pedido.codigo_canje,
    )

    assert _quedan(1) == 3


def test_un_pedido_sin_pagar_retiene_sus_unidades():
    """La limitación conocida de ADR-0015, fijada para que no se «arregle» sola.

    No hay caducidad: quien está terminando de pagar en la pasarela tiene su
    arepa apartada, y liberarla por tiempo se la quitaría. El camino de vuelta
    es el mostrador, que corrige el conteo con el endpoint.
    """
    _fijar(1, 5)
    _pedir((1, 2))

    assert _quedan(1) == 3, "sigue reservada aunque nadie pagó"

    _fijar(1, 5)
    assert _quedan(1) == 5, "y el mostrador la recupera escribiendo el número"


# --- El endpoint del mostrador -----------------------------------------------


def test_fijar_el_conteo_exige_sesion():
    respuesta = client.post("/v1/menu/items/1/inventario", json={"unidades_hoy": 5})

    assert respuesta.status_code == 401
    assert _quedan(1) is None


def test_el_mostrador_fija_el_conteo_de_su_carta(sesion_de_mostrador):
    respuesta = client.post("/v1/menu/items/1/inventario", json={"unidades_hoy": 7})

    assert respuesta.status_code == 200
    assert respuesta.json()["unidades_hoy"] == 7
    assert respuesta.json()["item_id"] == 1
    assert _quedan(1) == 7


def test_nulo_apaga_el_control(sesion_de_mostrador):
    _fijar(1, 2)

    respuesta = client.post("/v1/menu/items/1/inventario", json={"unidades_hoy": None})

    assert respuesta.status_code == 200
    assert respuesta.json()["unidades_hoy"] is None
    assert _pedir((1, 4)).status_code == 201, "vuelve a venderse sin descontar"


def test_el_item_de_otro_establecimiento_da_404_y_no_403(sesion_de_mostrador):
    """El ítem 3 es del establecimiento 2. Un 403 confirmaría que existe."""
    respuesta = client.post("/v1/menu/items/3/inventario", json={"unidades_hoy": 5})

    assert respuesta.status_code == 404
    assert menu_repo.buscar_por_id(3).unidades_hoy is None


def test_un_item_inexistente_da_el_mismo_404(sesion_de_mostrador):
    assert client.post("/v1/menu/items/9999/inventario", json={"unidades_hoy": 5}).status_code == 404


@pytest.mark.parametrize("cuerpo", [{"unidades_hoy": -1}, {"unidades_hoy": 1000}, {}])
def test_un_numero_que_ningun_mostrador_tiene_se_rechaza(sesion_de_mostrador, cuerpo):
    """Negativo, más de 999, o sin el campo: `null` hay que decirlo, no omitirlo."""
    respuesta = client.post("/v1/menu/items/1/inventario", json=cuerpo)

    assert respuesta.status_code == 422
    assert _quedan(1) is None


# --- Lo que solo PostgreSQL puede demostrar ----------------------------------


@pytest.fixture
def contra_postgres(monkeypatch):
    """La carta real, con las migraciones aplicadas y sin ningún conteo fijado.

    `_preparar_base_de_datos` vacía pedidos y pagos pero no toca la carta, así
    que el conteo se limpia aquí, antes y después: un fallo a medias en una
    ejecución anterior no puede dejar la arepa en cero para la siguiente.
    """
    if not URL_PRUEBAS:
        pytest.skip("Sin PIDEUTB_DATABASE_URL_PRUEBAS.")
    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()
    _sin_conteo_en_la_semilla()
    yield
    _sin_conteo_en_la_semilla()
    base_de_datos.cerrar_pool()


def _sin_conteo_en_la_semilla() -> None:
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        conexion.execute("UPDATE menu_items SET unidades_hoy = NULL WHERE id <= 4")
        conexion.commit()


def test_dos_reservas_de_la_ultima_unidad_solo_una_gana(contra_postgres):
    """Dos hilos, una arepa.

    Es la carrera que ninguna comprobación previa puede cerrar: los dos leen
    «queda 1» a la vez. Lo que la cierra es que la condición viaje dentro del
    `UPDATE` (`unidades_hoy >= cantidad`): el motor deja pasar a uno, el otro
    actualiza cero filas y se entera. Si esta prueba falla, el descuento se
    está haciendo con leer-decidir-escribir.
    """
    _fijar(1, 1)
    # El pool se abre antes de lanzar los hilos, para que la carrera sea por la
    # fila y no por crear el pool.
    assert menu_repo.buscar_por_id(1).unidades_hoy == 1

    listos = threading.Barrier(2)
    resultados: list[str] = []
    candado = threading.Lock()

    def pedir_la_ultima():
        listos.wait()
        try:
            pedidos_service.crear_pedido([(1, 1)], correo_cliente=CORREO)
            resultado = "creado"
        except pedidos_service.ItemNoDisponibleError as e:
            resultado = str(e)
        with candado:
            resultados.append(resultado)

    hilos = [threading.Thread(target=pedir_la_ultima) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(resultados) == sorted(["creado", "'Arepa de huevo' se agotó"]), resultados
    assert menu_repo.buscar_por_id(1).unidades_hoy == 0
    assert len(pedidos_repo.buscar_por_establecimiento(1)) == 1


def test_contra_postgres_el_todo_o_nada_es_una_transaccion(contra_postgres):
    """La arepa se descuenta y el jugo no alcanza: el `rollback` devuelve la arepa."""
    _fijar(1, 3)
    _fijar(2, 1)

    with pytest.raises(pedidos_service.ItemNoDisponibleError):
        pedidos_service.crear_pedido([(1, 2), (2, 2)], correo_cliente=CORREO)

    assert menu_repo.buscar_por_id(1).unidades_hoy == 3
    assert menu_repo.buscar_por_id(2).unidades_hoy == 1
    assert pedidos_repo.buscar_por_establecimiento(1) == []


def test_contra_postgres_la_base_rechaza_un_conteo_negativo(contra_postgres):
    """El `CHECK` de la migración 017, por si algún camino se salta el esquema."""
    import psycopg

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute("UPDATE menu_items SET unidades_hoy = -1 WHERE id = 1")
