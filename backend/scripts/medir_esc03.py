"""Mide la cadena de ESC-03 contra su umbral, y dice si lo cumple.

Uso (desde `backend/`, con `PIDEUTB_DATABASE_URL` apuntando a PostgreSQL):

    python scripts/medir_esc03.py [n_repeticiones] [--rtt MS] [--cola N]

### Qué mide, y por qué no basta con un número

[ESC-03](../../docs/arc42/arc42.md#esc-03) concede **10 segundos** desde que un
pedido se paga hasta que el encargado lo ha visualizado y cambiado de estado,
sin recargar la página. El estímulo del escenario es *recibir un pedido pagado*
y la respuesta incluye *visualizarlo*, así que el reloj arranca en el pago: el
tiempo que la cola tarda en mostrarlo **cuenta dentro del plazo**.

La cadena completa tiene cuatro tramos, y solo dos ocurren en el servidor:

    [1] espera al siguiente sondeo   hasta 8 000 ms   (sitio/panel.js)
    [2] GET /v1/pedidos               red + servidor
    [3] la persona ve y pulsa         ???
    [4] POST /{id}/estado             red + servidor

Este guion mide la parte de servidor de [2] y [4]. La red se pasa por
`--rtt` porque **no se puede medir desde aquí**: depende de dónde esté quien
mira. El valor por defecto son los 150,8 ms medidos contra el despliegue el
18/10/2026 sobre una conexión reutilizada, que es como sondea el panel
(`docs/evidencia-s14.md` §1).

Lo que el guion devuelve no es una latencia: es **cuánto tiempo le queda a la
persona**, que es la cifra con la que se decide si el escenario se cumple.

### Por qué exige PostgreSQL

Medir contra el almacenamiento en memoria daría un número bonito y falso: la
cola del mostrador se lee con una consulta cuyo coste crece con los pedidos del
establecimiento, y en memoria eso es un filtro sobre un diccionario. El
escenario se evalúa contra lo que corre en producción o no se evalúa.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.autenticacion import personal_de_establecimiento, usuario_actual  # noqa: E402
from app.main import app  # noqa: E402
from app.pedidos import service as pedidos_service  # noqa: E402
from app.usuarios.contracts import RolUsuario, UsuarioAutenticado  # noqa: E402

#: Umbral del escenario, en milisegundos.
PRESUPUESTO_ESC_03_MS = 10_000

#: Intervalo de sondeo del panel. Se lee del archivo, no se copia: una
#: constante duplicada aquí dejaría de coincidir sin que nadie se enterase.
RUTA_PANEL = Path(__file__).resolve().parents[2] / "sitio" / "panel.js"

#: Ida y vuelta de red medida contra el despliegue, conexión reutilizada.
RTT_MEDIDO_MS = 150.8

MOSTRADOR = UsuarioAutenticado(
    usuario_id=1,
    correo="medicion@utb.edu.co",
    rol=RolUsuario.PERSONAL_ESTABLECIMIENTO,
    establecimiento_id=1,
)


def intervalo_de_sondeo_ms() -> int:
    """Lee `MS_ENTRE_REFRESCOS` del panel."""
    import re

    texto = RUTA_PANEL.read_text(encoding="utf-8")
    hallado = re.search(r"\bMS_ENTRE_REFRESCOS\s*=\s*(\d+)", texto)
    if hallado is None:
        raise SystemExit(f"No se encontró MS_ENTRE_REFRESCOS en {RUTA_PANEL}")
    return int(hallado.group(1))


def percentil(muestras: list[float], p: float) -> float:
    ordenadas = sorted(muestras)
    indice = min(int(round(p / 100 * len(ordenadas))) - 1, len(ordenadas) - 1)
    return ordenadas[max(indice, 0)]


def resumen(nombre: str, muestras: list[float]) -> dict[str, float]:
    return {
        "operacion": nombre,
        "n": len(muestras),
        "min": min(muestras),
        "p50": statistics.median(muestras),
        "p95": percentil(muestras, 95),
        "max": max(muestras),
    }


def _pedido_pagado(client: TestClient) -> int:
    """Un pedido en `pagado`, por la vía legítima."""
    respuesta = client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1})
    if respuesta.status_code != 201:
        raise SystemExit(f"No se pudo crear el pedido: {respuesta.status_code} {respuesta.text}")
    pedido_id = respuesta.json()["pedido_id"]
    pedidos_service.confirmar_pago(pedido_id)
    return pedido_id


def medir(n: int, cola: int) -> list[dict[str, float]]:
    app.dependency_overrides[personal_de_establecimiento] = lambda: MOSTRADOR
    app.dependency_overrides[usuario_actual] = lambda: MOSTRADOR

    try:
        client = TestClient(app)

        # Una cola realista. Con un solo pedido, `GET /v1/pedidos` mide el caso
        # que nunca ocurre: el escenario habla de «varios pedidos simultáneos».
        for _ in range(cola):
            _pedido_pagado(client)

        # Calentamiento: descarta el coste de abrir el pool y compilar rutas.
        for _ in range(10):
            client.get("/v1/pedidos")

        lecturas: list[float] = []
        for _ in range(n):
            inicio = time.perf_counter()
            respuesta = client.get("/v1/pedidos")
            lecturas.append((time.perf_counter() - inicio) * 1000)
            if respuesta.status_code != 200:
                raise SystemExit(f"GET /v1/pedidos: {respuesta.status_code} {respuesta.text}")

        # Cada transición necesita un pedido nuevo: `pagado → en_preparacion`
        # solo se puede hacer una vez por pedido, y repetirla daría 409.
        transiciones: list[float] = []
        for _ in range(n):
            pedido_id = _pedido_pagado(client)
            inicio = time.perf_counter()
            respuesta = client.post(
                f"/v1/pedidos/{pedido_id}/estado", json={"estado": "en_preparacion"}
            )
            transiciones.append((time.perf_counter() - inicio) * 1000)
            if respuesta.status_code != 200:
                raise SystemExit(
                    f"POST /{pedido_id}/estado: {respuesta.status_code} {respuesta.text}"
                )

        return [
            resumen("GET /v1/pedidos (el sondeo)", lecturas),
            resumen("POST /{id}/estado (el cambio)", transiciones),
        ]
    finally:
        app.dependency_overrides.clear()


def informe(medidas: list[dict[str, float]], rtt: float, cola: int) -> int:
    sondeo = intervalo_de_sondeo_ms()
    lectura, transicion = medidas

    print(f"\nCola del establecimiento durante la medición: {cola} pedidos")
    print(f"Almacenamiento: PostgreSQL\n")
    print(f"{'Operación':<32} {'n':>4} {'mín':>8} {'p50':>8} {'p95':>8} {'máx':>9}")
    print("-" * 74)
    for m in medidas:
        print(
            f"{m['operacion']:<32} {m['n']:>4} {m['min']:>8.2f} "
            f"{m['p50']:>8.2f} {m['p95']:>8.2f} {m['max']:>9.2f}"
        )

    # El peor caso es el que el escenario exige: «máximo 10 segundos» es un
    # techo, no una mediana. El peor sondeo es el completo, porque el pago pudo
    # ocurrir un milisegundo después del anterior.
    servidor = lectura["p95"] + transicion["p95"]
    red = 2 * rtt
    consumido = sondeo + red + servidor
    queda = PRESUPUESTO_ESC_03_MS - consumido

    print(f"\n{'Tramo':<44} {'ms':>10}")
    print("-" * 56)
    print(f"{'[1] espera al siguiente sondeo (peor caso)':<44} {sondeo:>10.1f}")
    print(f"{'[2+4] red, dos idas y vueltas':<44} {red:>10.1f}")
    print(f"{'[2+4] servidor (p95 de las dos)':<44} {servidor:>10.2f}")
    print("-" * 56)
    print(f"{'consumido sin contar a la persona':<44} {consumido:>10.1f}")
    print(f"{'presupuesto de ESC-03':<44} {PRESUPUESTO_ESC_03_MS:>10.1f}")
    print(f"{'QUEDA PARA QUE LA PERSONA VEA Y PULSE':<44} {queda:>10.1f}")

    print()
    if queda < 0:
        print("VEREDICTO: ESC-03 NO SE CUMPLE ni con reacción instantánea.")
        return 1
    if queda < 2_000:
        print(f"VEREDICTO: ESC-03 se cumple solo si la persona reacciona en menos")
        print(f"           de {queda/1000:.2f} s. Es poco para un mostrador en hora pico:")
        print(f"           el margen depende de la persona, no del sistema.")
        return 1
    print(f"VEREDICTO: ESC-03 se cumple con {queda/1000:.2f} s de margen para la persona.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide la cadena de ESC-03.")
    parser.add_argument("n", nargs="?", type=int, default=50, help="repeticiones (50)")
    parser.add_argument("--rtt", type=float, default=RTT_MEDIDO_MS,
                        help=f"ida y vuelta de red en ms ({RTT_MEDIDO_MS})")
    parser.add_argument("--cola", type=int, default=10,
                        help="pedidos en la cola durante la medición (10)")
    args = parser.parse_args()

    if not os.getenv("PIDEUTB_DATABASE_URL", "").strip():
        print(
            "Falta PIDEUTB_DATABASE_URL.\n\n"
            "Este guion no mide contra el almacenamiento en memoria a propósito: "
            "la cola del mostrador se lee con una consulta cuyo coste crece con "
            "los pedidos del establecimiento, y en memoria eso es un filtro sobre "
            "un diccionario. Daría un número bonito y falso.",
            file=sys.stderr,
        )
        return 2

    return informe(medir(args.n, args.cola), args.rtt, args.cola)


if __name__ == "__main__":
    raise SystemExit(main())
