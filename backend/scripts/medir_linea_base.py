"""Mide la línea base de latencia del corte vertical de pedidos (ESC-01 / ESC-02).

Uso (desde backend/):
    python scripts/medir_linea_base.py [n_repeticiones]

Ejecuta N veces el flujo POST /pedidos contra la aplicación en proceso y
reporta latencia mínima, p50, p95 y máxima en milisegundos. El resultado es la
medición de referencia contra la cual se compara cualquier optimización
posterior; se registra en docs/restriccion-s5.md.
"""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PEDIDO = {"establecimiento_id": 1, "item_id": 1, "cantidad": 2}


def percentil(muestras: list[float], p: float) -> float:
    ordenadas = sorted(muestras)
    indice = min(int(round(p / 100 * len(ordenadas))) - 1, len(ordenadas) - 1)
    return ordenadas[max(indice, 0)]


def medir(n: int) -> dict[str, float]:
    client = TestClient(app)

    # Calentamiento: descarta el costo del primer arranque de la app.
    for _ in range(10):
        client.post("/pedidos", json=PEDIDO)

    muestras = []
    for _ in range(n):
        inicio = time.perf_counter()
        respuesta = client.post("/pedidos", json=PEDIDO)
        muestras.append((time.perf_counter() - inicio) * 1000)
        assert respuesta.status_code == 201, respuesta.text

    return {
        "n": n,
        "min_ms": min(muestras),
        "p50_ms": statistics.median(muestras),
        "p95_ms": percentil(muestras, 95),
        "max_ms": max(muestras),
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    r = medir(n)
    print(f"Línea base POST /pedidos  (n={r['n']} peticiones)")
    print(f"  min  : {r['min_ms']:.2f} ms")
    print(f"  p50  : {r['p50_ms']:.2f} ms")
    print(f"  p95  : {r['p95_ms']:.2f} ms")
    print(f"  max  : {r['max_ms']:.2f} ms")
