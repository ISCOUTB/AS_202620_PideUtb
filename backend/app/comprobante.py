"""El correo que recibe el cliente cuando se confirma su pago.

Escucha `pedidos-pagados` en vez de llamarse desde el cobro. Un correo que no sale
no puede bloquear ni cancelar un pedido, y es justo la garantía que da el bus
(`app/eventos.py`): quien publica no conoce a quien escucha, y un suscriptor que
falla no afecta a nadie. El envío va además en otro hilo, para que un servidor de
correo lento no le gane al plazo con el que la pasarela espera nuestro `2xx`.

**No se reintenta y no hay cola**, y es una decisión (ADR-0012): el comprobante es
un respaldo. Si no sale, el código sigue en la pantalla de quien pagó.

### Por qué «comprobante» y no «factura electrónica»

Se parece a una a propósito, pero una factura electrónica de venta en Colombia es
un documento que valida la DIAN, y llamar así a este sería afirmar algo falso en
un papel de dinero. Por eso el título es otro, el consecutivo es propio y el pie
lo dice.

### Las reglas del HTML

Un cliente de correo no es un navegador: Gmail y Outlook descartan hojas de
estilo y buena parte del CSS moderno. De ahí las tablas, los estilos en cada
etiqueta y el `bgcolor` repetido. **Todo lo que escribió alguien pasa por
`escape`**: el nombre lo teclea el cliente, y sin escapar podría meter HTML en el
comprobante.
"""
from __future__ import annotations

import logging
from html import escape
from zoneinfo import ZoneInfo

from app import correo, eventos
from app.pagos import service as pagos_service
from app.pagos.contracts import MetodoDePago
from app.pedidos import service as pedidos_service
from app.pedidos.contracts import ComprobanteDePedido
from app.usuarios import service as cuentas_service
from app.usuarios.contracts import EstablecimientoPublico

_LOG = logging.getLogger("pideutb")

_ZONA = ZoneInfo("America/Bogota")

_NOMBRE_DEL_METODO = {
    MetodoDePago.TARJETA: "Tarjeta",
    MetodoDePago.NEQUI: "Nequi",
    MetodoDePago.PSE: "PSE",
}

#: Los colores del sitio. Se repiten porque aquí no llega ninguna hoja de estilos.
_AZUL = "#093AD8"
_CODIGO_FONDO = "#0A1F5C"
_CODIGO_TINTA = "#FFD166"
_TINTA = "#1C1917"
_TINTA_TENUE = "#6E6660"
_LINEA = "#E9DED0"
_CREMA = "#FBF6EF"

_FUENTE = "Arial, Helvetica, sans-serif"

_AVISO_LEGAL = (
    "Este comprobante es un respaldo de tu pedido y no reemplaza una factura "
    "electrónica de venta ante la DIAN."
)
#: Lo mismo que dice el pie del sitio. Mientras se cobre en ambiente de pruebas,
#: un papel que dice «Total pagado» tiene que decirlo también.
_AVISO_DE_PRUEBAS = (
    "Los pagos usan la pasarela en ambiente de pruebas. No se cobra dinero real."
)


def _pesos(centavos: int) -> str:
    """400000 → `$4.000`. Sin depender del idioma instalado en el contenedor."""
    return "$" + f"{centavos // 100:,}".replace(",", ".")


def _numero(datos: ComprobanteDePedido) -> str:
    return f"PU-{datos.numero_comprobante:06d}"


def redactar(
    datos: ComprobanteDePedido,
    establecimiento: EstablecimientoPublico | None,
    metodo: MetodoDePago | None,
) -> tuple[str, str, str]:
    """Devuelve `(asunto, texto, html)`. No envía nada, para poder probarlo."""
    negocio = establecimiento.nombre if establecimiento else "PideUTB"
    ubicacion = establecimiento.ubicacion if establecimiento else ""
    nombre_metodo = _NOMBRE_DEL_METODO.get(metodo, "No disponible")
    fecha = datos.pagado_en.astimezone(_ZONA).strftime("%d/%m/%Y %H:%M")
    recogida = (
        datos.hora_recogida.astimezone(_ZONA).strftime("%H:%M")
        if datos.hora_recogida is not None
        else None
    )
    cliente = datos.nombre_cliente or "Cliente"

    asunto = f"Comprobante de tu pedido #{datos.pedido_id} en {negocio}"
    texto = _en_texto(datos, negocio, ubicacion, nombre_metodo, fecha, recogida, cliente)
    html = _en_html(datos, negocio, ubicacion, nombre_metodo, fecha, recogida, cliente)
    return asunto, texto, html


def _en_texto(datos, negocio, ubicacion, metodo, fecha, recogida, cliente) -> str:
    """La versión para quien no ve HTML, y lo que leen los filtros de spam."""
    lineas = [
        f"PideUTB · {negocio}",
        ubicacion,
        "",
        "COMPROBANTE DE PAGO",
        f"Código para recoger: {datos.codigo_canje}",
        "",
        f"Comprobante: {_numero(datos)}",
        f"Fecha y hora: {fecha}",
        f"Pedido: #{datos.pedido_id}",
        f"Cliente: {cliente}",
        f"Correo: {datos.correo_cliente}",
    ]
    if recogida:
        lineas.append(f"Hora de recogida: {recogida}")
    lineas.append("")
    for linea in datos.lineas:
        lineas.append(
            f"{linea.cantidad} x {linea.nombre_item} "
            f"({_pesos(linea.precio_unitario_centavos)} c/u): "
            f"{_pesos(linea.total_linea_centavos)}"
        )
    lineas += [
        "",
        f"Total pagado: {_pesos(datos.total_centavos)}",
        f"Método de pago: {metodo}",
        "",
        _AVISO_LEGAL,
        _AVISO_DE_PRUEBAS,
    ]
    return "\n".join(lineas)


def _dato(rotulo: str, valor: str) -> str:
    """Una fila de rótulo y valor."""
    return (
        "<tr>"
        f'<td style="padding:4px 0;font-family:{_FUENTE};font-size:14px;'
        f'color:{_TINTA_TENUE};">{escape(rotulo)}</td>'
        f'<td align="right" style="padding:4px 0;font-family:{_FUENTE};font-size:14px;'
        f'color:{_TINTA};font-weight:bold;">{escape(valor)}</td>'
        "</tr>"
    )


def _celda(contenido: str, *, alinear: str = "left", cabecera: bool = False) -> str:
    color = _TINTA_TENUE if cabecera else _TINTA
    tamano = "12px" if cabecera else "14px"
    borde = f"border-bottom:1px solid {_LINEA};"
    return (
        f'<td align="{alinear}" style="padding:8px 4px;font-family:{_FUENTE};'
        f'font-size:{tamano};color:{color};{borde}">{contenido}</td>'
    )


def _en_html(datos, negocio, ubicacion, metodo, fecha, recogida, cliente) -> str:
    filas = "".join(
        "<tr>"
        + _celda(str(linea.cantidad), alinear="center")
        + _celda(escape(linea.nombre_item))
        + _celda(_pesos(linea.precio_unitario_centavos), alinear="right")
        + _celda(_pesos(linea.total_linea_centavos), alinear="right")
        + "</tr>"
        for linea in datos.lineas
    )

    datos_del_pago = [
        _dato("Comprobante", _numero(datos)),
        _dato("Fecha y hora", fecha),
        _dato("Pedido", f"#{datos.pedido_id}"),
    ]
    if recogida:
        datos_del_pago.append(_dato("Hora de recogida", recogida))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Comprobante de pago</title>
</head>
<body style="margin:0;padding:0;background-color:{_CREMA};">
<div style="display:none;max-height:0;overflow:hidden;">Tu código para recoger es {escape(datos.codigo_canje)}.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{_CREMA}" style="background-color:{_CREMA};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#FFFFFF" style="width:100%;max-width:600px;background-color:#FFFFFF;border:1px solid {_LINEA};">

<tr><td bgcolor="{_AZUL}" style="background-color:{_AZUL};padding:20px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="font-family:Georgia,'Times New Roman',serif;font-size:26px;color:#FFFFFF;">PideUTB</td>
<td align="right" style="font-family:{_FUENTE};font-size:12px;letter-spacing:1px;color:#FFFFFF;">COMPROBANTE DE PAGO</td>
</tr></table>
</td></tr>

<tr><td style="padding:20px 24px 0;font-family:{_FUENTE};font-size:14px;color:{_TINTA};">
<strong>{escape(negocio)}</strong><br>
<span style="color:{_TINTA_TENUE};">{escape(ubicacion)}</span>
</td></tr>

<tr><td style="padding:20px 24px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{_CODIGO_FONDO}" style="background-color:{_CODIGO_FONDO};">
<tr><td align="center" style="padding:16px 12px 4px;font-family:{_FUENTE};font-size:12px;letter-spacing:1px;color:#FFFFFF;">TU CÓDIGO PARA RECOGER</td></tr>
<tr><td align="center" style="padding:0 12px 16px;font-family:Georgia,'Times New Roman',serif;font-size:36px;letter-spacing:6px;color:{_CODIGO_TINTA};">{escape(datos.codigo_canje)}</td></tr>
</table>
</td></tr>

<tr><td style="padding:20px 24px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{"".join(datos_del_pago)}</table>
</td></tr>

<tr><td style="padding:20px 24px 0;">
<div style="font-family:{_FUENTE};font-size:12px;letter-spacing:1px;color:{_TINTA_TENUE};padding-bottom:4px;">DATOS DEL CLIENTE</div>
<div style="font-family:{_FUENTE};font-size:14px;color:{_TINTA};">{escape(cliente)}<br>{escape(datos.correo_cliente)}</div>
</td></tr>

<tr><td style="padding:20px 24px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>{_celda("Cant.", alinear="center", cabecera=True)}{_celda("Producto", cabecera=True)}{_celda("Precio unit.", alinear="right", cabecera=True)}{_celda("Subtotal", alinear="right", cabecera=True)}</tr>
{filas}
</table>
</td></tr>

<tr><td style="padding:16px 24px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="font-family:{_FUENTE};font-size:16px;font-weight:bold;color:{_TINTA};">Total pagado</td>
<td align="right" style="font-family:{_FUENTE};font-size:20px;font-weight:bold;color:{_TINTA};">{_pesos(datos.total_centavos)}</td>
</tr>
{_dato("Método de pago", metodo)}
</table>
</td></tr>

<tr><td style="padding:20px 24px 24px;font-family:{_FUENTE};font-size:12px;line-height:18px;color:{_TINTA_TENUE};">
{escape(_AVISO_LEGAL)}<br>{escape(_AVISO_DE_PRUEBAS)}
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _enviar(pedido_id: int) -> None:
    """Redacta y manda el comprobante. Corre en otro hilo.

    Un fallo se registra con el pedido y el tipo de error, **sin el mensaje**: el
    de `smtplib` puede traer la dirección del cliente, y no tiene por qué acabar
    en los registros.
    """
    try:
        datos = pedidos_service.datos_del_comprobante(pedido_id)
        if datos is None:
            return

        asunto, texto, html = redactar(
            datos,
            cuentas_service.obtener_establecimiento(datos.establecimiento_id),
            pagos_service.metodo_del_pedido(pedido_id),
        )
        correo.enviar(para=datos.correo_cliente, asunto=asunto, texto=texto, html=html)
    except Exception as error:  # noqa: BLE001 — el correo no puede afectar al pedido
        _LOG.warning(
            "comprobante_no_enviado",
            extra={"pedido_id": pedido_id, "motivo": type(error).__name__},
        )
        return

    _LOG.info("comprobante_enviado", extra={"pedido_id": pedido_id})


def al_confirmarse_el_pago(mensaje: dict) -> None:
    """Suscriptor de `pedidos-pagados`. No hace nada si no hay servidor de correo."""
    if correo.configurado():
        eventos.en_segundo_plano(_enviar, mensaje["pedido_id"])


def suscribir() -> None:
    eventos.suscribir(eventos.CANAL_PEDIDO_PAGADO, al_confirmarse_el_pago)
