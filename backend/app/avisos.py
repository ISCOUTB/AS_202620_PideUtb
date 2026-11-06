"""El aviso al teléfono del cliente cuando su pedido está listo (Web Push).

### Qué hace falta

`PIDEUTB_VAPID_CLAVE_PRIVADA`: 32 bytes aleatorios en base64url. **Sin ella esta
función no existe**: `GET /v1/avisos/clave-publica` responde 404, el sitio no
ofrece el botón, y el pedido funciona igual que antes. La clave pública se deriva
de la privada, para que no puedan quedar dos variables que no se correspondan.

### El aviso va vacío a propósito

Web Push permite mandar un texto, pero hay que cifrarlo a mano (RFC 8291). Aquí no
hace falta: la notificación dice siempre lo mismo y la escribe el Service Worker
(`sitio/sw.js`). Solo se firma quién manda (VAPID, RFC 8292), que son veinte
líneas sobre una biblioteca probada en vez de un cifrado escrito aquí. Y deja una
ventaja: **el código de canje nunca pasa por Google ni por Apple**, ni aparece en
la pantalla de bloqueo, que es de donde alguien más podría leerlo.

### Por qué no `pywebpush`

Arrastra `aiohttp` y `requests` para hacer un POST. La S13 sacó de la imagen ocho
paquetes que no se usaban, y la API corre con 192 MB (ADR-0008). `cryptography` se
importa solo al firmar, así que un despliegue sin avisos no paga su memoria.

### Sin reintentos

Como el comprobante (ADR-0012): es una comodidad. Si el aviso no llega, la
pantalla del cliente se entera en la siguiente consulta.
"""
from __future__ import annotations

import base64
import http.client
import json
import logging
import os
import re
import time
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import eventos
from app.esquemas_comunes import ErrorDeNegocio
from app.pedidos import service as pedidos_service

router = APIRouter(prefix="/v1/avisos", tags=["avisos"])

_LOG = logging.getLogger("pideutb")

#: Quién manda el aviso. La exige el estándar, y los servicios de push la usan
#: para contactar a quien esté abusando.
_CONTACTO_POR_DEFECTO = "https://pideutb.iscoutb.dev"

#: La firma caduca en una hora. Se genera en cada envío, así que no hay motivo para
#: pedir más, y alguno de los servicios no acepta plazos largos.
_SEGUNDOS_DE_VALIDEZ = 3600

#: Si el teléfono está apagado, el servicio guarda el aviso una hora. Pasado eso ya
#: no es noticia: es un pedido frío.
_SEGUNDOS_DE_VIDA = 3600

_SEGUNDOS_DE_ESPERA = 10

#: 32 bytes en base64url, sin relleno, son siempre 43 caracteres.
_FORMATO_DE_LA_CLAVE = re.compile(r"[A-Za-z0-9_-]{43}")


class ClavePublicaResponse(BaseModel):
    """Lo que el navegador necesita para suscribirse."""

    clave_publica: str = Field(min_length=1)


def _base64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _clave_privada():
    """La clave, o `None` si no hay. Se lee en cada llamada, como los demás secretos."""
    crudo = os.getenv("PIDEUTB_VAPID_CLAVE_PRIVADA", "").strip()
    if not crudo:
        return None

    from cryptography.hazmat.primitives.asymmetric import ec

    # Mal pegada en el panel, se ignora y se registra, igual que la URL de la pasarela
    # simulada: el sitio deja de ofrecer el botón y lo demás sigue funcionando.
    #
    # El formato se comprueba antes de decodificar porque `urlsafe_b64decode` tira lo
    # que no entiende sin decir nada: la línea entera del `.env` pegada en el campo
    # del valor saldría convertida en otra clave, válida y que nadie generó.
    if not _FORMATO_DE_LA_CLAVE.fullmatch(crudo):
        _LOG.warning("clave_vapid_ignorada", extra={"motivo": "no son 32 bytes en base64url"})
        return None

    numero = int.from_bytes(base64.urlsafe_b64decode(crudo + "="), "big")
    return ec.derive_private_key(numero, ec.SECP256R1())


def clave_publica() -> str | None:
    """La clave pública en el formato que pide `pushManager.subscribe`."""
    privada = _clave_privada()
    if privada is None:
        return None

    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return _base64url(
        privada.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    )


def firmar(audiencia: str) -> str:
    """La cabecera `Authorization` de VAPID para un servicio de push."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils

    contacto = os.getenv("PIDEUTB_VAPID_CONTACTO", "").strip() or _CONTACTO_POR_DEFECTO
    cabecera = _base64url(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    cuerpo = _base64url(
        json.dumps(
            {"aud": audiencia, "exp": int(time.time()) + _SEGUNDOS_DE_VALIDEZ, "sub": contacto}
        ).encode()
    )
    a_firmar = f"{cabecera}.{cuerpo}"

    # ES256 en un JWT es `r` y `s` pegados, y la biblioteca los entrega en DER.
    firma_der = _clave_privada().sign(a_firmar.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(firma_der)
    firma = _base64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))

    return f"vapid t={a_firmar}.{firma}, k={clave_publica()}"


def _avisar(pedido_id: int) -> None:
    """Manda el aviso, una vez. Corre en otro hilo.

    `http.client` y no `urllib.request` porque este no sigue redirecciones: la
    lista de servicios conocidos no serviría de nada si uno pudiera mandarnos a
    otro sitio con un 302. Tampoco se registra la dirección: quien la tiene puede
    mandarle notificaciones a ese teléfono.
    """
    try:
        endpoint = pedidos_service.tomar_aviso_push(pedido_id)
        if endpoint is None:
            return

        # Lo que hay en la base entró validado, y se vuelve a mirar antes de
        # hacer una petición a una dirección que escribió un navegador.
        if not pedidos_service.es_servicio_de_push_conocido(endpoint):
            _LOG.warning("aviso_a_servicio_desconocido", extra={"pedido_id": pedido_id})
            return

        partes = urlsplit(endpoint)
        ruta = partes.path + (f"?{partes.query}" if partes.query else "")
        conexion = http.client.HTTPSConnection(partes.hostname, timeout=_SEGUNDOS_DE_ESPERA)
        try:
            conexion.request(
                "POST",
                ruta,
                headers={
                    "Authorization": firmar(f"https://{partes.hostname}"),
                    "TTL": str(_SEGUNDOS_DE_VIDA),
                    "Urgency": "high",
                    "Content-Length": "0",
                },
            )
            estado = conexion.getresponse().status
        finally:
            conexion.close()
    except Exception as error:  # noqa: BLE001 — el aviso no puede afectar al pedido
        _LOG.warning(
            "aviso_no_enviado",
            extra={"pedido_id": pedido_id, "motivo": type(error).__name__},
        )
        return

    if 200 <= estado < 300:
        _LOG.info("aviso_enviado", extra={"pedido_id": pedido_id})
    else:
        # 404 y 410 son una suscripción que ya no existe: la persona desinstaló o
        # revocó el permiso, y no hay nada que corregir.
        _LOG.warning("aviso_rechazado", extra={"pedido_id": pedido_id, "estado": estado})


def al_quedar_listo(mensaje: dict) -> None:
    """Suscriptor de `pedidos-listos`. Sin clave no hay avisos que mandar."""
    if os.getenv("PIDEUTB_VAPID_CLAVE_PRIVADA", "").strip():
        eventos.en_segundo_plano(_avisar, mensaje["pedido_id"])


def suscribir() -> None:
    eventos.suscribir(eventos.CANAL_PEDIDO_LISTO, al_quedar_listo)


@router.get(
    "/clave-publica",
    responses={404: {"model": ErrorDeNegocio}},
    summary="La clave con la que el navegador se suscribe a los avisos.",
)
def obtener_clave_publica() -> ClavePublicaResponse:
    """`404` si este despliegue no manda avisos: el sitio no ofrece el botón."""
    clave = clave_publica()
    if clave is None:
        raise HTTPException(status_code=404, detail="Este despliegue no manda avisos.")
    return ClavePublicaResponse(clave_publica=clave)
