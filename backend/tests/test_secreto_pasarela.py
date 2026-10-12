"""Sin secreto configurado, el webhook rechaza todo.

Cubre [V-11](../../docs/violaciones.md): hasta la semana 9,
`app/pagos/service.py` traía un secreto **por defecto** para que el repositorio
fuera ejecutable sin credenciales. El despliegue nunca definió la variable real,
así que la API en producción verificaba las firmas contra una cadena publicada
en un repositorio público.

El efecto no era teórico: cualquiera que leyera el repositorio podía firmar un
aviso de pago válido y obtener un código de canje sin pagar. La primera prueba
de este archivo reproduce ese ataque y comprueba que ya no funciona.

La decisión fue **fallar en cerrado**. Un sistema sin su secreto deja de
aceptar confirmaciones de pago: molesto y visible. Con un secreto público
aceptaba pagos falsos: peor y silencioso.

### Por qué el valor histórico no aparece escrito en ninguna parte

Está en el historial de git y no se puede borrar de ahí; eso no es excusa para
seguir repitiéndolo en el código vigente, donde cualquiera que haga `grep` lo
encuentra en cinco sitios distintos sin tener que saber buscar.

Y para probar lo que hay que probar no hace falta nombrarlo. La regresión que
este archivo vigila no es «*ese* valor dejó de servir», es «**no hay** valor por
defecto»: el código no cae en ninguna cadena cuando la variable falta. Probarlo
con un secreto cualquiera distinto del configurado cubre el caso histórico y
además todos los demás, así que la prueba se hizo más fuerte al quitar el
literal, no más débil.
"""
import hashlib
import hmac
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pagos import service

client = TestClient(app)

#: Un secreto cualquiera que **no** es el configurado.
#:
#: Ocupa el lugar del que estuvo publicado hasta la semana 9, y vale igual: lo
#: que se comprueba es que una firma hecha con algo distinto de lo configurado
#: se rechaza, sea ese algo el valor histórico o cualquier otro.
SECRETO_AJENO = "un-secreto-que-no-es-el-configurado"


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


def test_una_firma_hecha_con_otro_secreto_no_sirve(monkeypatch):
    """Reproduce el ataque que V-11 hacía posible.

    Con el secreto real configurado, un evento firmado con cualquier otra cadena
    —entre ellas la que estuvo publicada en el repositorio— tiene que
    rechazarse. Ese «cualquier otra» es lo que hace la prueba más fuerte que
    comprobar un valor concreto: no queda especializada en el defecto de una
    semana.
    """
    monkeypatch.setenv("PIDEUTB_SECRETO_PASARELA", "el-secreto-real-de-produccion")
    referencia = _crear_pedido_con_intento()
    cuerpo, firma = _evento_firmado_con(SECRETO_AJENO, referencia)

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
    cuerpo, firma = _evento_firmado_con(SECRETO_AJENO, "cualquier-referencia")

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
        if SECRETO_AJENO in archivo.read_text(encoding="utf-8")
        and "V-11" not in archivo.read_text(encoding="utf-8")
    ]

    assert not culpables, (
        "Hay un secreto escrito en el código:\n"
        + "\n".join(f"  - {c}" for c in culpables)
    )


# --------------------------------------------------------------------------
# El guardia: que no vuelva a entrar por donde entró
# --------------------------------------------------------------------------

#: Nombres de variable que, si llevan valor por defecto, lo que llevan es una
#: credencial escrita en el código.
PALABRAS_DE_SECRETO = ("SECRETO", "CLAVE", "TOKEN", "PASSWORD", "DATABASE_URL")

#: `os.getenv("ALGO", "no vacío")` o `os.environ.get("ALGO", "no vacío")`.
#:
#: Solo se persigue el valor por defecto **no vacío**: `os.getenv("X", "")` es
#: precisamente la forma correcta, porque la cadena vacía no verifica ninguna
#: firma ni abre ninguna conexión. Lo que rompe es un valor que *parece*
#: funcionar.
LECTURA_CON_DEFECTO = re.compile(
    r"""os\.(?:getenv|environ\.get)\(\s*["']([A-Z0-9_]+)["']\s*,\s*["']([^"']+)["']""",
)


def credenciales_con_defecto(lineas: list[str], origen: str) -> list[str]:
    """Las líneas de `lineas` que escriben una credencial en el código.

    Está extraído como función y no embebido en la prueba para que el detector
    se pueda alimentar con líneas inventadas. Un detector al que solo se le dan
    archivos que están bien nunca demuestra que detecte algo: pasa igual si
    funciona y si está roto.
    """
    encontrados: list[str] = []

    for numero, linea in enumerate(lineas, start=1):
        for variable, defecto in LECTURA_CON_DEFECTO.findall(linea):
            if any(p in variable for p in PALABRAS_DE_SECRETO):
                encontrados.append(
                    f"{origen}:{numero} — {variable} tiene valor por "
                    f"defecto de {len(defecto)} caracteres"
                )

    return encontrados


def test_el_guardia_de_secretos_detecta_lo_que_dice_detectar():
    """Lo que vuelve útil a la prueba de abajo: que se sabe que falla cuando debe.

    Los tres primeros casos son la forma exacta de V-11 con nombres distintos.
    Los dos últimos son lo que **no** debe marcar: la cadena vacía, que es la
    forma correcta de fallar en cerrado, y una variable que no es un secreto
    aunque tenga valor por defecto.
    """
    delatan = [
        'X = os.getenv("PIDEUTB_SECRETO_PASARELA", "cualquier-cosa")',
        'X = os.environ.get("PIDEUTB_DATABASE_URL", "postgres://u:p@h/d")',
        'X = os.getenv("ALGUN_TOKEN_DE_API", "abc123")',
    ]
    for caso in delatan:
        assert credenciales_con_defecto([caso], "inventado"), (
            f"El guardia no marcó una credencial escrita en el código: {caso}"
        )

    inocentes = [
        'X = os.getenv("PIDEUTB_SECRETO_PASARELA", "")',
        'X = os.getenv("PIDEUTB_ORIGENES_PERMITIDOS", "http://localhost:8080")',
    ]
    for caso in inocentes:
        assert not credenciales_con_defecto([caso], "inventado"), (
            f"El guardia marcó algo que no es un secreto: {caso}"
        )


def test_ningun_secreto_vuelve_a_tener_valor_por_defecto():
    """V-11 no se corrige una vez: se corrige y se vigila.

    La corrección de la semana 9 quitó **un** valor por defecto. Nada impedía
    que el siguiente volviera a entrar, y por el mismo motivo razonable que
    entró el primero: que el repositorio arranque sin configurar nada. Esta
    prueba convierte esa comodidad en una decisión que hay que defender en una
    revisión, en lugar de una que se cuela en un commit de dos líneas.

    No busca el valor histórico —ese ya no está escrito en ninguna parte— sino
    **la forma** del defecto. Buscar el valor solo habría protegido contra
    repetir exactamente aquel error; buscar la forma protege contra el error.
    """
    raiz = Path(__file__).resolve().parents[1] / "app"
    encontrados: list[str] = []

    for archivo in sorted(raiz.rglob("*.py")):
        encontrados += credenciales_con_defecto(
            archivo.read_text(encoding="utf-8").splitlines(),
            archivo.relative_to(raiz.parents[1]).as_posix(),
        )

    assert not encontrados, (
        "Una variable de entorno con pinta de credencial lleva valor por "
        "defecto en el código:\n\n"
        + "\n".join(f"  - {e}" for e in encontrados)
        + "\n\nEs la forma exacta de V-11 (docs/violaciones.md). Usá "
        "`os.getenv(\"NOMBRE\", \"\")` y fallá en cerrado: un sistema sin su "
        "secreto que deja de funcionar es molesto y visible; uno que funciona "
        "con un secreto público acepta lo que no debe, y en silencio.\n\n"
        "El mensaje no imprime el valor encontrado, solo su longitud: una "
        "prueba que filtra el secreto en el log del pipeline lo publica otra "
        "vez, y los logs de las construcciones son legibles para cualquiera "
        "que tenga acceso al repositorio."
    )
