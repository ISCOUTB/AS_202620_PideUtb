"""Las dos implementaciones de cada repositorio se comportan igual.

Hay dos: memoria y PostgreSQL. Tener dos es lo que permite que la suite corra en
un portátil sin base de datos instalada, pero abre un riesgo evidente —que se
separen— y este archivo es la contención: **las mismas aserciones se ejecutan
contra ambas**.

### Cómo se ejecuta la parte de PostgreSQL

Se necesita `PIDEUTB_DATABASE_URL_PRUEBAS`. Sin ella, esos casos se **omiten**
con el motivo escrito, en lugar de fallar: no tener PostgreSQL instalado no es
un defecto del código.

La variable es **distinta** de `PIDEUTB_DATABASE_URL` a propósito. Si las
pruebas leyeran la misma que usa la aplicación, bastaría con tenerla exportada
en la terminal —que es lo normal mientras se desarrolla contra Supabase— para
que la suite borrase las tablas de producción. Ese accidente ocurre, y la única
defensa fiable es que el nombre no coincida.

En CI la aporta un contenedor de PostgreSQL efímero.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app import base_de_datos
from app.menu import repository as menu_repo
from app.pagos import repository as pagos_repo
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pagos.models import IntentoPago
from app.pedidos import repository as pedidos_repo
from app.pedidos.contracts import EstadoPedido
from app.usuarios import repository as usuarios_repo

RAIZ = Path(__file__).resolve().parent.parent
MIGRACIONES = RAIZ / "migraciones"

URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()
sin_postgres = pytest.mark.skipif(
    not URL_PRUEBAS,
    reason="Sin PIDEUTB_DATABASE_URL_PRUEBAS: no hay PostgreSQL contra el que probar.",
)


@pytest.fixture(params=["memoria", "postgres"])
def implementacion(request, monkeypatch):
    """Deja el sistema apuntando a una implementación u otra.

    Cada caso que use este fixture se ejecuta **dos veces**, una por cada una.
    Esa duplicación es justamente el punto: una aserción que solo se comprueba
    contra memoria no dice nada del código que corre en producción.
    """
    if request.param == "memoria":
        monkeypatch.delenv("PIDEUTB_DATABASE_URL", raising=False)
        base_de_datos.cerrar_pool()
        pedidos_repo._PEDIDOS.clear()
        pedidos_repo._contador = 0
        pagos_repo._INTENTOS.clear()
        yield request.param
        pedidos_repo._PEDIDOS.clear()
        pedidos_repo._contador = 0
        pagos_repo._INTENTOS.clear()
        return

    if not URL_PRUEBAS:
        pytest.skip("Sin PIDEUTB_DATABASE_URL_PRUEBAS.")

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()
    yield request.param
    base_de_datos.cerrar_pool()


def _preparar_base_de_datos() -> None:
    """Aplica el esquema y deja las tablas transaccionales vacías.

    La semilla **no** se borra: los identificadores 1 a 4 están escritos en las
    pruebas y en los ejemplos del contrato.
    """
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        with conexion.cursor() as cur:
            cur.execute("SELECT to_regclass('public.pedidos')")
            if cur.fetchone()[0] is None:
                for archivo in sorted(MIGRACIONES.glob("*.sql")):
                    cur.execute(archivo.read_text(encoding="utf-8"))
            # `RESTART IDENTITY` devuelve la secuencia a su inicio, para que el
            # primer pedido de cada prueba vuelva a ser el 1 y las aserciones no
            # dependan del orden de ejecución.
            cur.execute("TRUNCATE pagos_intentos, pedidos RESTART IDENTITY CASCADE")
        conexion.commit()


# ---------------------------------------------------------------------------
# Catálogo y Cuentas: solo lectura, y la semilla tiene que ser la misma
# ---------------------------------------------------------------------------

def test_la_carta_de_un_establecimiento_llega_ordenada(implementacion):
    items = menu_repo.buscar_por_establecimiento(1)

    assert [i.id for i in items] == [1, 2]
    assert [i.nombre for i in items] == ["Arepa de huevo", "Jugo de mango"]
    # El precio es un entero en centavos (V-07), no un decimal.
    assert items[0].precio_centavos == 400000


def test_un_item_agotado_se_lee_como_agotado(implementacion):
    assert menu_repo.buscar_por_id(3).disponible is False


def test_un_item_inexistente_devuelve_none_y_no_lanza(implementacion):
    assert menu_repo.buscar_por_id(9999) is None


def test_un_establecimiento_sin_carta_devuelve_lista_vacia(implementacion):
    """El establecimiento 4 existe y opera, pero no ha cargado productos.

    Es lo que obliga a distinguir «no existe» de «existe y no tiene nada».
    """
    assert usuarios_repo.buscar_establecimiento_por_id(4) is not None
    assert menu_repo.buscar_por_establecimiento(4) == []


def test_el_establecimiento_inactivo_se_lee_como_inactivo(implementacion):
    assert usuarios_repo.buscar_establecimiento_por_id(3).activo is False


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------

def _crear_pedido() -> object:
    return pedidos_repo.crear(
        establecimiento_id=1,
        item_id=1,
        nombre_item="Arepa de huevo",
        precio_unitario_centavos=400000,
        cantidad=2,
        total_centavos=800000,
    )


def test_el_identificador_lo_asigna_el_almacenamiento(implementacion):
    """Quien crea el pedido no lo inventa.

    Antes de la migración el servicio pedía el identificador a un contador en
    memoria del proceso, y con dos instancias las dos habrían empezado por 1.
    Era el ejemplo concreto de V-09.
    """
    primero = _crear_pedido()
    segundo = _crear_pedido()

    assert primero.id >= 1
    assert segundo.id > primero.id


def test_un_pedido_creado_se_puede_volver_a_leer(implementacion):
    creado = _crear_pedido()
    leido = pedidos_repo.buscar_por_id(creado.id)

    assert leido == creado
    assert leido.estado is EstadoPedido.PENDIENTE_PAGO
    assert leido.codigo_canje is None


def test_la_cola_del_establecimiento_llega_del_mas_reciente_al_mas_antiguo(implementacion):
    ids = [_crear_pedido().id for _ in range(3)]

    cola = pedidos_repo.buscar_por_establecimiento(1)

    assert [p.id for p in cola] == sorted(ids, reverse=True)


def test_la_cola_de_otro_establecimiento_no_los_incluye(implementacion):
    _crear_pedido()
    assert pedidos_repo.buscar_por_establecimiento(2) == []


def test_marcar_pagado_deja_el_pedido_pagado_y_con_codigo(implementacion):
    pedido = _crear_pedido()

    pagado = pedidos_repo.marcar_pagado(pedido.id, "ABC123")

    assert pagado.estado is EstadoPedido.PAGADO
    assert pagado.codigo_canje == "ABC123"
    assert pedidos_repo.buscar_por_id(pedido.id).codigo_canje == "ABC123"


def test_marcar_pagado_dos_veces_devuelve_none_la_segunda(implementacion):
    """El comportamiento que sostiene la promesa de idempotencia de ADR-0003.

    La pasarela entrega al-menos-una-vez: el mismo aviso llega repetido. Si la
    segunda llamada generara otro código, el usuario tendría dos códigos válidos
    para un pedido y el establecimiento no sabría cuál aceptar.
    """
    pedido = _crear_pedido()

    assert pedidos_repo.marcar_pagado(pedido.id, "PRIMERO") is not None
    assert pedidos_repo.marcar_pagado(pedido.id, "SEGUNDO") is None

    # Y el código no se pisó.
    assert pedidos_repo.buscar_por_id(pedido.id).codigo_canje == "PRIMERO"


def test_marcar_pagado_un_pedido_inexistente_devuelve_none(implementacion):
    assert pedidos_repo.marcar_pagado(9999, "ABC123") is None


def test_guardar_persiste_el_cambio_de_estado(implementacion):
    pedido = pedidos_repo.marcar_pagado(_crear_pedido().id, "ABC123")

    pedidos_repo.guardar(pedido.model_copy(update={"estado": EstadoPedido.EN_PREPARACION}))

    assert pedidos_repo.buscar_por_id(pedido.id).estado is EstadoPedido.EN_PREPARACION


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------

def _intento(pedido_id: int, referencia: str, estado=EstadoPago.PENDIENTE) -> IntentoPago:
    return IntentoPago(
        referencia_pago=referencia,
        pedido_id=pedido_id,
        monto_centavos=800000,
        metodo=MetodoDePago.NEQUI,
        estado_pago=estado,
        url_checkout=f"https://sandbox.example/{referencia}",
    )


def test_un_intento_guardado_se_encuentra_por_su_referencia(implementacion):
    pedido = _crear_pedido()
    pagos_repo.guardar(_intento(pedido.id, "ref-1"))

    encontrado = pagos_repo.buscar_por_referencia("ref-1")

    assert encontrado.pedido_id == pedido.id
    assert encontrado.metodo is MetodoDePago.NEQUI
    assert encontrado.url_checkout.endswith("ref-1")


def test_solo_se_encuentra_como_pendiente_mientras_lo_esta(implementacion):
    """Es lo que impide abrir dos cobros sobre el mismo pedido."""
    pedido = _crear_pedido()
    pagos_repo.guardar(_intento(pedido.id, "ref-1"))

    assert pagos_repo.buscar_pendiente_de_pedido(pedido.id) is not None

    pagos_repo.guardar(_intento(pedido.id, "ref-1", EstadoPago.RECHAZADO))

    assert pagos_repo.buscar_pendiente_de_pedido(pedido.id) is None


def test_un_pedido_puede_reintentar_tras_un_rechazo(implementacion):
    """Por eso el índice único de la migración es **parcial**.

    Un índice sobre `pedido_id` a secas habría impedido reintentar con otro
    método después de un rechazo, que es un caso de uso legítimo.
    """
    pedido = _crear_pedido()
    pagos_repo.guardar(_intento(pedido.id, "ref-1", EstadoPago.RECHAZADO))
    pagos_repo.guardar(_intento(pedido.id, "ref-2"))

    assert pagos_repo.buscar_pendiente_de_pedido(pedido.id).referencia_pago == "ref-2"


# ---------------------------------------------------------------------------
# La semilla de memoria y la del SQL dicen lo mismo
# ---------------------------------------------------------------------------

def _valores_del_insert(tabla: str) -> list[tuple[str, ...]]:
    """Extrae las filas literales de un INSERT de la migración de semilla.

    Es un análisis deliberadamente tonto —no es un intérprete de SQL— porque
    solo tiene que leer un archivo que escribimos nosotros y que no contiene
    subconsultas.

    Dos detalles no son adorno, y los dos costaron una prueba en rojo antes de
    estar aquí:

    1. **Se quitan los comentarios primero.** La primera versión no lo hacía y
       se tragaba los paréntesis de un comentario («200 con lista vacía»),
       tomándolos por una fila de datos.
    2. **Las comas se parten respetando las comillas.** Los valores contienen
       comas dentro —`'Bloque A, primer piso'`—, así que un `split(",")` las
       cortaba por la mitad.
    """
    crudo = (MIGRACIONES / "002_datos_semilla.sql").read_text(encoding="utf-8")
    sql = "\n".join(re.sub(r"--.*$", "", linea) for linea in crudo.splitlines())
    bloque = sql.split(f"INSERT INTO {tabla}", 1)[1].split("ON CONFLICT", 1)[0]
    filas = re.findall(r"\(([^()]*)\)", bloque.split("VALUES", 1)[1])
    return [_partir_columnas(fila) for fila in filas]


def _partir_columnas(fila: str) -> tuple[str, ...]:
    """Parte una fila de VALUES por comas que estén fuera de comillas."""
    columnas: list[str] = []
    actual: list[str] = []
    dentro_de_comillas = False

    for caracter in fila:
        if caracter == "'":
            dentro_de_comillas = not dentro_de_comillas
        elif caracter == "," and not dentro_de_comillas:
            columnas.append("".join(actual).strip())
            actual = []
            continue
        actual.append(caracter)

    columnas.append("".join(actual).strip())
    return tuple(c.strip().strip("'") for c in columnas)


def test_la_semilla_de_memoria_coincide_con_la_del_sql():
    """Si se separan, las pruebas en memoria dejan de decir algo de producción.

    Esta prueba no necesita base de datos: compara dos archivos del repositorio.
    """
    del_sql = {int(f[0]): f for f in _valores_del_insert("menu_items")}
    de_memoria = menu_repo._ITEMS_SEED

    assert set(del_sql) == set(de_memoria), "los ítems de la semilla no son los mismos"

    for item_id, fila in del_sql.items():
        item = de_memoria[item_id]
        assert int(fila[1]) == item.establecimiento_id, f"ítem {item_id}: establecimiento"
        assert fila[2] == item.nombre, f"ítem {item_id}: nombre"
        assert int(fila[3]) == item.precio_centavos, f"ítem {item_id}: precio"
        assert (fila[4] == "true") == item.disponible, f"ítem {item_id}: disponibilidad"


def test_la_semilla_de_establecimientos_coincide_con_la_del_sql():
    del_sql = {int(f[0]): f for f in _valores_del_insert("establecimientos")}
    de_memoria = usuarios_repo._ESTABLECIMIENTOS_SEED

    assert set(del_sql) == set(de_memoria)

    for establecimiento_id, fila in del_sql.items():
        establecimiento = de_memoria[establecimiento_id]
        assert fila[1] == establecimiento.nombre
        assert fila[2] == establecimiento.ubicacion
        assert fila[3] == establecimiento.horario
        assert (fila[4] == "true") == establecimiento.activo


# ---------------------------------------------------------------------------
# Lo que solo PostgreSQL puede demostrar
# ---------------------------------------------------------------------------

@sin_postgres
def test_la_base_de_datos_rechaza_un_codigo_de_canje_sin_pago(monkeypatch):
    """La restricción que protege ESC-04 desde el motor.

    Aunque un fallo del código intentara emitir un código de canje antes de
    cobrar, la base de datos rechaza la escritura. Es la diferencia entre una
    regla que se cumple porque el código está bien y una que se cumple aunque
    el código esté mal.
    """
    import psycopg

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()

    pedido = _crear_pedido()

    with pytest.raises(psycopg.errors.CheckViolation):
        with base_de_datos.conexion() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE pedidos SET codigo_canje = 'TRAMPA' WHERE id = %s",
                (pedido.id,),
            )

    base_de_datos.cerrar_pool()


@sin_postgres
def test_la_base_de_datos_rechaza_un_total_incoherente(monkeypatch):
    """Un error de cálculo en el código no llega a escribirse."""
    import psycopg

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()

    with pytest.raises(psycopg.errors.CheckViolation):
        pedidos_repo.crear(
            establecimiento_id=1,
            item_id=1,
            nombre_item="Arepa de huevo",
            precio_unitario_centavos=400000,
            cantidad=2,
            total_centavos=1,          # no es 400000 * 2
        )

    base_de_datos.cerrar_pool()


@sin_postgres
def test_no_se_pueden_abrir_dos_cobros_pendientes_sobre_el_mismo_pedido(monkeypatch):
    """El índice único parcial, que es la defensa contra el caso simultáneo.

    La consulta previa de `buscar_pendiente_de_pedido` evita el caso normal;
    esto evita el que ninguna consulta previa puede evitar, porque dos
    peticiones simultáneas leen «no hay ninguno» a la vez.
    """
    import psycopg

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()

    pedido = _crear_pedido()
    pagos_repo.guardar(_intento(pedido.id, "ref-1"))

    with pytest.raises(psycopg.errors.UniqueViolation):
        pagos_repo.guardar(_intento(pedido.id, "ref-2"))

    base_de_datos.cerrar_pool()
