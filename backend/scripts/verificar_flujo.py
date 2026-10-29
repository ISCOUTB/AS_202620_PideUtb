"""Recorre la cadena entera y dice en qué eslabón se rompe.

    python scripts/verificar_flujo.py                       # contra local
    python scripts/verificar_flujo.py https://api-pideutb.iscoutb.dev

Carta → pedido → intento de pago → pasarela → pago aprobado → código de
recogida → el pedido pagado en la cola del mostrador, con su código.

### Por qué existe, si ya hay 455 pruebas

Porque ninguna de ellas recorre *el despliegue*. Las pruebas montan la
aplicación en memoria y comprueban que cada pieza cumple su contrato; lo que
falló esta semana no fue ninguna pieza, fue **cómo estaban conectadas en el
servidor**: el sitio creaba pedidos en el establecimiento 5 y la cuenta del
mostrador vivía en el 1. Las dos mitades pasaban sus pruebas. La cola no se
movía.

Este guion solo habla HTTP contra una URL. No importa qué haya detrás —local,
laboratorio, o un contenedor recién desplegado—, y por eso ve lo que las
pruebas no pueden ver: la configuración.

### Por qué pasa por el simulador y no firma el evento

La confirmación de pago de verdad llega firmada con `PIDEUTB_SECRETO_PASARELA`,
y ese secreto no está acá ni debería. `POST /v1/pagos/simulador/{ref}` es el
doble de la pasarela: no pide firma y **solo existe donde
`PIDEUTB_URL_PASARELA_SIMULADA` esté definida**, así que este guion comprueba
de paso que el camino de la demo está en pie. Si esa ruta responde 404, lo dice
con todas las letras en vez de fallar en el paso siguiente.

### Qué deja detrás

Un pedido pagado y entregado. Es a propósito: comprobar que el pago funciona
sin pagar nada no comprueba nada. Para borrarlo está
`POST /v1/demo/reiniciar`, o el propio `--limpiar`.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

# La consola de Windows arranca en cp1252, donde «→» no existe: sin esto el
# guion se cae con `UnicodeEncodeError` a mitad del paso 5, después de haber
# creado un pedido de verdad. Un verificador que rompe más tarde que lo que
# verifica no sirve de nada, y este se va a correr desde Windows el día de la
# charla.
#
# `errors="replace"` y no "strict": si alguna consola rarísima tampoco acepta
# UTF-8, preferimos un carácter feo a perder el informe entero.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_POR_DEFECTO = "http://127.0.0.1:8000"
ESTABLECIMIENTO = int(os.getenv("PIDEUTB_ESTABLECIMIENTO_DEMO", "5"))

# Las credenciales del mostrador son opcionales: sin ellas se recorre el lado
# del cliente, que es el que la charla enseña, y se avisa de lo que quedó sin
# comprobar. Pedirlas siempre volvería inútil el guion contra producción, que
# es justo donde más falta hace.
#: Cloudflare devuelve 403 a `Python-urllib/3.x` antes de que la petición
#: llegue al servidor, así que sin esto el guion no puede verificar producción
#: —que es justo para lo que se escribió—. Cualquier agente que no sea el de
#: urllib pasa; este dice la verdad sobre quién llama.
AGENTE = "pideutb-verificador/1.0"

CORREO = os.getenv("PIDEUTB_MOSTRADOR_CORREO", "")
CONTRASENA = os.getenv("PIDEUTB_MOSTRADOR_CONTRASENA", "")

_VERDE, _ROJO, _GRIS, _FIN = "\033[32m", "\033[31m", "\033[90m", "\033[0m"


class Fallo(Exception):
    """Un eslabón que no respondió lo que el siguiente necesita."""


def _pedir(
    base: str,
    metodo: str,
    ruta: str,
    cuerpo: dict | None = None,
    cabeceras: dict | None = None,
) -> tuple[int, dict]:
    """Una petición, y el cuerpo ya interpretado.

    Devuelve el código en vez de lanzar: varios pasos de este guion esperan un
    404 o un 401 como respuesta correcta, y tratarlos como excepción obligaría
    a envolver cada llamada en un `try`.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"{base}{ruta}",
        data=datos,
        method=metodo,
        headers={
            "Content-Type": "application/json",
            "User-Agent": AGENTE,
            **(cabeceras or {}),
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            crudo = respuesta.read().decode()
            return respuesta.status, (json.loads(crudo) if crudo else {})
    except urllib.error.HTTPError as error:
        crudo = error.read().decode()
        try:
            return error.code, json.loads(crudo) if crudo else {}
        except json.JSONDecodeError:
            return error.code, {"detail": crudo[:200]}


def _paso(numero: int, titulo: str) -> None:
    print(f"{_GRIS}{numero:2}{_FIN} {titulo} ... ", end="", flush=True)


def _ok(detalle: str = "") -> None:
    print(f"{_VERDE}ok{_FIN} {_GRIS}{detalle}{_FIN}")


def _pesos(centavos: int) -> str:
    return f"$ {centavos // 100:,}".replace(",", ".")


def verificar(base: str, limpiar: bool = False) -> int:
    arranque = time.monotonic()

    # ---------------------------------------------------------------- salud
    _paso(1, "La API responde")
    codigo, salud = _pedir(base, "GET", "/health")
    if codigo != 200:
        raise Fallo(f"/health respondió {codigo}. No hay nada más que mirar.")
    degradadas = [
        nombre
        for nombre, estado in salud.get("dependencias", {}).items()
        if estado.get("estado") != "ok"
    ]
    if degradadas:
        raise Fallo(f"dependencias caídas: {', '.join(degradadas)}")
    _ok(" · ".join(
        f"{n} {e['latencia_ms']} ms" for n, e in salud["dependencias"].items()
    ))

    # ---------------------------------------------------------------- carta
    _paso(2, f"La carta del establecimiento {ESTABLECIMIENTO} tiene productos")
    codigo, carta = _pedir(
        base, "GET", f"/v1/menu/establecimientos/{ESTABLECIMIENTO}/items"
    )
    if codigo != 200:
        raise Fallo(f"la carta respondió {codigo}")
    items = [i for i in carta.get("items", []) if i.get("disponible")]
    if not items:
        # El fallo silencioso que más caro sale: 200 con lista vacía es una
        # respuesta legítima del contrato, y la portada dice «todavía no cargó
        # su carta» sin que nada se registre.
        raise Fallo(
            f"el establecimiento {ESTABLECIMIENTO} respondió 200 con la lista "
            "vacía. Existe y no tiene productos disponibles: la portada se "
            "vería vacía sin que nada fallara."
        )
    _ok(f"{len(items)} disponibles de {len(carta['items'])}")

    # --------------------------------------------------------------- pedido
    _paso(3, "Se crea un pedido")
    lineas = [{"item_id": items[0]["item_id"], "cantidad": 2}]
    if len(items) > 1:
        lineas.append({"item_id": items[1]["item_id"], "cantidad": 1})
    codigo, pedido = _pedir(base, "POST", "/v1/pedidos", {"lineas": lineas})
    if codigo != 201:
        raise Fallo(f"crear el pedido respondió {codigo}: {pedido}")

    pedido_id = pedido["pedido_id"]
    token = pedido.get("token_consulta")
    if not token:
        raise Fallo(
            "el pedido se creó sin `token_consulta`. Sin él el cliente no "
            "puede consultar su propio pedido (contrato 4.0.0)."
        )
    if pedido["establecimiento_id"] != ESTABLECIMIENTO:
        raise Fallo(
            f"el pedido quedó en el establecimiento {pedido['establecimiento_id']}"
            f" y se pidió al {ESTABLECIMIENTO}"
        )
    _ok(f"#{pedido_id} · {_pesos(pedido['total_centavos'])} · {pedido['estado']}")

    # ------------------------------------------------- el token es necesario
    _paso(4, "Sin el token, el pedido no se deja leer")
    codigo, _ = _pedir(base, "GET", f"/v1/pedidos/{pedido_id}")
    if codigo == 200:
        raise Fallo(
            "`GET /v1/pedidos/{id}` devolvió el pedido sin token. Es V-13: los "
            "identificadores son secuenciales, así que los códigos de canje se "
            "pueden cosechar recorriéndolos. ¿Esta API es anterior a la 4.0.0?"
        )
    _ok(f"{codigo} como debe")

    # --------------------------------------------------------------- intento
    _paso(5, "Se abre el cobro")
    codigo, intento = _pedir(
        base, "POST", "/v1/pagos/intentos",
        {"pedido_id": pedido_id, "metodo": "tarjeta"},
    )
    if codigo != 201:
        raise Fallo(f"abrir el cobro respondió {codigo}: {intento}")
    referencia = intento["referencia_pago"]
    checkout = intento["url_checkout"]
    _ok(f"{referencia} → {checkout[:60]}")

    # ------------------------------------------------------------- pasarela
    _paso(6, "La pasarela simulada está en pie")
    codigo, acuse = _pedir(
        base, "POST", f"/v1/pagos/simulador/{referencia}",
        {"estado_pago": "aprobado"},
    )
    if codigo == 404:
        raise Fallo(
            "`/v1/pagos/simulador/{ref}` responde 404, así que "
            "`PIDEUTB_URL_PASARELA_SIMULADA` no está puesta (o no es una URL "
            "absoluta y se ignora). Sin ella el público tendría que pagar con "
            "una tarjeta de verdad: la demo no se puede dar así."
        )
    if codigo != 202:
        raise Fallo(f"el simulador respondió {codigo}: {acuse}")
    _ok(f"aceptado · pedido {acuse.get('estado')}")

    # ---------------------------------------------------------------- código
    _paso(7, "El cliente ve su código de recogida")
    codigo, visto = _pedir(
        base, "GET", f"/v1/pedidos/{pedido_id}", cabeceras={"X-Token-Pedido": token}
    )
    if codigo != 200:
        raise Fallo(f"consultar con el token respondió {codigo}: {visto}")
    if visto["estado"] != "pagado":
        raise Fallo(
            f"el pedido quedó en `{visto['estado']}` después de aprobar el "
            "pago. La confirmación es asíncrona (ADR-0003), pero el simulador "
            "la aplica antes de responder: esto no es una carrera."
        )
    canje = visto.get("codigo_canje")
    if not canje:
        raise Fallo("el pedido está pagado y no trae `codigo_canje`")
    _ok(f"{canje} · {visto['estado']}")

    segundos_cliente = time.monotonic() - arranque

    # ------------------------------------------------------------ mostrador
    if not (CORREO and CONTRASENA):
        print(
            f"\n{_GRIS}   Sin PIDEUTB_MOSTRADOR_CORREO y "
            f"PIDEUTB_MOSTRADOR_CONTRASENA no se comprueba la cola del "
            f"mostrador,{_FIN}"
            f"\n{_GRIS}   que es justo donde estaba el bug. "
            f"Vale la pena ponerlas.{_FIN}"
        )
    else:
        _paso(8, "El mostrador entra")
        codigo, sesion = _pedir(
            base, "POST", "/v1/sesiones",
            {"correo": CORREO, "contrasena": CONTRASENA},
        )
        if codigo != 201:
            raise Fallo(f"iniciar sesión respondió {codigo}: {sesion}")
        auth = {"Authorization": f"Bearer {sesion['token']}"}
        suyo = sesion.get("usuario", {}).get("establecimiento_id")
        if suyo != ESTABLECIMIENTO:
            raise Fallo(
                f"la cuenta del mostrador opera sobre el establecimiento "
                f"{suyo} y los pedidos entran al {ESTABLECIMIENTO}. Es el bug "
                "que arregló la migración 008: la cola se refresca sola cada "
                "cinco segundos y no puede cambiar nunca."
            )
        _ok(f"establecimiento {suyo}")

        _paso(9, "El pedido pagado aparece en la cola, con su código")
        codigo, cola = _pedir(base, "GET", "/v1/pedidos", cabeceras=auth)
        if codigo != 200:
            raise Fallo(f"la cola respondió {codigo}: {cola}")
        encontrado = next(
            (p for p in cola.get("pedidos", []) if p["pedido_id"] == pedido_id), None
        )
        if encontrado is None:
            raise Fallo(
                f"el pedido #{pedido_id} no está en la cola del mostrador. "
                f"La cola trae {len(cola.get('pedidos', []))} pedidos."
            )
        if encontrado.get("codigo_canje") != canje:
            raise Fallo(
                "el mostrador no ve el mismo código que el cliente: "
                f"{encontrado.get('codigo_canje')} contra {canje}"
            )
        _ok(f"#{pedido_id} · {encontrado['estado']} · {canje}")

        _paso(10, "El pedido avanza hasta entregado")
        for estado, extra in (
            ("en_preparacion", {}),
            ("listo_para_recoger", {}),
            ("entregado", {"codigo_canje": canje}),
        ):
            codigo, resultado = _pedir(
                base, "POST", f"/v1/pedidos/{pedido_id}/estado",
                {"estado": estado, **extra}, auth,
            )
            if codigo != 200:
                raise Fallo(f"pasar a `{estado}` respondió {codigo}: {resultado}")
        _ok("en_preparacion → listo_para_recoger → entregado")

        if limpiar:
            _paso(11, "Se borra el pedido de prueba")
            codigo, _ = _pedir(
                base, "POST", f"/v1/pedidos/{pedido_id}/estado",
                {"estado": "cancelado"}, auth,
            )
            _ok("cancelado" if codigo == 200 else f"no se pudo ({codigo})")

    total = time.monotonic() - arranque
    print()
    print(f"   Cadena del cliente: {_VERDE}{segundos_cliente:.2f} s{_FIN} "
          f"{_GRIS}(del escaneo al código){_FIN}")
    print(f"   Cadena completa:    {total:.2f} s")
    print(f"   Pedido de prueba:   #{pedido_id}")
    return 0


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else BASE_POR_DEFECTO).rstrip("/")
    limpiar = "--limpiar" in sys.argv

    print(f"\n   Verificando {base}\n")
    try:
        return verificar(base, limpiar)
    except Fallo as error:
        print(f"{_ROJO}roto{_FIN}\n\n   {error}\n")
        return 1
    except urllib.error.URLError as error:
        print(f"{_ROJO}roto{_FIN}\n\n   No se pudo llegar a {base}: "
              f"{error.reason}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
