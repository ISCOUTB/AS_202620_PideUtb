"""Ata las constantes y los textos del sitio a lo que arc42 promete.

Estas pruebas no ejercitan código Python: leen los archivos del sitio y
comprueban dos cosas que ninguna otra prueba puede ver, porque el sitio es
estático y no pasa por `TestClient`.

1. Que los números que sostienen un escenario de calidad sigan cumpliéndolo.
2. Que ningún texto explique el comportamiento del sistema con una plataforma
   que ya no se usa.

Las dos nacen del mismo hallazgo de la semana 11 (arc42 §7.6): **la
configuración no viaja por el mismo camino que las pruebas**. La respuesta no es
documentarlo mejor, es que falle.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SITIO = RAIZ / "sitio"

#: Presupuesto total de ESC-03, en milisegundos.
#:
#: arc42 §10.4: «El cambio de estado deberá completarse en máximo 10 segundos».
#: El estímulo del escenario es *recibir un pedido pagado* y la respuesta
#: incluye *visualizarlo*, así que el reloj arranca en el pago y el tiempo que
#: la cola tarda en mostrarlo cuenta dentro.
PRESUPUESTO_ESC_03_MS = 10_000

#: Lo que se reserva para la persona: ver el pedido nuevo y pulsar.
#:
#: Dos segundos es generoso para un clic y escaso para una cocina en hora pico.
#: Se elige explícito para que el margen sea discutible en vez de implícito.
MARGEN_HUMANO_MS = 2_000

#: Archivos del sitio que esta suite inspecciona.
ARCHIVOS_DEL_SITIO = ("config.js", "app.js", "panel.js", "index.html", "panel.html")

#: Archivos cuyo contenido **lo lee una persona**, no solo quien programa.
#:
#: En estos, una mención a la plataforma antigua no se arregla con un paréntesis
#: aclaratorio: el usuario no lee comentarios, lee la frase que le sale en
#: pantalla. Así que aquí no se permite ni en pasado.
ARCHIVOS_CON_TEXTO_VISIBLE = ("index.html", "panel.html")

#: Rastros de la plataforma anterior. `\b` importa: «render» es subcadena de
#: «renderiza», que los scripts usan con todo derecho para hablar de pintar el
#: DOM, y sin el límite de palabra la prueba da un falso positivo en cuanto
#: alguien escribe el verbo.
RASTROS_DE_RENDER = (r"\brender\b", r"plan gratuito", r"duerme el servicio")

#: Cuántos caracteres alrededor de la mención se admiten para encontrar la
#: corrección. Un comentario que nombra Render y remite a ADR-0008 cuatrocientas
#: líneas más abajo no está corrigiendo nada.
VENTANA_DE_CORRECCION = 400


def _constante(archivo: str, nombre: str) -> int:
    """Devuelve el entero asignado a `nombre` en un archivo del sitio."""
    texto = (SITIO / archivo).read_text(encoding="utf-8")
    hallado = re.search(rf"\b{nombre}\b\s*[:=]\s*(\d+)", texto)
    assert hallado is not None, (
        f"No se encontró la constante `{nombre}` en sitio/{archivo}. "
        "Si se renombró, hay que actualizar esta prueba: el umbral que protege "
        "sigue existiendo aunque el nombre cambie."
    )
    return int(hallado.group(1))


def test_el_refresco_del_panel_cabe_en_el_presupuesto_de_esc_03():
    """El sondeo de la cola no puede comerse el plazo de ESC-03.

    Lo que esta prueba impide es un cambio concreto y plausible: subir el
    intervalo de refresco para hacer menos peticiones. Es una línea, no rompe
    nada visible, y deja un escenario de calidad incumplido sin que nadie se
    entere hasta que el personal del mostrador se queja de que los pedidos
    «aparecen tarde».
    """
    intervalo = _constante("panel.js", "MS_ENTRE_REFRESCOS")
    disponible = PRESUPUESTO_ESC_03_MS - MARGEN_HUMANO_MS

    assert intervalo <= disponible, (
        f"MS_ENTRE_REFRESCOS = {intervalo} ms deja solo "
        f"{PRESUPUESTO_ESC_03_MS - intervalo} ms para que una persona vea el "
        f"pedido y pulse. ESC-03 (arc42 §10.4) concede "
        f"{PRESUPUESTO_ESC_03_MS} ms en total desde que el pedido se paga."
    )


def test_el_margen_de_esc_03_esta_agotado_y_eso_consta():
    """Hoy el intervalo está **exactamente** en el límite, y es el hallazgo.

    No es redundante con la anterior: esa impide empeorar, esta documenta que no
    hay hacia dónde empeorar. Si alguien baja el intervalo y crea margen, esta
    prueba falla y obliga a venir a retirar el riesgo de arc42 §11.

    Se escribe así a propósito. Un riesgo que se resuelve y nadie borra de la
    documentación es la otra mitad del problema que esta suite ataca.
    """
    intervalo = _constante("panel.js", "MS_ENTRE_REFRESCOS")

    assert intervalo == PRESUPUESTO_ESC_03_MS - MARGEN_HUMANO_MS, (
        f"MS_ENTRE_REFRESCOS = {intervalo} ms ya no agota el presupuesto de "
        "ESC-03. Si se bajó a propósito, el riesgo «margen nulo de ESC-03» de "
        "arc42 §11 hay que actualizarlo o retirarlo."
    )


@pytest.mark.parametrize("archivo", ARCHIVOS_DEL_SITIO)
def test_el_sitio_no_presenta_render_como_una_causa_vigente(archivo):
    """Nombrar la plataforma vieja se permite; afirmarla como causa, no.

    El sistema se desplegaba en el plan gratuito de Render, que dormía el
    servicio tras 15 minutos sin tráfico. ADR-0008 lo movió al servidor del
    laboratorio, donde el contenedor **no duerme**, y ADR-0004 quedó reemplazada
    diciéndolo con todas las letras.

    Lo que no cambió fue el sitio. Durante los cinco días que siguieron
    —ADR-0008 es del 13/10/2026 y esto se encontró el 18— siguió mostrando a los
    usuarios «es el arranque en frío del plan gratuito»: no un comentario
    desactualizado, sino **una causa falsa delante de una persona** que, creyendo
    que el servicio despierta, espera un minuto que no va a servirle de nada.

    La regla que se verifica no es «no digas Render». Explicar de dónde viene una
    constante es legítimo y útil. La regla es que la mención venga **con su
    corrección al lado**, de modo que quien la lea no se quede con la premisa
    muerta. En los archivos que muestran texto a una persona no se permite
    siquiera eso, porque nadie lee los comentarios de un HTML.
    """
    ruta = SITIO / archivo
    if not ruta.exists():  # pragma: no cover — depende de los archivos del sitio
        pytest.skip(f"sitio/{archivo} no existe")

    texto = ruta.read_text(encoding="utf-8").lower()
    visible = archivo in ARCHIVOS_CON_TEXTO_VISIBLE

    for rastro in RASTROS_DE_RENDER:
        for mencion in re.finditer(rastro, texto):
            legible = rastro.replace(r"\b", "")

            assert not visible, (
                f"sitio/{archivo} menciona «{legible}», y es un archivo que "
                "muestra texto a una persona. Aquí la plataforma antigua no "
                "cabe ni en pasado: el usuario no lee comentarios."
            )

            desde = max(0, mencion.start() - VENTANA_DE_CORRECCION)
            hasta = mencion.end() + VENTANA_DE_CORRECCION

            assert "adr-0008" in texto[desde:hasta], (
                f"sitio/{archivo} menciona «{legible}» sin corregirla cerca. "
                "La plataforma cambió con ADR-0008 y el arranque en frío dejó "
                "de existir: una mención sin esa aclaración se lee como causa "
                "vigente, que es justo el defecto que esta prueba persigue."
            )
