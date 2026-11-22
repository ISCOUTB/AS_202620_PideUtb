"""El guion que mide ESC-03 tiene que poder repetirse con el contrato vigente.

`scripts/medir_esc03.py` es la evidencia reproducible de ESC-03 (arc42 §10.4,
`docs/evidencia-s14.md`), y no corre en CI porque mide contra PostgreSQL. Eso lo
dejó roto sin que nadie lo notara: seguía creando pedidos con el formato de la
2.x, y desde el carrito (3.0.0) la API los rechazaba con 422. La medición que
sostiene el escenario no se podía repetir.

Esta prueba ejecuta la misma cadena en memoria. **No mide nada**: la cifra que
vale es la de PostgreSQL. Lo que comprueba es que el guion sigue hablando el
contrato de hoy, para que la próxima rotura del contrato también rompa la
construcción y no la sustentación.
"""
from scripts import medir_esc03


def test_el_guion_recorre_la_cadena_de_esc_03_con_el_contrato_vigente():
    lectura, transicion = medir_esc03.medir(n=3, cola=2)

    assert lectura["n"] == 3
    assert transicion["n"] == 3


def test_el_guion_da_un_veredicto_con_lo_que_mide(capsys):
    """El informe lee el sondeo de `panel.js` y dice cuánto le queda a la persona."""
    codigo = medir_esc03.informe(medir_esc03.medir(n=3, cola=1), rtt=150.8, cola=1)

    salida = capsys.readouterr().out
    assert "QUEDA PARA QUE LA PERSONA VEA Y PULSE" in salida
    assert codigo == 0, salida
