"""Acceso a datos del contexto Catálogo.

Solo este módulo lee y escribe las tablas del catálogo (`menu_items`).

### Dos implementaciones tras la misma interfaz

Cuando `PIDEUTB_DATABASE_URL` está configurada se consulta PostgreSQL; cuando
no, se usa la semilla en memoria de siempre. La elección se hace en cada
llamada, no al importar el módulo, para que las pruebas puedan ejercitar las dos
sin recargar la aplicación.

No es indecisión: es lo que permite que la suite corra en un portátil sin
PostgreSQL instalado. El riesgo de que las dos se separen se controla ejecutando
**las mismas pruebas contra ambas** (`tests/test_repositorios.py`).

Los precios están en **centavos de COP**: 400000 son 4 000 pesos.
"""
from app import base_de_datos
from app.menu.models import ItemMenu

#: Semilla en memoria. Debe coincidir con `migraciones/002_datos_semilla.sql`,
#: y que coincida lo verifica `tests/test_repositorios.py`.
#:
#: **Son los cuatro casos de prueba, y nada más.** Cada uno existe para hacer
#: comprobable una regla: uno agotado, uno de un establecimiento inactivo, y un
#: establecimiento que opera sin haber cargado carta.
#:
#: La carta real de El Asao —36 productos, `migraciones/005_carta_el_asao.sql`—
#: **no está aquí a propósito**. Son datos de operación de un punto de venta,
#: no casos de prueba, y copiarlos a esta implementación no haría comprobable
#: nada que los cuatro de arriba no comprueben ya.
#:
#: La consecuencia hay que saberla: **sin `PIDEUTB_DATABASE_URL` la carta real
#: no existe**, y la portada diría «este establecimiento todavía no cargó su
#: carta», que es cierto en ese modo. Lo que ata el número de la portada a los
#: datos es `test_el_establecimiento_de_la_portada_tiene_carta`, y `GET /health`
#: dice cuál de las dos implementaciones está sirviendo.
#:
#: Ninguno lleva `unidades_hoy`, igual que ninguno en `002`: la columna llegó en
#: `017` sin valor por defecto, así que todos quedan sin control de inventario.
#: Las pruebas que lo necesitan lo fijan por `fijar_unidades`, y lo deshacen.
_ITEMS_SEED = {
    1: ItemMenu(id=1, establecimiento_id=1, nombre="Arepa de huevo", precio_centavos=400000, disponible=True, categoria="Asados"),
    2: ItemMenu(id=2, establecimiento_id=1, nombre="Jugo de mango", precio_centavos=300000, disponible=True, categoria="Bebidas"),
    3: ItemMenu(id=3, establecimiento_id=2, nombre="Empanada", precio_centavos=250000, disponible=False),
    4: ItemMenu(id=4, establecimiento_id=3, nombre="Café americano", precio_centavos=200000, disponible=True),
}

_COLUMNAS = (
    "id, establecimiento_id, nombre, precio_centavos, disponible, "
    "imagen, categoria, descripcion, "
    "precio_promocional_centavos, promocion_desde, promocion_hasta, "
    "solo_en_promocion, unidades_hoy"
)


def _desde_fila(fila) -> ItemMenu:
    return ItemMenu(
        id=fila[0],
        establecimiento_id=fila[1],
        nombre=fila[2],
        precio_centavos=fila[3],
        disponible=fila[4],
        imagen=fila[5],
        categoria=fila[6],
        descripcion=fila[7],
        precio_promocional_centavos=fila[8],
        promocion_desde=fila[9],
        promocion_hasta=fila[10],
        solo_en_promocion=fila[11],
        unidades_hoy=fila[12],
    )


def buscar_por_id(item_id: int) -> ItemMenu | None:
    if not base_de_datos.hay_base_de_datos():
        return _ITEMS_SEED.get(item_id)

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        # Parámetro y no interpolación: `f"... WHERE id = {item_id}"` sería
        # inyección de SQL en cuanto el valor dejara de ser un entero validado.
        cur.execute(f"SELECT {_COLUMNAS} FROM menu_items WHERE id = %s", (item_id,))
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)


def buscar_por_establecimiento(establecimiento_id: int) -> list[ItemMenu]:
    """Ítems de un establecimiento, ordenados de forma estable.

    El orden se fija aquí y no se deja al azar del almacenamiento: una lista que
    cambia de orden entre dos llamadas idénticas obliga al consumidor a
    reordenar por su cuenta, y el contrato no promete ningún criterio.

    Contra PostgreSQL esto importa más, no menos: sin `ORDER BY`, el motor
    devuelve las filas en el orden que le convenga, y ese orden cambia cuando
    cambia el plan de ejecución.
    """
    if not base_de_datos.hay_base_de_datos():
        return sorted(
            (item for item in _ITEMS_SEED.values() if item.establecimiento_id == establecimiento_id),
            key=lambda item: item.id,
        )

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM menu_items "
            "WHERE establecimiento_id = %s ORDER BY id",
            (establecimiento_id,),
        )
        return [_desde_fila(f) for f in cur.fetchall()]


# ---------------------------------------------------------------------------
# Inventario del día (ADR-0015)
#
# Son las únicas escrituras del catálogo, y las tres tocan una sola columna.
# Un producto con `unidades_hoy` nulo no lleva cuenta: ninguna de ellas lo
# modifica, y así la carta de quien no cuenta se vende exactamente como antes.
# ---------------------------------------------------------------------------


def descontar_unidades(lineas: list[tuple[int, int]]) -> tuple[str, int] | None:
    """Descuenta las unidades de todas las líneas, o de ninguna.

    `lineas` son pares `(item_id, cantidad)`. Devuelve `None` si todo alcanzó,
    o `(nombre, quedan)` del primer producto que no alcanzó; en ese caso **no se
    descontó nada**, ni de él ni de los que venían antes.

    ### Por qué la condición viaja dentro del `UPDATE`

    Es la misma primitiva que `pedidos.repository.marcar_pagado`: leer, decidir
    y escribir deja una ventana, y en hora de almuerzo esa ventana tiene dos
    teléfonos dentro pidiendo la última arepa. Con `WHERE unidades_hoy >= %s`
    el motor solo deja que una de las dos escrituras encuentre la fila con
    saldo: la otra actualiza cero filas, y ese cero es la señal de que no
    alcanzó. `test_dos_reservas_de_la_ultima_unidad_solo_una_gana` lo ejecuta
    con dos hilos.

    Todas las líneas van en **una** transacción para que el todo-o-nada no
    dependa de compensar a mano: si la tercera línea no alcanza, el `rollback`
    devuelve las dos primeras sin que nadie tenga que acordarse de sumarlas.
    """
    if not lineas:
        return None

    # Por identificador, siempre en el mismo orden. Dos pedidos que descuentan
    # los mismos dos productos en orden distinto se bloquearían mutuamente
    # —cada uno esperando la fila que el otro ya tiene—, y el motor resolvería
    # el abrazo matando a uno con un error que no significa nada para quien
    # pidió. En memoria no hay bloqueo, pero el orden se comparte para que las
    # dos implementaciones fallen por el mismo producto.
    ordenadas = sorted(lineas)

    if not base_de_datos.hay_base_de_datos():
        for item_id, cantidad in ordenadas:
            item = _ITEMS_SEED.get(item_id)
            if item is not None and item.unidades_hoy is not None and item.unidades_hoy < cantidad:
                return item.nombre, item.unidades_hoy
        for item_id, cantidad in ordenadas:
            item = _ITEMS_SEED.get(item_id)
            if item is not None and item.unidades_hoy is not None:
                _ITEMS_SEED[item_id] = item.model_copy(
                    update={"unidades_hoy": item.unidades_hoy - cantidad}
                )
        return None

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        for item_id, cantidad in ordenadas:
            cur.execute(
                "UPDATE menu_items SET unidades_hoy = unidades_hoy - %s "
                "WHERE id = %s AND unidades_hoy IS NOT NULL AND unidades_hoy >= %s",
                (cantidad, item_id, cantidad),
            )
            if cur.rowcount == 1:
                continue

            # Cero filas tiene dos lecturas, y solo una es un rechazo: que el
            # producto no lleve cuenta (nulo) es lo normal, y se sigue. Esta
            # segunda consulta solo se paga en el camino que no descuenta.
            cur.execute(
                "SELECT nombre, unidades_hoy FROM menu_items WHERE id = %s",
                (item_id,),
            )
            fila = cur.fetchone()
            if fila is None or fila[1] is None:
                continue

            # Deshace lo que las líneas anteriores ya habían descontado. El
            # `with` cierra la transacción vacía que queda, sin escribir nada.
            conn.rollback()
            return fila[0], fila[1]

    return None


def devolver_unidades(lineas: list[tuple[int, int]]) -> None:
    """Suma de vuelta las unidades de un pedido que no se va a preparar.

    Solo donde hay cuenta: un producto que pasó a nulo después de la reserva
    —el mostrador apagó el control a media mañana— no recupera un número que
    ya no significa nada.
    """
    if not lineas:
        return

    if not base_de_datos.hay_base_de_datos():
        for item_id, cantidad in lineas:
            item = _ITEMS_SEED.get(item_id)
            if item is not None and item.unidades_hoy is not None:
                _ITEMS_SEED[item_id] = item.model_copy(
                    update={"unidades_hoy": item.unidades_hoy + cantidad}
                )
        return

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.executemany(
            "UPDATE menu_items SET unidades_hoy = unidades_hoy + %s "
            "WHERE id = %s AND unidades_hoy IS NOT NULL",
            [(cantidad, item_id) for item_id, cantidad in sorted(lineas)],
        )


def fijar_unidades(item_id: int, unidades: int | None) -> ItemMenu | None:
    """Escribe el conteo del día tal cual lo dice el mostrador.

    No suma ni resta sobre lo que había: el mostrador cuenta lo que tiene en la
    vitrina y ese número manda, aunque la API hubiera descontado otra cosa. Es
    también la forma de corregir una reserva que se quedó retenida en un pedido
    que nadie pagó (ADR-0015).

    Devuelve `None` si el producto no existe. Quién puede fijarlo —y que un
    producto de otro establecimiento se trate como inexistente— lo decide el
    servicio, no esta función.
    """
    if not base_de_datos.hay_base_de_datos():
        item = _ITEMS_SEED.get(item_id)
        if item is None:
            return None
        actualizado = item.model_copy(update={"unidades_hoy": unidades})
        _ITEMS_SEED[item_id] = actualizado
        return actualizado

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE menu_items SET unidades_hoy = %s WHERE id = %s "
            f"RETURNING {_COLUMNAS}",
            (unidades, item_id),
        )
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)
