"""Prueba de regresión sobre la línea base de latencia de POST /pedidos.

Protege el umbral de ESC-02 (ver docs/restriccion-s5.md). No pretende ser una
prueba de carga: mide la latencia del corte vertical en proceso, que es la
parte que la arquitectura controla directamente. El umbral es deliberadamente
holgado respecto de la línea base medida en local para no volverse inestable
en los runners compartidos de CI.
"""

from scripts.medir_linea_base import medir

UMBRAL_P95_MS = 50.0


def test_p95_de_crear_pedido_bajo_umbral():
    resultado = medir(100)

    assert resultado["p95_ms"] < UMBRAL_P95_MS, (
        f"Regresión de rendimiento en POST /pedidos: "
        f"p95={resultado['p95_ms']:.2f} ms supera el umbral de {UMBRAL_P95_MS} ms. "
        f"Línea base documentada en docs/restriccion-s5.md."
    )
