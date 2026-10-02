"""Sin secreto configurado, el webhook rechaza todo.

Cubre [V-11](../../docs/violaciones.md): hasta la semana 9,
`app/pagos/service.py` traía un secreto por defecto —`"secreto-de-desarrollo"`—
para que el repositorio fuera ejecutable sin credenciales. El despliegue nunca
definió la variable real, así que la API en producción verificaba las firmas
contra una cadena **publicada en un repositorio público**.

El efecto no era teórico: cualquiera que leyera el repositorio podía firmar un
aviso de pago válido y obtener un código de canje sin pagar. La primera prueba
de este archivo reproduce ese ataque y comprueba que ya no funciona.

La decisión fue **fallar en cerrado**. Un sistema sin su secreto deja de
aceptar confirmaciones de pago: molesto y visible. Con un secreto público
aceptaba pagos falsos: peor y silencioso.
"""
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pagos import service

client = TestClient(app)

#: El secreto que estuvo publicado en el repositorio hasta la semana 9.
SECRETO_FILTRADO = "secreto-de-desarrollo"


def _evento_firmado_con(secreto: str, referencia: str) -> tuple[bytes, str]:
    cuerpo = json.dumps(
        {
            "evento": "transaccion.actualizada",
            "referencia_pago": referencia,
            "estado_pago": "aprobado",
        }
    ).encode()
    firma = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return cuerpo, firma


def _crear_pedido_con_intento() -> str:
    pedido_id = client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1}).json()["pedido_id"]
    intento = client.post(
        "/v1/pagos/intentos", json={"pedido_id": pedido_id, "metodo": "nequi"}
    ).json()
    return intento["referencia_pago"]


def test_el_secreto_que_estuvo_publicado_ya_no_sirve(monkeypatch):
    """Reproduce el ataque que V-11 hacía posible.

    Con el secreto real configurado, un evento firmado con el que estuvo
    publicado en el repositorio tiene que rechazarse.
    """
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", "el-secreto-real-de-produccion")
    referencia = _crear_pedido_con_intento()
    cuerpo, firma = _evento_firmado_con(SECRETO_FILTRADO, referencia)

    respuesta = client.post(
        "/v1/pagos/eventos",
        content=cuerpo,
        headers={"Content-Type": "application/json", "X-Firma-Evento": firma},
    )

    assert respuesta.status_code == 401


def test_sin_secreto_configurado_se_rechaza_cualquier_evento(monkeypatch):
    """Fallar en cerrado: sin secreto, ninguna firma puede ser válida.

    La alternativa —aceptar los eventos— convertiría un error de configuración
    en una vía para cobrar sin pagar, que es justo lo que ocurrió.
    """
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", "")
    cuerpo, firma = _evento_firmado_con(SECRETO_FILTRADO, "cualquier-referencia")

    assert service.firma_valida(cuerpo, firma) is False
    # Y tampoco vale mandar una firma vacía o ausente.
    assert service.firma_valida(cuerpo, "") is False
    assert service.firma_valida(cuerpo, None) is False


def test_firmar_se_niega_en_vez_de_usar_una_cadena_vacia(monkeypatch):
    """Firmar sin secreto produciría una firma válida contra `""`.

    Si `firmar` cayera a la cadena vacía, emisor y verificador coincidirían y
    **toda** firma sería válida: el fallo abierto más silencioso posible.
    """
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", "   ")

    with pytest.raises(service.SecretoNoConfiguradoError):
        service.firmar(b"{}")


def test_con_el_secreto_correcto_el_evento_se_acepta(monkeypatch):
    """El camino legítimo sigue funcionando: esto no es un rechazo de todo."""
    secreto = "el-secreto-real-de-produccion"
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", secreto)
    referencia = _crear_pedido_con_intento()
    cuerpo, firma = _evento_firmado_con(secreto, referencia)

    respuesta = client.post(
        "/v1/pagos/eventos",
        content=cuerpo,
        headers={"Content-Type": "application/json", "X-Firma-Evento": firma},
    )

    assert respuesta.status_code == 202
    assert respuesta.json()["estado"] == "pagado"


def test_el_secreto_no_aparece_en_el_codigo_fuente():
    """Nada en `app/` puede volver a traer un secreto escrito.

    Es la prueba que habría evitado V-11 desde el principio: no comprueba el
    comportamiento sino la ausencia de la causa.
    """
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[1] / "app"
    culpables = [
        archivo.relative_to(app_dir.parent)
        for archivo in app_dir.rglob("*.py")
        if SECRETO_FILTRADO in archivo.read_text(encoding="utf-8")
        and "V-11" not in archivo.read_text(encoding="utf-8")
    ]

    assert not culpables, (
        "Hay un secreto escrito en el código:\n"
        + "\n".join(f"  - {c}" for c in culpables)
    )
