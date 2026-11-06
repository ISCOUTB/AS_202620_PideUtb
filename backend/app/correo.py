"""Mandar un correo por SMTP. Solo el transporte: qué dice lo decide quien llama.

Usa la biblioteca estándar y no un paquete ni la API de un proveedor. SMTP lo
habla cualquier servicio de correo, así que cambiar de proveedor es cambiar cuatro
variables en el panel de despliegue, y la imagen no gana ninguna dependencia.

| Variable | Qué es |
|---|---|
| `PIDEUTB_SMTP_HOST` | El servidor. **Sin ella no se manda nada** |
| `PIDEUTB_SMTP_PUERTO` | 587 por defecto; con 465 se conecta ya cifrado |
| `PIDEUTB_SMTP_USUARIO` / `PIDEUTB_SMTP_CONTRASENA` | Las credenciales |
| `PIDEUTB_SMTP_REMITENTE` | Quién firma el correo. Por defecto, el usuario |

Se leen en cada envío, igual que el secreto de la pasarela: en el panel las
variables cambian sin que nadie reconstruya la imagen.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

#: Un servidor que no contesta no puede dejar un hilo colgado para siempre.
_SEGUNDOS_DE_ESPERA = 15


def configurado() -> bool:
    """Si hay un servidor al que mandar. Sin él, el comprobante no se intenta."""
    return bool(os.getenv("PIDEUTB_SMTP_HOST", "").strip())


def enviar(*, para: str, asunto: str, texto: str, html: str) -> None:
    """Manda un correo con su versión en texto y su versión en HTML.

    Lanza una excepción si no se puede. Quien llama decide qué significa eso.
    """
    host = os.getenv("PIDEUTB_SMTP_HOST", "").strip()
    puerto = int(os.getenv("PIDEUTB_SMTP_PUERTO", "587").strip() or "587")
    usuario = os.getenv("PIDEUTB_SMTP_USUARIO", "").strip()
    contrasena = os.getenv("PIDEUTB_SMTP_CONTRASENA", "")

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = os.getenv("PIDEUTB_SMTP_REMITENTE", "").strip() or usuario
    mensaje["To"] = para
    mensaje.set_content(texto)
    mensaje.add_alternative(html, subtype="html")

    contexto = ssl.create_default_context()

    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, timeout=_SEGUNDOS_DE_ESPERA, context=contexto) as servidor:
            if usuario:
                servidor.login(usuario, contrasena)
            servidor.send_message(mensaje)
        return

    with smtplib.SMTP(host, puerto, timeout=_SEGUNDOS_DE_ESPERA) as servidor:
        servidor.ehlo()
        if servidor.has_extn("starttls"):
            servidor.starttls(context=contexto)
            servidor.ehlo()
        elif usuario:
            # Un servidor que no ofrece cifrado puede ser alguien en medio que
            # le quitó esa opción. Las credenciales no salen en claro por eso.
            raise smtplib.SMTPNotSupportedError("El servidor no ofrece STARTTLS.")

        if usuario:
            servidor.login(usuario, contrasena)
        servidor.send_message(mensaje)
