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
from urllib.parse import urlencode

from app.pagos import repository
from app.pagos.contracts import EstadoPago, IntentoPagoPublicado, MetodoDePago
from app.pagos.models import IntentoPago
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import EstadoPedido, PedidoPublicado

#: Secreto compartido con la pasarela. **Sin valor por defecto, a propósito.**
#:
#: Antes había uno, para que el repositorio fuera ejecutable sin credenciales.
#: El valor no se reproduce aquí a propósito: está en el historial de git y no
#: se puede borrar de ahí, pero repetirlo en el código vigente lo deja al
#: alcance de un `grep` y no añade nada que no diga esta explicación.
#:
#: La consecuencia de aquel valor por defecto, descubierta en la auditoría de
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

#: Dirección de una pasarela **de mentira**, o cadena vacía si no la hay.
#:
#: Cuando está puesta, `url_checkout` apunta a ella en vez de a Wompi y se
#: habilita `simular_evento`. Sirve para poder recorrer el flujo entero —crear
#: el pedido, pagarlo, ver el código— sin una cuenta de pasarela, que es lo que
#: hace falta para una demostración y para desarrollar sin red.
#:
#: **No es un modo de prueba del cobro real: es otro cobrador.** La diferencia
#: importa: con la variable puesta, cualquiera que alcance el simulador puede
#: dar un pedido por pagado. Por eso no tiene valor por defecto, igual que el
#: secreto, y por eso el despliegue de producción no la define.
def _url_pasarela_simulada() -> str:
    """Se lee en cada llamada, por lo mismo que `_secreto`."""
    return os.getenv("PIDEUTB_URL_PASARELA_SIMULADA", "").strip()


def _url_de_checkout(
    referencia: str, monto_centavos: int, metodo: MetodoDePago
) -> str:
    """A dónde mandar a quien va a pagar.

    La pasarela simulada recibe el importe y el método como parámetros porque
    es lo que hace una de verdad: el widget de Wompi también se abre con el
    monto y la referencia en la URL. Son datos del pedido, no de la persona.

    Lo que se manda ahí **solo decide lo que se pinta**. La confirmación viaja
    por referencia y el importe que cuenta es el que está guardado, así que
    cambiar `monto` a mano en la barra de direcciones no cambia lo que se
    cobra ni lo que queda registrado.
    """
    simulada = _url_pasarela_simulada()
    if not simulada:
        return f"{_URL_CHECKOUT}/{referencia}"

    parametros = urlencode(
        {"referencia": referencia, "monto": monto_centavos, "metodo": metodo.value}
    )
    return f"{simulada}?{parametros}"


class PedidoNoEncontradoError(Exception):
    pass


class PedidoNoCobrableError(Exception):
    pass


class ReferenciaDesconocidaError(Exception):
    pass


# --------------------------------------------------------------------------
# Verificación de la firma del webhook
# --------------------------------------------------------------------------

class PasarelaSimuladaApagadaError(RuntimeError):
    """Se intentó usar la pasarela de mentira donde no la hay."""


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
        url_checkout=_url_de_checkout(referencia, pedido.total_centavos, metodo),
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


def simular_evento(
    referencia_pago: str, estado_pago: EstadoPago
) -> tuple[PedidoPublicado, bool]:
    """Lo que haría la pasarela, cuando la pasarela somos nosotros.

    Entra por la **misma** puerta que un aviso real: `procesar_evento`. No es
    un atajo que marque el pedido como pagado, y la diferencia es el motivo de
    que esta función exista en vez de un `if` en el frontend.

    [ADR-0003](../../../docs/adr/0003-estrategia-integracion.md) dice que la
    confirmación llega por un canal asíncrono y que el cliente se entera
    consultando. Si la simulación devolviera el pedido ya pagado en la misma
    respuesta del botón, la demostración enseñaría una arquitectura distinta de
    la que está escrita: el sondeo, la idempotencia y la ventana de
    `conciliar` dejarían de ejercitarse justo en la pantalla donde se mira.

    Aquí el botón solo dispara el evento. Quien lo pulsó sigue sin saber nada
    hasta que su propia consulta le diga que el pedido cambió de estado, que es
    exactamente lo que pasa con una pasarela real.

    No lleva firma porque en esta configuración **no hay dos partes**: firmar
    con el secreto para verificarlo acto seguido no demuestra nada. Lo que
    protege es que la operación no existe sin
    `PIDEUTB_URL_PASARELA_SIMULADA`.
    """
    if not _url_pasarela_simulada():
        raise PasarelaSimuladaApagadaError(
            "No hay pasarela simulada en este despliegue."
        )

    return procesar_evento(referencia_pago, estado_pago)


def conciliar() -> list[str]:
    """Referencias de pago que quedaron descolgadas, si las hay.

    Devuelve los intentos que siguen en `pendiente` **aunque su pedido ya esté
    pagado**. En un sistema sano la lista está vacía.

    ### Por qué puede no estarlo

    `procesar_evento` escribe en dos sitios y **no en una sola transacción**:
    primero pide a Pedidos que confirme —lo que genera el código de canje— y
    después marca el intento como aprobado. Entre las dos hay una ventana. Si el
    proceso muere ahí, o si la segunda escritura falla, el pedido queda pagado y
    su intento pendiente.

    El orden está elegido y no es casual: **falla hacia el cliente**. Así, un
    corte deja a alguien que pagó con su código en la mano y a nosotros con la
    contabilidad desactualizada. Al revés —marcar el intento primero— dejaría a
    quien pagó sin código, que es el fallo que sí se nota y el que no se puede
    reparar solo.

    ### Por qué no se cierra con una transacción única

    Se puede, y se evaluó. Exigiría que Pagos y Pedidos compartieran una
    conexión, es decir que un contexto pasara su transacción al otro. Eso rompe
    [ADR-0001](../../../docs/adr/0001-estilo-arquitectonico.md), que es lo único
    que hoy mantiene separados los contextos, y lo rompe en el sitio más difícil
    de revertir: la capa de datos.

    Se prefirió **conservar la frontera y hacer la ventana visible**, que es lo
    que hace esta función. El detalle del descarte, con las cuatro opciones
    evaluadas, está en
    [arc42 §6.7](../../../docs/arc42/arc42.md#fallos-parciales).

    ### Por qué no es una saga

    Una saga coordina escrituras en **sistemas distintos**, donde no existe una
    transacción común y hay que compensar. Aquí las dos escrituras van a la
    misma base de datos: no falta un coordinador, falta una transacción. Llamar
    saga a esto sería ponerle un nombre grande a un problema local.
    """
    pagados = pedidos_service.ids_pagados()
    descolgados = repository.buscar_pendientes_de_pedidos(pagados)
    return [intento.referencia_pago for intento in descolgados]


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
