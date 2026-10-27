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
en la terminal —que es lo normal mientras se desarrolla contra una base real—
para que la suite borrase las tablas de producción. Ese accidente ocurre, y la única
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
from app.menu.models import ItemMenu
from app.pagos import repository as pagos_repo
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pagos.models import IntentoPago
from app.pedidos import repository as pedidos_repo
from app.pedidos.contracts import EstadoPedido
from app.pedidos.models import LineaPedido, Pedido
from app.usuarios import repository as usuarios_repo
from app.usuarios.models import Establecimiento, Usuario

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

    # La categoría se lee de la fila, no se deduce. Se comprueba el valor y no
    # solo que no sea nulo porque `categoria` y `descripcion` son del mismo
    # tipo: intercambiarlas en `_desde_fila` no daría error, daría datos
    # cruzados, y la comprobación estructural de más abajo no lo vería.
    assert [i.categoria for i in items] == ["Asados", "Bebidas"]
    assert items[0].descripcion is None
    assert items[0].imagen is None


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
        lineas=[
            LineaPedido(
                item_id=1,
                nombre_item="Arepa de huevo",
                precio_unitario_centavos=400000,
                cantidad=2,
                total_linea_centavos=800000,
            )
        ],
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


def test_buscar_ids_pagados_solo_devuelve_los_pagados(implementacion):
    """Lo que la conciliación de fallos parciales usa para cruzar los contextos.

    Es la mitad de Pedidos del detector de [arc42 §6.7](../../docs/arc42/arc42.md#fallos-parciales):
    Pagos pregunta por esta vía en lugar de leer la tabla `pedidos`, que
    [ADR-0001](../../docs/adr/0001-estilo-arquitectonico.md) le prohíbe tocar.
    """
    sin_pagar = _crear_pedido()
    pagado = _crear_pedido()
    pedidos_repo.marcar_pagado(pagado.id, "PAGADO1")

    ids = pedidos_repo.buscar_ids_pagados()

    assert pagado.id in ids
    assert sin_pagar.id not in ids


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


def test_buscar_pendientes_de_pedidos_filtra_por_estado_y_por_pedido(implementacion):
    """La otra mitad del detector de fallos parciales.

    Devuelve los intentos **pendientes** de los pedidos que se le pasan, que es
    justo lo que hay que cruzar con los pedidos ya pagados para encontrar los
    que quedaron descolgados (`pagos.service.conciliar`).

    Recibe identificadores en lugar de hacer el `JOIN` en SQL a propósito: un
    cruce entre `pagos_intentos` y `pedidos` dentro del repositorio de Pagos
    sería leer la tabla de otro contexto, que es lo que ADR-0001 prohíbe.
    """
    descolgado = _crear_pedido()
    resuelto = _crear_pedido()
    ajeno = _crear_pedido()
    pagos_repo.guardar(_intento(descolgado.id, "ref-descolgada"))
    pagos_repo.guardar(_intento(resuelto.id, "ref-resuelta", EstadoPago.APROBADO))
    pagos_repo.guardar(_intento(ajeno.id, "ref-ajena"))

    encontrados = pagos_repo.buscar_pendientes_de_pedidos([descolgado.id, resuelto.id])

    referencias = [i.referencia_pago for i in encontrados]
    assert referencias == ["ref-descolgada"], (
        "tiene que traer solo los pendientes, y solo de los pedidos pedidos"
    )


def test_buscar_pendientes_sin_pedidos_no_consulta_nada(implementacion):
    """Una lista vacía no es «todos».

    Sin este caso, `WHERE pedido_id = ANY('{}')` devolvería cero filas por
    casualidad y nadie notaría que la función se llamó sin sentido. Peor: una
    implementación descuidada podría interpretar la lista vacía como «sin
    filtro» y devolver **todos** los intentos pendientes del sistema.
    """
    pedido = _crear_pedido()
    pagos_repo.guardar(_intento(pedido.id, "ref-1"))

    assert pagos_repo.buscar_pendientes_de_pedidos([]) == []


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
# Lo que el SELECT pide y lo que el modelo tiene son la misma lista
# ---------------------------------------------------------------------------
#
# Esta sección nació de un fallo real: se añadieron `imagen`, `categoria` y
# `descripcion` a `ItemMenu` y a la tabla, pero no a la lista de columnas del
# `SELECT`. La suite entera siguió en verde —ninguna aserción nombraba los
# campos nuevos— y la API devolvía `null` en los tres contra PostgreSQL. En
# memoria funcionaba, que es lo que hizo tardar en verlo.
#
# La defensa no es acordarse de escribir una aserción por campo. Es esta: la
# lista de columnas y los campos del modelo tienen que ser **la misma lista en
# el mismo orden**, porque `_desde_fila` lee la tupla por posición. Añadir un
# campo sin añadir su columna rompe aquí, sin que nadie tenga que acordarse.

# Campos que el modelo tiene y la fila no, con el motivo. Cada entrada es una
# excepción consciente: si se vacía esta lista, la comprobación es exacta.
CAMPOS_QUE_NO_SON_COLUMNAS = {
    # Las líneas viven en `pedido_lineas`; `_desde_fila` las recibe aparte.
    "lineas",
}


@pytest.mark.parametrize(
    "nombre, columnas, modelo",
    [
        ("menu_items", menu_repo._COLUMNAS, ItemMenu),
        ("pagos_intentos", pagos_repo._COLUMNAS, IntentoPago),
        ("pedidos", pedidos_repo._COLUMNAS, Pedido),
        ("pedido_lineas", pedidos_repo._COLUMNAS_LINEA, LineaPedido),
        ("establecimientos", usuarios_repo._COLUMNAS, Establecimiento),
        ("usuarios", usuarios_repo._COLUMNAS_USUARIO, Usuario),
    ],
)
def test_el_select_pide_exactamente_los_campos_del_modelo(nombre, columnas, modelo):
    """No necesita PostgreSQL: compara dos declaraciones del propio código."""
    del_sql = [c.strip() for c in columnas.split(",")]
    del_modelo = [
        campo for campo in modelo.model_fields if campo not in CAMPOS_QUE_NO_SON_COLUMNAS
    ]

    faltan = [c for c in del_modelo if c not in del_sql]
    assert not faltan, (
        f"{nombre}: el modelo tiene {faltan} y el SELECT no los pide. "
        "Contra PostgreSQL llegarían vacíos; en memoria no se nota."
    )

    sobran = [c for c in del_sql if c not in del_modelo]
    assert not sobran, f"{nombre}: el SELECT pide {sobran}, que el modelo no tiene"

    # El orden importa porque `_desde_fila` indexa la tupla por posición: dos
    # columnas del mismo tipo intercambiadas no darían error, darían datos
    # cruzados.
    assert del_sql == del_modelo, (
        f"{nombre}: las columnas están en otro orden que los campos; "
        "`_desde_fila` lee por posición"
    )


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

    # Solo el `execute` va dentro del `raises`: si abrir la conexión fallara,
    # la prueba pasaría creyendo haber comprobado la restricción.
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                "UPDATE pedidos SET codigo_canje = 'TRAMPA' WHERE id = %s",
                (pedido.id,),
            )

    base_de_datos.cerrar_pool()


@sin_postgres
def test_la_base_de_datos_rechaza_un_total_incoherente(monkeypatch):
    """Un error de cálculo en el código no llega a escribirse.

    Hasta la migración 004 lo impedía un `CHECK` de fila:
    `total_centavos = precio_unitario_centavos * cantidad`. Con el carrito esa
    restricción dejó de poder existir —el total pasó a ser una **suma de otra
    tabla**, y un `CHECK` de fila no ve otra tabla— así que la vigila un
    disparador diferido.

    Lo que esta prueba comprueba no cambió: que un total que no cuadra con sus
    líneas **no llegue a escribirse**. Lo que cambió es quién lo rechaza, y por
    eso la excepción que se espera es otra.
    """
    import psycopg

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()
    _preparar_base_de_datos()

    with pytest.raises(psycopg.errors.RaiseException):
        pedidos_repo.crear(
            establecimiento_id=1,
            lineas=[
                LineaPedido(
                    item_id=1,
                    nombre_item="Arepa de huevo",
                    precio_unitario_centavos=400000,
                    cantidad=2,
                    total_linea_centavos=800000,
                )
            ],
            total_centavos=1,          # no es la suma de las líneas
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

    # El segundo intento se construye fuera del bloque: dentro solo puede
    # quedar la llamada que se espera que falle, para que un fallo al
    # construirlo no se confunda con el rechazo del índice.
    segundo = _intento(pedido.id, "ref-2")

    with pytest.raises(psycopg.errors.UniqueViolation):
        pagos_repo.guardar(segundo)

    base_de_datos.cerrar_pool()
