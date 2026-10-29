"""Cuánta gente puede pedir a la vez sin que la charla se note lenta.

    python scripts/medir_carga_demo.py                      # 40 personas, local
    python scripts/medir_carga_demo.py 60 https://api-pideutb.iscoutb.dev

Cada «persona» hace lo mismo que hará el público: pide la carta, crea su
pedido, abre el cobro, pasa por la pasarela y mira su código. Todas arrancan a
la vez.

### Por qué hace falta medirlo y no estimarlo

La API del laboratorio corre con **0,5 CPU de tope** (ADR-0008) y el pool de
PostgreSQL tiene un tamaño fijo. Con 60 personas a la vez el cuello puede estar
en cualquiera de los dos, y la diferencia importa: la CPU se pide al laboratorio
y el pool se cambia en una variable. Sin medir no se sabe cuál.

### Qué cuenta como «bien»

El requisito de la charla es **menos de un minuto desde escanear hasta ver el
código**, y eso incluye a una persona leyendo la carta y eligiendo. De ese
minuto, lo que este guion mide —las cinco peticiones— debería ser ruido: si el
p95 pasa de 3 s, la elección deja de caber.

### Lo que NO mide

El navegador. Descargar `app.js`, pintar 37 productos y que alguien toque los
botones no está acá; eso se ve con el panel de red del navegador. Esto mide la
cadena del servidor, que es la que se cae por concurrencia.

### Qué deja detrás

Tantos pedidos pagados como personas se simulen. Con `--limpiar` y
`PIDEUTB_TOKEN_REINICIO_DEMO` los borra al terminar; sin eso hay que reiniciar
a mano antes de la charla, o el primer pedido del público será el #61.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_POR_DEFECTO = "http://127.0.0.1:8000"
PERSONAS_POR_DEFECTO = 40
ESTABLECIMIENTO = int(os.getenv("PIDEUTB_ESTABLECIMIENTO_DEMO", "5"))

#: Por encima de esto, el minuto de la charla deja de tener holgura para que
#: alguien lea la carta y elija.
P95_ACEPTABLE_S = 3.0

_VERDE, _AMBAR, _ROJO, _GRIS, _FIN = (
    "\033[32m", "\033[33m", "\033[31m", "\033[90m", "\033[0m",
)


def _pedir(base: str, metodo: str, ruta: str, cuerpo: dict | None = None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"{base}{ruta}", data=datos, method=metodo,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        crudo = respuesta.read().decode()
        return json.loads(crudo) if crudo else {}


def _una_persona(base: str, items: list[dict]) -> tuple[float, str | None]:
    """El recorrido completo de alguien del público. Devuelve (segundos, error)."""
    arranque = time.monotonic()
    try:
        # Dos productos distintos por persona, rotando, para que no todas
        # golpeen la misma fila: un pedido idéntico repetido 60 veces mediría
        # el caché de PostgreSQL más que el sistema.
        i = int(time.monotonic() * 1000) % len(items)
        lineas = [{"item_id": items[i]["item_id"], "cantidad": 1}]
        if len(items) > 1:
            lineas.append({"item_id": items[(i + 1) % len(items)]["item_id"], "cantidad": 2})

        pedido = _pedir(base, "POST", "/v1/pedidos", {"lineas": lineas})
        intento = _pedir(
            base, "POST", "/v1/pagos/intentos",
            {"pedido_id": pedido["pedido_id"], "metodo": "tarjeta"},
        )
        _pedir(
            base, "POST", f"/v1/pagos/simulador/{intento['referencia_pago']}",
            {"estado_pago": "aprobado"},
        )
        visto = _pedir_con_token(
            base, f"/v1/pedidos/{pedido['pedido_id']}", pedido["token_consulta"]
        )
        if not visto.get("codigo_canje"):
            return time.monotonic() - arranque, "pagado sin código de canje"
        return time.monotonic() - arranque, None
    except urllib.error.HTTPError as error:
        return time.monotonic() - arranque, f"HTTP {error.code} en {error.url}"
    except Exception as error:  # noqa: BLE001 — cualquier fallo es un dato
        return time.monotonic() - arranque, f"{type(error).__name__}: {error}"


def _pedir_con_token(base: str, ruta: str, token: str) -> dict:
    peticion = urllib.request.Request(
        f"{base}{ruta}", headers={"X-Token-Pedido": token}
    )
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return json.loads(respuesta.read().decode())


def medir(base: str, personas: int, limpiar: bool) -> int:
    print(f"\n   {personas} personas a la vez contra {base}\n")

    carta = _pedir(base, "GET", f"/v1/menu/establecimientos/{ESTABLECIMIENTO}/items")
    items = [i for i in carta["items"] if i["disponible"]]
    if not items:
        print(f"{_ROJO}   El establecimiento {ESTABLECIMIENTO} no tiene productos "
              f"disponibles.{_FIN}\n")
        return 1

    # Una comprobación barata antes de lanzar 60 hilos contra una ruta que
    # quizá no existe: sin la pasarela simulada, las 60 fallarían igual y el
    # informe diría «60 errores» en vez de «falta una variable».
    sonda = _una_persona(base, items)
    if sonda[1]:
        print(f"{_ROJO}   La cadena ya falla con una sola persona: {sonda[1]}{_FIN}")
        print(f"{_GRIS}   Corré primero scripts/verificar_flujo.py, que dice en qué "
              f"eslabón.{_FIN}\n")
        return 1

    arranque = time.monotonic()
    with ThreadPoolExecutor(max_workers=personas) as grupo:
        resultados = list(grupo.map(lambda _: _una_persona(base, items), range(personas)))
    total = time.monotonic() - arranque

    tiempos = sorted(t for t, e in resultados if e is None)
    errores = [e for _, e in resultados if e is not None]

    if not tiempos:
        print(f"{_ROJO}   Fallaron las {personas}.{_FIN}")
        for mensaje in dict.fromkeys(errores):
            print(f"     {mensaje}")
        print()
        return 1

    p50 = statistics.median(tiempos)
    p95 = tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.95))]

    print(f"   Completaron   {len(tiempos)} de {personas}")
    print(f"   p50           {p50:.2f} s")
    color = _VERDE if p95 < P95_ACEPTABLE_S else _AMBAR
    print(f"   p95           {color}{p95:.2f} s{_FIN} "
          f"{_GRIS}(umbral {P95_ACEPTABLE_S:.0f} s){_FIN}")
    print(f"   el más lento  {max(tiempos):.2f} s")
    print(f"   pared         {total:.2f} s para las {personas}")
    print(f"   rendimiento   {len(tiempos) / total:.1f} pedidos/s")

    if errores:
        print(f"\n{_ROJO}   {len(errores)} fallaron:{_FIN}")
        for mensaje, veces in _contar(errores):
            print(f"     {veces}×  {mensaje}")

    if limpiar:
        token = os.getenv("PIDEUTB_TOKEN_REINICIO_DEMO", "").strip()
        if not token:
            print(f"\n{_AMBAR}   --limpiar sin PIDEUTB_TOKEN_REINICIO_DEMO: "
                  f"los {personas} pedidos se quedan.{_FIN}")
        else:
            peticion = urllib.request.Request(
                f"{base}/v1/demo/reiniciar", data=b"", method="POST",
                headers={"X-Token-Demo": token, "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                    borrados = json.loads(respuesta.read().decode())["borrados"]
                print(f"\n   Borrados: {borrados}")
            except urllib.error.HTTPError as error:
                print(f"\n{_AMBAR}   El reinicio respondió {error.code}: el token no "
                      f"vale o la ruta está apagada.{_FIN}")

    print()
    return 0 if not errores and p95 < P95_ACEPTABLE_S else 1


def _contar(mensajes: list[str]) -> list[tuple[str, int]]:
    cuenta: dict[str, int] = {}
    for mensaje in mensajes:
        cuenta[mensaje] = cuenta.get(mensaje, 0) + 1
    return sorted(cuenta.items(), key=lambda par: -par[1])


def main() -> int:
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    personas = int(argumentos[0]) if argumentos else PERSONAS_POR_DEFECTO
    base = (argumentos[1] if len(argumentos) > 1 else BASE_POR_DEFECTO).rstrip("/")
    return medir(base, personas, "--limpiar" in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
