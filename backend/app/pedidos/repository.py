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
from datetime import datetime, timezone

from app import base_de_datos
from app.pedidos.contracts import EstadoPedido
from app.pedidos.models import LineaPedido, Pedido

_PEDIDOS: dict[int, Pedido] = {}
_contador = 0
_contador_comprobantes = 0

#: Las columnas del pedido. Las de línea viven en `pedido_lineas` desde la
#: migración 004; las que quedaron en `pedidos` son histórico y no se leen.
_COLUMNAS = (
    "id, establecimiento_id, total_centavos, estado, codigo_canje, "
    "token_consulta, hora_recogida, nombre_cliente, correo_cliente, "
    "numero_comprobante, pagado_en, aviso_push_endpoint"
)

_COLUMNAS_LINEA = (
    "item_id, nombre_item, precio_unitario_centavos, cantidad, "
    "total_linea_centavos"
)


def _linea_desde_fila(fila) -> LineaPedido:
    return LineaPedido(
        item_id=fila[0],
        nombre_item=fila[1],
        precio_unitario_centavos=fila[2],
        cantidad=fila[3],
        total_linea_centavos=fila[4],
    )


def _lineas_de(cur, pedido_id: int) -> list[LineaPedido]:
    """Las líneas de un pedido, en orden estable.

    El orden sale del identificador de la línea y no del motor: sin `ORDER BY`
    PostgreSQL puede devolverlas en cualquier orden, y una carta que cambia de
    orden entre dos consultas se lee como un error del sistema.
    """
    cur.execute(
        f"SELECT {_COLUMNAS_LINEA} FROM pedido_lineas "
        "WHERE pedido_id = %s ORDER BY id",
        (pedido_id,),
    )
    return [_linea_desde_fila(f) for f in cur.fetchall()]


def _desde_fila(fila, lineas: list[LineaPedido]) -> Pedido:
    return Pedido(
        id=fila[0],
        establecimiento_id=fila[1],
        lineas=lineas,
        total_centavos=fila[2],
        estado=EstadoPedido(fila[3]),
        codigo_canje=fila[4],
        token_consulta=fila[5],
        hora_recogida=fila[6],
        nombre_cliente=fila[7],
        correo_cliente=fila[8],
        numero_comprobante=fila[9],
        pagado_en=fila[10],
        aviso_push_endpoint=fila[11],
    )


def crear(
    *,
    establecimiento_id: int,
    lineas: list[LineaPedido],
    total_centavos: int,
    token_consulta: str,
    hora_recogida: datetime | None = None,
    nombre_cliente: str | None = None,
    correo_cliente: str | None = None,
) -> Pedido:
    """Inserta un pedido con sus líneas y devuelve el que quedó guardado.

    Los argumentos son de palabra clave obligatoria: una llamada posicional se
    equivocaría de orden tarde o temprano y escribiría un importe donde va un
    establecimiento.

    **El pedido y sus líneas se escriben en la misma transacción.** No es una
    preferencia: entre el `INSERT` del pedido y el de sus líneas el total no
    cuadra con la suma, y el disparador que lo vigila es `DEFERRABLE INITIALLY
    DEFERRED` precisamente para dejar pasar ese instante. Partir esto en dos
    transacciones dejaría un pedido sin líneas visible para quien consulte.
    """
    if not lineas:
        raise ValueError("Un pedido necesita al menos una línea")

    if not base_de_datos.hay_base_de_datos():
        global _contador
        _contador += 1
        pedido = Pedido(
            id=_contador,
            establecimiento_id=establecimiento_id,
            lineas=lineas,
            total_centavos=total_centavos,
            estado=EstadoPedido.PENDIENTE_PAGO,
            token_consulta=token_consulta,
            hora_recogida=hora_recogida,
            nombre_cliente=nombre_cliente,
            correo_cliente=correo_cliente,
        )
        _PEDIDOS[pedido.id] = pedido
        return pedido

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pedidos (establecimiento_id, total_centavos, "
            "token_consulta, hora_recogida, nombre_cliente, correo_cliente) "
            f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLUMNAS}",
            (
                establecimiento_id,
                total_centavos,
                token_consulta,
                hora_recogida,
                nombre_cliente,
                correo_cliente,
            ),
        )
        fila = cur.fetchone()
        pedido_id = fila[0]

        cur.executemany(
            "INSERT INTO pedido_lineas (pedido_id, item_id, nombre_item, "
            "precio_unitario_centavos, cantidad, total_linea_centavos) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (
                    pedido_id,
                    l.item_id,
                    l.nombre_item,
                    l.precio_unitario_centavos,
                    l.cantidad,
                    l.total_linea_centavos,
                )
                for l in lineas
            ],
        )
        return _desde_fila(fila, _lineas_de(cur, pedido_id))


def guardar(pedido: Pedido, *, estado_esperado: EstadoPedido) -> Pedido | None:
    """Persiste los cambios de un pedido que ya existe, **si no se movió**.

    No crea: un pedido nuevo entra por `crear`, que es quien deja que la base de
    datos asigne el identificador.

    Devuelve **`None` si la fila ya no estaba en `estado_esperado`**, igual que
    `marcar_pagado` y por el mismo motivo: la condición viaja dentro del
    `UPDATE` y no en un `if` previo de quien llama.

    Esto era un defecto, y uno de los que no se ven hasta que hay dos personas.
    Antes la instrucción era `UPDATE ... WHERE id = %s` a secas, y
    `avanzar_estado` validaba la transición **antes**, contra un estado que
    había leído en otra consulta. Entre la lectura y la escritura no había nada,
    y en un mostrador esa ventana tiene dos personas dentro: A lee `pagado`, B
    mueve el pedido a `en_preparacion` y luego a `listo`, y entonces aterriza la
    escritura de A y el pedido **retrocede** a `en_preparacion`. Ni falla, ni
    avisa, ni queda registro.

    Lo detectó la auditoría de la semana 12 por lectura estática, contrastando
    la tabla de consistencia de arc42 —que promete `UPDATE ... WHERE estado =
    <el esperado>`— con lo que hacía esta función.
    """
    if not base_de_datos.hay_base_de_datos():
        actual = _PEDIDOS.get(pedido.id)
        if actual is None:
            raise LookupError(f"El pedido {pedido.id} no existe")
        if actual.estado is not estado_esperado:
            return None
        _PEDIDOS[pedido.id] = pedido
        return pedido

    existe = True
    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET estado = %s, codigo_canje = %s, "
            "actualizado_en = now() WHERE id = %s AND estado = %s "
            f"RETURNING {_COLUMNAS}",
            (
                pedido.estado.value,
                pedido.codigo_canje,
                pedido.id,
                estado_esperado.value,
            ),
        )
        fila = cur.fetchone()
        lineas = _lineas_de(cur, pedido.id) if fila is not None else []
        if fila is None:
            # Cero filas puede ser «no existe» o «ya no está en ese estado», y
            # la diferencia le importa a quien llama: una es un 404 y la otra un
            # 409. Esta segunda consulta solo se paga en el camino del fallo.
            cur.execute("SELECT 1 FROM pedidos WHERE id = %s", (pedido.id,))
            existe = cur.fetchone() is not None

    if fila is not None:
        return _desde_fila(fila, lineas)
    if not existe:
        raise LookupError(f"El pedido {pedido.id} no existe")
    return None


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
        global _contador_comprobantes
        _contador_comprobantes += 1
        actualizado = pedido.model_copy(
            update={
                "estado": EstadoPedido.PAGADO,
                "codigo_canje": codigo_canje,
                "numero_comprobante": _contador_comprobantes,
                "pagado_en": datetime.now(timezone.utc),
            }
        )
        _PEDIDOS[pedido_id] = actualizado
        return actualizado

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET estado = 'pagado', codigo_canje = %s, "
            "numero_comprobante = nextval('comprobantes_consecutivo'), "
            "pagado_en = now(), actualizado_en = now() "
            "WHERE id = %s AND estado = 'pendiente_pago' "
            f"RETURNING {_COLUMNAS}",
            (codigo_canje, pedido_id),
        )
        fila = cur.fetchone()
        lineas = _lineas_de(cur, pedido_id) if fila is not None else []

    return None if fila is None else _desde_fila(fila, lineas)


def guardar_aviso_push(pedido_id: int, endpoint: str) -> None:
    """Deja anotado a dónde avisar cuando el pedido esté listo."""
    if not base_de_datos.hay_base_de_datos():
        _PEDIDOS[pedido_id] = _PEDIDOS[pedido_id].model_copy(
            update={"aviso_push_endpoint": endpoint}
        )
        return

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET aviso_push_endpoint = %s WHERE id = %s",
            (endpoint, pedido_id),
        )


def tomar_aviso_push(pedido_id: int) -> str | None:
    """Devuelve la dirección del aviso **y la borra**, en una sola instrucción.

    En una sola para que dos llamadas simultáneas no puedan llevarse la misma
    dirección: el aviso se manda una vez. Y se borra porque ya no le sirve a
    nadie, y un dato que no se guarda no se puede filtrar.
    """
    if not base_de_datos.hay_base_de_datos():
        pedido = _PEDIDOS.get(pedido_id)
        if pedido is None or pedido.aviso_push_endpoint is None:
            return None
        _PEDIDOS[pedido_id] = pedido.model_copy(update={"aviso_push_endpoint": None})
        return pedido.aviso_push_endpoint

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "WITH previo AS ("
            "  SELECT id, aviso_push_endpoint FROM pedidos "
            "  WHERE id = %s AND aviso_push_endpoint IS NOT NULL FOR UPDATE"
            ") "
            "UPDATE pedidos SET aviso_push_endpoint = NULL FROM previo "
            "WHERE pedidos.id = previo.id RETURNING previo.aviso_push_endpoint",
            (pedido_id,),
        )
        fila = cur.fetchone()

    return None if fila is None else fila[0]


def buscar_por_id(pedido_id: int) -> Pedido | None:
    if not base_de_datos.hay_base_de_datos():
        return _PEDIDOS.get(pedido_id)

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {_COLUMNAS} FROM pedidos WHERE id = %s", (pedido_id,))
        fila = cur.fetchone()
        lineas = _lineas_de(cur, pedido_id) if fila is not None else []

    return None if fila is None else _desde_fila(fila, lineas)


def buscar_ids_pagados() -> list[int]:
    """Identificadores de los pedidos en estado `pagado`.

    Lo usa la conciliación de `pagos.service` para detectar intentos que
    quedaron descolgados. Devuelve solo identificadores y no pedidos enteros
    porque es lo único que hace falta: quien pregunta va a cruzarlos con otra
    tabla, no a mostrarlos.
    """
    if not base_de_datos.hay_base_de_datos():
        return sorted(
            p.id for p in _PEDIDOS.values() if p.estado is EstadoPedido.PAGADO
        )

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM pedidos WHERE estado = 'pagado' ORDER BY id")
        return [fila[0] for fila in cur.fetchall()]


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
        filas = cur.fetchall()

        # Las líneas de toda la cola en **una** consulta y no una por pedido.
        # Con veinte pedidos en pantalla, lo segundo son veintiuna idas a la
        # base para pintar una lista: el caso que la hora pico convierte en
        # problema.
        por_pedido: dict[int, list[LineaPedido]] = {f[0]: [] for f in filas}
        if por_pedido:
            cur.execute(
                f"SELECT pedido_id, {_COLUMNAS_LINEA} FROM pedido_lineas "
                "WHERE pedido_id = ANY(%s) ORDER BY pedido_id, id",
                (list(por_pedido),),
            )
            for fila_linea in cur.fetchall():
                por_pedido[fila_linea[0]].append(_linea_desde_fila(fila_linea[1:]))

        return [_desde_fila(f, por_pedido[f[0]]) for f in filas]
