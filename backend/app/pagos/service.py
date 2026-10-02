"""Lógica de negocio del contexto Pagos.

Dos operaciones con naturalezas opuestas, y esa oposición es el contenido de
[ADR-0003](../../../docs/adr/0003-estrategia-integracion.md):

- `iniciar_intento` es **síncrona**. El usuario está esperando y necesita saber
  a dónde ir. Si algo falla, falla delante de él y puede reintentar.
- `procesar_evento` es **asíncrona**. Nadie espera. Llega cuando la pasarela
  decide, puede llegar repetida y puede no llegar nunca.

Pagos no escribe `Pedido`: cuando un cobro se aprueba, pide a
`pedidos.service.confirmar_pago` que haga la transición. Pedidos es su único
escritor (ADR-0002) y además es quien garantiza la idempotencia de esa
transición.
"""
import hashlib
import hmac
import os
import secrets

from app.pagos import repository
from app.pagos.contracts import EstadoPago, IntentoPagoPublicado, MetodoDePago
from app.pagos.models import IntentoPago
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import EstadoPedido, PedidoPublicado

#: Secreto compartido con la pasarela. **Sin valor por defecto, a propósito.**
#:
#: Antes había uno —`"secreto-de-desarrollo"`— para que el repositorio fuera
#: ejecutable sin credenciales. La consecuencia, descubierta en la auditoría de
#: la semana 9, es que el despliegue nunca definió la variable y quedó
#: verificando las firmas contra una cadena que **está en un repositorio
#: público**: cualquiera podía firmar un evento válido y obtener un código de
#: canje sin pagar ([V-11](../../../docs/violaciones.md)).
#:
#: Ahora falla en cerrado. Sin la variable, `firma_valida` rechaza **todo**
#: evento. Un sistema sin su secreto deja de aceptar confirmaciones de pago,
#: que es molesto y visible; con un secreto público aceptaba pagos falsos, que
#: es peor y silencioso.
#:
#: Las pruebas y el desarrollo local la definen explícitamente
#: (`tests/conftest.py`). Que haya que definirla es el punto: un secreto que se
#: puede omitir termina omitido.
_SECRETO_PASARELA = os.getenv("PIDEUTB_SECRETO_PASARELA", "")

_URL_CHECKOUT = "https://sandbox.wompi.co/checkout"


class PedidoNoEncontradoError(Exception):
    pass


class PedidoNoCobrableError(Exception):
    pass


class ReferenciaDesconocidaError(Exception):
    pass


# --------------------------------------------------------------------------
# Verificación de la firma del webhook
# --------------------------------------------------------------------------

class SecretoNoConfiguradoError(RuntimeError):
    """No hay `PIDEUTB_SECRETO_PASARELA`, así que no se puede verificar nada."""


def _secreto() -> str:
    """Devuelve el secreto o se niega a seguir.

    Se lee en cada llamada y no al importar el módulo para que las pruebas
    puedan activarlo y desactivarlo, y para que un despliegue que añada la
    variable no necesite reiniciar para que surta efecto.
    """
    secreto = os.getenv("PIDEUTB_SECRETO_PASARELA", "").strip()
    if not secreto:
        raise SecretoNoConfiguradoError(
            "Falta PIDEUTB_SECRETO_PASARELA. Sin ella no se puede distinguir un "
            "aviso legítimo de la pasarela de uno falsificado."
        )
    return secreto


def firmar(cuerpo: bytes) -> str:
    """Firma HMAC-SHA256 del cuerpo de un evento.

    Se expone porque las pruebas necesitan construir eventos legítimos. Que el
    mismo código produzca y verifique la firma es aceptable aquí porque el
    secreto es lo que se está comprobando, no el algoritmo.
    """
    return hmac.new(_secreto().encode(), cuerpo, hashlib.sha256).hexdigest()


def firma_valida(cuerpo: bytes, firma: str | None) -> bool:
    """Compara la firma recibida con la esperada en tiempo constante.

    `hmac.compare_digest` y no `==`: una comparación que termina en el primer
    byte distinto filtra, por su duración, cuántos bytes acertó quien la
    intenta, y eso permite descubrir la firma correcta a fuerza de intentos.
    """
    if not firma:
        return False

    try:
        esperada = firmar(cuerpo)
    except SecretoNoConfiguradoError:
        # Fallar en cerrado: sin secreto no hay forma de distinguir un aviso
        # legítimo de uno falsificado, así que se rechazan todos. La alternativa
        # —aceptarlos— convierte un error de configuración en una vía para
        # cobrar sin pagar.
        return False

    return hmac.compare_digest(esperada, firma)


# --------------------------------------------------------------------------
# Operación síncrona
# --------------------------------------------------------------------------

def iniciar_intento(pedido_id: int, metodo: MetodoDePago) -> IntentoPagoPublicado:
    """Abre un cobro y devuelve a dónde enviar al usuario.

    **Es idempotente por pedido**: si ya hay un intento pendiente se devuelve
    ese mismo, en vez de abrir un segundo cobro. Sin esto, pulsar «Pagar» dos
    veces —o un reintento del navegador— dejaría dos transacciones vivas sobre
    el mismo pedido y solo una quedaría reconciliada.

    Lo que esta función **no** devuelve es si el cobro salió bien, porque en
    este instante todavía no existe esa información. Prometerlo obligaría a
    esperar a la pasarela dentro de la petición, que es la alternativa que
    ADR-0003 descarta.
    """
    pedido = pedidos_service.obtener_pedido(pedido_id)
    if pedido is None:
        raise PedidoNoEncontradoError(f"El pedido {pedido_id} no existe")

    if pedido.estado is not EstadoPedido.PENDIENTE_PAGO:
        raise PedidoNoCobrableError(
            f"El pedido {pedido_id} está en estado '{pedido.estado.value}' y ya no admite cobro"
        )

    existente = repository.buscar_pendiente_de_pedido(pedido_id)
    if existente is not None:
        return _publicar(existente)

    referencia = f"pago-{pedido_id}-{secrets.token_hex(3)}"
    intento = IntentoPago(
        referencia_pago=referencia,
        pedido_id=pedido_id,
        monto_centavos=pedido.total_centavos,
        metodo=metodo,
        estado_pago=EstadoPago.PENDIENTE,
        url_checkout=f"{_URL_CHECKOUT}/{referencia}",
    )
    return _publicar(repository.guardar(intento))


# --------------------------------------------------------------------------
# Operación asíncrona
# --------------------------------------------------------------------------

def procesar_evento(
    referencia_pago: str, estado_pago: EstadoPago
) -> tuple[PedidoPublicado, bool]:
    """Aplica una confirmación de la pasarela. Devuelve `(pedido, duplicado)`.

    La referencia la generó PideUTB al abrir el intento, no la pasarela: por
    eso un evento con una referencia que no conocemos es `404` y no un pedido
    nuevo. Si la generase la pasarela no habría forma de distinguir un aviso
    legítimo de uno inventado.

    Un `duplicado: True` **no es un error**: es la señal de que la idempotencia
    hizo su trabajo ante un reintento de la pasarela, y por eso se responde
    igualmente con `202`.
    """
    intento = repository.buscar_por_referencia(referencia_pago)
    if intento is None:
        raise ReferenciaDesconocidaError(
            f"La referencia de pago '{referencia_pago}' no corresponde a ningún intento"
        )

    ya_estaba_resuelto = intento.estado_pago is not EstadoPago.PENDIENTE

    if estado_pago is EstadoPago.APROBADO:
        # Pedidos es quien ejecuta la transición y quien garantiza que hacerla
        # dos veces no genere un segundo código de canje.
        pedido, ya_estaba_pagado = pedidos_service.confirmar_pago(intento.pedido_id)
        repository.guardar(intento.model_copy(update={"estado_pago": EstadoPago.APROBADO}))
        return pedido, ya_estaba_pagado

    if estado_pago is EstadoPago.RECHAZADO:
        repository.guardar(intento.model_copy(update={"estado_pago": EstadoPago.RECHAZADO}))
        return _pedido_de(intento.pedido_id), ya_estaba_resuelto

    # `pendiente`: la pasarela informa de un cambio que no resuelve nada. Se
    # acusa recibo y no se toca el pedido — actuar aquí sería adivinar.
    return _pedido_de(intento.pedido_id), ya_estaba_resuelto


def _pedido_de(pedido_id: int) -> PedidoPublicado:
    pedido = pedidos_service.obtener_pedido(pedido_id)
    if pedido is None:
        raise PedidoNoEncontradoError(f"El pedido {pedido_id} no existe")
    return pedido


def _publicar(intento: IntentoPago) -> IntentoPagoPublicado:
    return IntentoPagoPublicado(
        referencia_pago=intento.referencia_pago,
        pedido_id=intento.pedido_id,
        monto_centavos=intento.monto_centavos,
        estado_pago=intento.estado_pago,
        url_checkout=intento.url_checkout,
    )
