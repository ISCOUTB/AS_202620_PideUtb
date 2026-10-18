"""Acceso a datos del contexto Pagos.

Solo este módulo lee y escribe la tabla de pagos (`pagos_intentos`).

Se indexa por `referencia_pago` y además por `pedido_id`, porque las dos
búsquedas responden a preguntas distintas: el webhook llega con la referencia y
no sabe nada del pedido, mientras que el frontend pide el intento de un pedido y
no conoce la referencia hasta que se la devolvemos.

### Lo que la migración a PostgreSQL añadió

La idempotencia de «pulsar Pagar dos veces» ya no depende solo de que el código
consulte antes de escribir. La migración crea un **índice único parcial** sobre
`pedido_id` limitado a los intentos pendientes, así que dos peticiones
simultáneas no pueden abrir dos cobros sobre el mismo pedido aunque las dos
lean «no hay ninguno» a la vez.

Es parcial a propósito: un pedido sí puede acumular varios intentos resueltos,
si el primero fue rechazado y el usuario reintentó con otro método.

Cuando `PIDEUTB_DATABASE_URL` no está configurada se usa el almacenamiento en
memoria, que reproduce la misma semántica.
"""
from app import base_de_datos
from app.pagos.contracts import EstadoPago, MetodoDePago
from app.pagos.models import IntentoPago

_INTENTOS: dict[str, IntentoPago] = {}

_COLUMNAS = (
    "referencia_pago, pedido_id, monto_centavos, metodo, estado_pago, url_checkout"
)


def _desde_fila(fila) -> IntentoPago:
    return IntentoPago(
        referencia_pago=fila[0],
        pedido_id=fila[1],
        monto_centavos=fila[2],
        metodo=MetodoDePago(fila[3]),
        estado_pago=EstadoPago(fila[4]),
        url_checkout=fila[5],
    )


def guardar(intento: IntentoPago) -> IntentoPago:
    """Inserta o actualiza un intento, indexado por su referencia.

    Es un `upsert` porque el mismo intento se escribe dos veces en su vida: al
    abrirlo y al resolverlo con el aviso de la pasarela.
    """
    if not base_de_datos.hay_base_de_datos():
        _INTENTOS[intento.referencia_pago] = intento
        return intento

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pagos_intentos (referencia_pago, pedido_id, "
            "monto_centavos, metodo, estado_pago, url_checkout) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (referencia_pago) DO UPDATE SET estado_pago = EXCLUDED.estado_pago "
            f"RETURNING {_COLUMNAS}",
            (
                intento.referencia_pago,
                intento.pedido_id,
                intento.monto_centavos,
                intento.metodo.value,
                intento.estado_pago.value,
                intento.url_checkout,
            ),
        )
        return _desde_fila(cur.fetchone())


def buscar_por_referencia(referencia_pago: str) -> IntentoPago | None:
    if not base_de_datos.hay_base_de_datos():
        return _INTENTOS.get(referencia_pago)

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM pagos_intentos WHERE referencia_pago = %s",
            (referencia_pago,),
        )
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)


def buscar_pendientes_de_pedidos(pedido_ids: list[int]) -> list[IntentoPago]:
    """Intentos que siguen `pendiente` para pedidos que se le indiquen.

    Existe para detectar la ventana de inconsistencia que describe
    [arc42 §6.7](../../../docs/arc42/arc42.md#fallos-parciales): `procesar_evento`
    escribe en dos transacciones —primero el pedido, después el intento— y un
    corte entre ambas deja el pedido pagado con su intento todavía pendiente.

    Recibe los identificadores en lugar de cruzar las dos tablas en SQL **a
    propósito**. Un `JOIN` entre `pagos_intentos` y `pedidos` dentro de este
    repositorio sería que el contexto Pagos leyera la tabla de Pedidos, que es
    exactamente lo que [ADR-0001](../../../docs/adr/0001-estilo-arquitectonico.md)
    prohíbe. El cruce lo hace quien tiene derecho a preguntar a los dos: el
    servicio, llamando a la interfaz pública de cada contexto.
    """
    if not pedido_ids:
        return []

    if not base_de_datos.hay_base_de_datos():
        return [
            intento for intento in _INTENTOS.values()
            if intento.pedido_id in pedido_ids
            and intento.estado_pago is EstadoPago.PENDIENTE
        ]

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM pagos_intentos "
            "WHERE pedido_id = ANY(%s) AND estado_pago = 'pendiente' "
            "ORDER BY pedido_id",
            (pedido_ids,),
        )
        return [_desde_fila(fila) for fila in cur.fetchall()]


def buscar_pendiente_de_pedido(pedido_id: int) -> IntentoPago | None:
    """Intento aún sin resolver para un pedido, si lo hay.

    Es lo que hace idempotente a `iniciar_intento`: sin esta consulta, pulsar
    dos veces «Pagar» abriría dos cobros sobre el mismo pedido.

    Contra PostgreSQL, la consulta es la primera línea de defensa y el índice
    único parcial es la segunda: esta evita el caso normal, aquel evita el caso
    simultáneo, que ninguna consulta previa puede evitar por sí sola.
    """
    if not base_de_datos.hay_base_de_datos():
        for intento in _INTENTOS.values():
            if intento.pedido_id == pedido_id and intento.estado_pago is EstadoPago.PENDIENTE:
                return intento
        return None

    with base_de_datos.conexion() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_COLUMNAS} FROM pagos_intentos "
            "WHERE pedido_id = %s AND estado_pago = 'pendiente'",
            (pedido_id,),
        )
        fila = cur.fetchone()

    return None if fila is None else _desde_fila(fila)
