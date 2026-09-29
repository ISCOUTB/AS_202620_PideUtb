"""Acceso a datos del módulo `pedidos`.

Solo este módulo lee y escribe la tabla `pedidos`.

### Qué cambió al migrar a PostgreSQL

**Los identificadores los genera la base de datos.** Antes había un
`siguiente_id()` que el servicio llamaba antes de construir el pedido; ya no
existe. Era un contador en memoria del proceso, y con dos instancias desplegadas
las dos habrían empezado por 1 — el ejemplo concreto con el que
[V-09](../../../docs/violaciones.md) describía el problema. Ahora se inserta sin
identificador y la columna `GENERATED ALWAYS AS IDENTITY` lo asigna.

**Confirmar un pago es una escritura condicional.** `marcar_pagado` no lee,
decide y escribe: hace un `UPDATE ... WHERE estado = 'pendiente_pago'` en una
sola instrucción. Es la primitiva con la que `comparacion-despliegue.md` §1.1
justificó elegir PostgreSQL, y aquí es lo que sostiene la promesa de
idempotencia de [ADR-0003](../../../docs/adr/0003-estrategia-integracion.md): la
pasarela entrega al-menos-una-vez, así que dos avisos del mismo pago pueden
llegar a la vez a dos trabajadores distintos. Con leer-decidir-escribir, los dos
verían «pendiente» y se generarían dos códigos de canje.

Cuando `PIDEUTB_DATABASE_URL` no está configurada se usa el almacenamiento en
memoria, que reproduce la misma semántica.
"""
from app import base_de_datos
from app.pedidos.contracts import EstadoPedido
from app.pedidos.models import Pedido

_PEDIDOS: dict[int, Pedido] = {}
_contador = 0

_COLUMNAS = (
    "id, establecimiento_id, item_id, nombre_item, precio_unitario_centavos, "
    "cantidad, total_centavos, estado, codigo_canje"
)


def _desde_fila(fila) -> Pedido:
    return Pedido(
        id=fila[0],
        establecimiento_id=fila[1],
        item_id=fila[2],
        nombre_item=fila[3],
        precio_unitario_centavos=fila[4],
        cantidad=fila[5],
        total_centavos=fila[6],
        estado=EstadoPedido(fila[7]),
        codigo_canje=fila[8],
    )


def crear(
    *,
    establecimiento_id: int,
    item_id: int,
    nombre_item: str,
    precio_unitario_centavos: int,
    cantidad: int,
    total_centavos: int,
) -> Pedido:
    """Inserta un pedido nuevo y devuelve el que quedó guardado, con su id.

    Los argumentos son de palabra clave obligatoria: son seis y cuatro de ellos
    son enteros, así que una llamada posicional se equivocaría de orden tarde o
    temprano y escribiría un importe donde va una cantidad.
    """
    if not base_de_datos.hay_base_de_datos():
        global _contador
        _contador += 1
        pedido = Pedido(
            id=_contador,
            establecimiento_id=establecimiento_id,
            item_id=item_id,
            nombre_item=nombre_item,
            precio_unitario_centavos=precio_unitario_centavos,
            cantidad=cantidad,
            total_centavos=total_centavos,
            estado=EstadoPedido.PENDIENTE_PAGO,
        )
        _PEDIDOS[pedido.id] = pedido
        return pedido

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pedidos (establecimiento_id, item_id, nombre_item, "
            "precio_unitario_centavos, cantidad, total_centavos) "
            f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLUMNAS}",
            (
                establecimiento_id,
                item_id,
                nombre_item,
                precio_unitario_centavos,
                cantidad,
                total_centavos,
            ),
        )
        return _desde_fila(cur.fetchone())


def guardar(pedido: Pedido) -> Pedido:
    """Persiste los cambios de un pedido que ya existe.

    No crea: un pedido nuevo entra por `crear`, que es quien deja que la base de
    datos asigne el identificador.
    """
    if not base_de_datos.hay_base_de_datos():
        _PEDIDOS[pedido.id] = pedido
        return pedido

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET estado = %s, codigo_canje = %s, "
            f"actualizado_en = now() WHERE id = %s RETURNING {_COLUMNAS}",
            (pedido.estado.value, pedido.codigo_canje, pedido.id),
        )
        fila = cur.fetchone()

    if fila is None:
        raise LookupError(f"El pedido {pedido.id} no existe")
    return _desde_fila(fila)


def marcar_pagado(pedido_id: int, codigo_canje: str) -> Pedido | None:
    """Transición atómica `pendiente_pago` → `pagado`.

    Devuelve el pedido actualizado, o **`None` si ya no estaba pendiente** —lo
    que significa que otro aviso de la misma pasarela ganó la carrera—.

    La condición viaja dentro del `UPDATE`, no en un `if` previo. Esa diferencia
    es la que hace que dos entregas simultáneas del mismo webhook no generen dos
    códigos de canje: el motor solo deja que una de las dos encuentre la fila en
    estado `pendiente_pago`.
    """
    if not base_de_datos.hay_base_de_datos():
        pedido = _PEDIDOS.get(pedido_id)
        if pedido is None or pedido.estado is not EstadoPedido.PENDIENTE_PAGO:
            return None
        actualizado = pedido.model_copy(
            update={"estado": EstadoPedido.PAGADO, "codigo_canje": codigo_canje}
        )
        _PEDIDOS[pedido_id] = actualizado
        return actualizado

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET estado = 'pagado', codigo_canje = %s, "
            "actualizado_en = now() "
            "WHERE id = %s AND estado = 'pendiente_pago' "
            f"RETURNING {_COLUMNAS}",
            (codigo_canje, pedido_id),
        )
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)


def buscar_por_id(pedido_id: int) -> Pedido | None:
    if not base_de_datos.hay_base_de_datos():
        return _PEDIDOS.get(pedido_id)

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {_COLUMNAS} FROM pedidos WHERE id = %s", (pedido_id,))
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)


def buscar_por_establecimiento(establecimiento_id: int) -> list[Pedido]:
    """Pedidos de un establecimiento, del más reciente al más antiguo.

    Quien atiende el mostrador necesita ver arriba lo que acaba de entrar, no lo
    que lleva media hora resuelto. Con el orden al revés, el pedido urgente
    aparecería al final de la lista justo en hora pico.
    """
    if not base_de_datos.hay_base_de_datos():
        return sorted(
            (p for p in _PEDIDOS.values() if p.establecimiento_id == establecimiento_id),
            key=lambda p: p.id,
            reverse=True,
        )

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM pedidos WHERE establecimiento_id = %s "
            "ORDER BY id DESC",
            (establecimiento_id,),
        )
        return [_desde_fila(f) for f in cur.fetchall()]
