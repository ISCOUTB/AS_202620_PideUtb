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
_ITEMS_SEED = {
    1: ItemMenu(id=1, establecimiento_id=1, nombre="Arepa de huevo", precio_centavos=400000, disponible=True),
    2: ItemMenu(id=2, establecimiento_id=1, nombre="Jugo de mango", precio_centavos=300000, disponible=True),
    3: ItemMenu(id=3, establecimiento_id=2, nombre="Empanada", precio_centavos=250000, disponible=False),
    4: ItemMenu(id=4, establecimiento_id=3, nombre="Café americano", precio_centavos=200000, disponible=True),
}

_COLUMNAS = "id, establecimiento_id, nombre, precio_centavos, disponible"


def _desde_fila(fila) -> ItemMenu:
    return ItemMenu(
        id=fila[0],
        establecimiento_id=fila[1],
        nombre=fila[2],
        precio_centavos=fila[3],
        disponible=fila[4],
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
