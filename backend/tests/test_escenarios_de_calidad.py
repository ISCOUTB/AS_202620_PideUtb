"""Ata las constantes y los textos del repositorio a lo que es cierto hoy.

Estas pruebas no ejercitan código: leen archivos y comprueban dos cosas que
ninguna otra puede ver, porque no ocurren en tiempo de ejecución.

1. Que los números que sostienen un escenario de calidad sigan cumpliéndolo.
2. Que ningún texto explique el comportamiento del sistema con una plataforma
   que ya no se usa.

Las dos nacen del mismo hallazgo (arc42 §7.6): **la configuración y los
comentarios no viajan por el mismo camino que las pruebas**. La respuesta no es
documentarlo mejor, es que falle.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SITIO = RAIZ / "sitio"

# ---------------------------------------------------------------------------
# Umbrales de escenario
# ---------------------------------------------------------------------------

#: Presupuesto total de ESC-03, en milisegundos.
#:
#: arc42 §10.4: «El cambio de estado deberá completarse en máximo 10 segundos».
#: El estímulo del escenario es *recibir un pedido pagado* y la respuesta
#: incluye *visualizarlo*, así que el reloj arranca en el pago y el tiempo que
#: la cola tarda en mostrarlo cuenta dentro.
PRESUPUESTO_ESC_03_MS = 10_000

#: Lo que se reserva para la persona: ver el pedido nuevo y pulsar.
#:
#: Estuvo en 2 000 hasta la S14. La medición de la cadena completa mostró que
#: ese valor dejaba al escenario cumpliéndose solo con una reacción de 1,68 s
#: mientras se cocina, que no es realista. Cuatro segundos es generoso y sigue
#: siendo explícito: el margen se discute cambiando esta constante, no
#: descubriéndolo en producción.
MARGEN_HUMANO_MS = 4_000

#: Lo que cuestan la red y el servidor en la cadena de ESC-03, medido.
#:
#: Dos idas y vueltas —leer la cola y cambiar el estado— más el tiempo de
#: servidor de las dos operaciones:
#:
#:   red          2 × 150,8 ms  · conexión reutilizada, contra el despliegue
#:   servidor      7,96 + 10,70 · p95 con PostgreSQL y 10 pedidos en cola
#:
#: Se vuelve a medir con `backend/scripts/medir_esc03.py`. Está aquí como
#: constante y no como medición en vivo porque una prueba que depende de la red
#: falla por motivos que no son el defecto que busca.
COSTO_RED_Y_SERVIDOR_MS = 321

#: Cuánta holgura se admite por debajo de lo que el presupuesto permite.
#:
#: Un segundo. Sondear más a menudo de lo necesario no mejora ESC-03 y sí
#: multiplica las peticiones de cada panel abierto, así que el valor elegido
#: debe ser el más largo que cabe — no el más corto que se nos ocurra.
HOLGURA_MAXIMA_MS = 1_000

# ---------------------------------------------------------------------------
# Rastros de la plataforma anterior
# ---------------------------------------------------------------------------

#: Dónde se vigila. No se barre el repositorio entero a propósito.
#:
#: `docs/` queda fuera porque contiene evidencias semanales, ADRs reemplazados y
#: comparativas que **deben** hablar de la plataforma vieja: son el registro de
#: cuando era la actual. Reescribir la historia para que una prueba pase sería
#: peor que el defecto que la prueba busca.
#:
#: `backend/migraciones` queda fuera por un motivo más duro, y aprendido a
#: golpes. Una migración ya aplicada **es inmutable, comentarios incluidos**:
#: `scripts/migrar.py` compara un sha256 del archivo entero contra la huella que
#: guardó la base, así que corregir una palabra de un comentario deja el
#: contenedor en bucle de reinicio.
#:
#: Esta lista incluía `backend/migraciones` en su primera versión, y eso
#: **provocó una caída de producción**: la prueba exigía corregir el comentario
#: sobre Supabase de `001_esquema_inicial.sql`, se corrigió, y la API dejó de
#: arrancar. La prueba pedía exactamente el cambio que rompía el sistema.
#:
#: Así que ahí la documentación se queda inexacta a propósito, y la corrección
#: vive en arc42 §7.6. `tests/test_migraciones.py` vigila lo contrario: que esos
#: archivos **no** cambien.
AMBITOS = ("backend/app", "backend/scripts", "sitio", "deploy")

#: Archivos cuyo contenido **lo lee una persona**, no solo quien programa.
#:
#: Aquí una mención no se arregla con un paréntesis aclaratorio: el usuario no
#: lee comentarios, lee la frase que le sale en pantalla.
EXTENSIONES_VISIBLES = (".html",)

#: `\b` importa: «render» es subcadena de «renderiza», que los scripts usan con
#: todo derecho para hablar de pintar el DOM.
RASTROS = (r"\brender\b", r"\bsupabase\b", r"plan gratuito", r"duerme el servicio")

#: Señales de que la mención está en pasado y corregida. Basta una cerca.
#:
#: Se acepta cualquiera de estas en vez de exigir «ADR-0008» porque lo que
#: importa no es citar la decisión sino **no presentar la premisa como
#: vigente**. Un «antes era X, hoy es Y» cumple el objetivo sin nota al pie.
MARCAS_DE_PASADO = (
    r"adr-0008", r"anterior", r"ya no", r"dej[óo] de", r"desapareci[óe]",
    r"nació", r"nacio", r"antes era", r"de entonces", r"obsolet",
    r"lo era con", r"cambi[óo] de sitio", r"reemplaz",
)

#: Menciones que no son a la plataforma. `ADR-0007` se titula literalmente
#: «...en lugar de Supabase Auth», así que nombrarlo es citar una decisión
#: vigente, no arrastrar una premisa muerta.
EXCEPCIONES = (r"supabase auth",)

#: Caracteres alrededor de la mención donde se admite la corrección. Un
#: comentario que remite a ADR-0008 cuatrocientas líneas más abajo no corrige.
VENTANA = 400


def _archivos_vigilados() -> list[str]:
    """Rutas versionadas dentro de los ámbitos vigilados."""
    salida = subprocess.run(
        ["git", "ls-files", *AMBITOS],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return [linea for linea in salida.splitlines() if linea.strip()]


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
    disponible = PRESUPUESTO_ESC_03_MS - MARGEN_HUMANO_MS - COSTO_RED_Y_SERVIDOR_MS

    assert intervalo <= disponible, (
        f"MS_ENTRE_REFRESCOS = {intervalo} ms deja "
        f"{PRESUPUESTO_ESC_03_MS - intervalo - COSTO_RED_Y_SERVIDOR_MS} ms para "
        f"que una persona vea el pedido y pulse, y hacen falta "
        f"{MARGEN_HUMANO_MS}. ESC-03 (arc42 §10.4) concede "
        f"{PRESUPUESTO_ESC_03_MS} ms en total desde que el pedido se paga, de "
        f"los que {COSTO_RED_Y_SERVIDOR_MS} se van en red y servidor."
    )


def test_el_refresco_es_el_mas_largo_que_cabe_en_el_presupuesto():
    """La otra mitad: sondear más a menudo de lo necesario también es un defecto.

    La prueba anterior impide que el intervalo crezca y rompa ESC-03. Esta
    impide que se encoja sin motivo: cada sondeo es una petición por panel
    abierto, y bajarlo «por si acaso» multiplica el tráfico sin mejorar nada que
    el escenario mida.

    Juntas dicen que el valor está **elegido** y no heredado: es el más largo
    que cabe en el presupuesto, con una holgura declarada.

    Esta prueba nació fallando. En la S12 afirmaba que el margen estaba agotado,
    para que crear margen obligase a volver a mirar el riesgo R-01; la medición
    de la S14 lo creó, la prueba falló como estaba previsto, y esto es el
    resultado de haber vuelto.
    """
    intervalo = _constante("panel.js", "MS_ENTRE_REFRESCOS")
    disponible = PRESUPUESTO_ESC_03_MS - MARGEN_HUMANO_MS - COSTO_RED_Y_SERVIDOR_MS

    assert intervalo >= disponible - HOLGURA_MAXIMA_MS, (
        f"MS_ENTRE_REFRESCOS = {intervalo} ms deja "
        f"{disponible - intervalo} ms de holgura sobre lo que ESC-03 necesita, "
        f"y el máximo aceptado es {HOLGURA_MAXIMA_MS}. Sondear más a menudo "
        "cuesta peticiones y no mejora ningún umbral: si hay un motivo nuevo "
        "para bajarlo, va escrito aquí y en `panel.js`."
    )


@pytest.mark.parametrize("archivo", _archivos_vigilados())
def test_no_se_presenta_una_plataforma_abandonada_como_causa_vigente(archivo):
    """Nombrar la plataforma vieja se permite; afirmarla como causa, no.

    El sistema se desplegaba en el plan gratuito de Render con PostgreSQL en
    Supabase. ADR-0008 lo movió al servidor del laboratorio el 13/10/2026, con
    la base dentro del despliegue, y ADR-0004 quedó reemplazada **diciendo
    expresamente** que la plataforma nueva no tiene arranque en frío.

    El código no se enteró, y durante los cinco días siguientes:

    - `sitio/index.html` mostraba a los usuarios «es el arranque en frío del
      plan gratuito». No un comentario desactualizado: **una causa falsa delante
      de una persona**, que creyendo que el servicio despertaba esperaba un
      minuto inútil.
    - `base_de_datos.py` justificaba el techo del pool con una cuota de
      conexiones de Supabase. Eso es peor que ruido: una constante cuyo motivo
      declarado no existe invita a cambiarla por la razón equivocada.

    La regla que se verifica no es «no digas Render». Explicar de dónde viene una
    decisión es legítimo y a menudo es lo más valioso del comentario. La regla es
    que la mención venga **con su corrección cerca**, para que quien la lea no se
    quede con la premisa muerta.

    `docs/` queda fuera a propósito: las evidencias semanales y los ADR
    reemplazados tienen que hablar de la plataforma vieja, porque son el
    registro de cuando era la actual.
    """
    ruta = RAIZ / archivo
    if not ruta.exists():  # pragma: no cover — el índice de git puede adelantarse
        pytest.skip(f"{archivo} ya no existe en el árbol de trabajo")

    texto = ruta.read_text(encoding="utf-8", errors="replace").lower()
    visible = ruta.suffix in EXTENSIONES_VISIBLES

    for rastro in RASTROS:
        for mencion in re.finditer(rastro, texto):
            legible = rastro.replace(r"\b", "")
            desde = max(0, mencion.start() - VENTANA)
            hasta = mencion.end() + VENTANA
            contexto = texto[desde:hasta]

            if any(re.search(e, contexto) for e in EXCEPCIONES):
                continue

            assert not visible, (
                f"{archivo} menciona «{legible}», y es un archivo que muestra "
                "texto a una persona. Aquí la plataforma abandonada no cabe ni "
                "en pasado: nadie lee los comentarios de un HTML."
            )

            assert any(re.search(m, contexto) for m in MARCAS_DE_PASADO), (
                f"{archivo} menciona «{legible}» sin nada cerca que la sitúe en "
                "el pasado. La plataforma cambió con ADR-0008: una mención sin "
                "esa aclaración se lee como causa vigente, y si además sostiene "
                "una constante, invita a cambiarla por el motivo equivocado."
            )


# ---------------------------------------------------------------------------
# Las cabeceras que nginx no hereda
# ---------------------------------------------------------------------------
#
# En nginx, `add_header` **no se hereda**: si un bloque hijo define una sola
# cabecera, las del padre dejan de aplicarse en esa ruta. El archivo ya
# documenta el caso —`/panel.html` perdió `X-Frame-Options` justo así, y no se
# notó, porque una cabecera ausente no rompe nada visible— pero documentarlo no
# lo impide: cada página nueva con su propio bloque repite la trampa.
#
# Esta prueba es la que lo impide. No ejercita nginx: compara el archivo
# consigo mismo, que es todo lo que hace falta para la clase de error que
# importa aquí.

NGINX = RAIZ / "sitio" / "nginx.conf"

#: Las que protegen y por eso no pueden faltar. `X-Robots-Tag` no está: es una
#: preferencia de indexación, no una defensa, y cada página decide la suya.
CABECERAS_QUE_PROTEGEN = (
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
)


def _bloques_de_location(texto: str) -> dict[str, str]:
    """Devuelve `{ruta: cuerpo}` de cada `location = ...` del archivo.

    Lectura deliberadamente tonta, como la de la semilla: cuenta llaves hasta
    cerrar el bloque. No es un intérprete de nginx porque no tiene que serlo —
    solo lee un archivo que escribimos nosotros.
    """
    bloques: dict[str, str] = {}

    for apertura in re.finditer(r"location\s*=\s*(\S+)\s*\{", texto):
        ruta = apertura.group(1)
        profundidad = 1
        i = apertura.end()
        while i < len(texto) and profundidad:
            if texto[i] == "{":
                profundidad += 1
            elif texto[i] == "}":
                profundidad -= 1
            i += 1
        bloques[ruta] = texto[apertura.end():i - 1]

    return bloques


def test_cada_pagina_con_bloque_propio_repite_las_cabeceras_que_protegen():
    """Un bloque que declara una cabecera tiene que declararlas todas.

    El disparador es declarar **cualquier** `add_header`: es el gesto que
    cancela la herencia. Un bloque sin ninguno sigue recibiendo las del
    servidor y no necesita repetir nada.
    """
    texto = NGINX.read_text(encoding="utf-8")
    bloques = _bloques_de_location(texto)

    assert bloques, "no se encontró ningún bloque `location =` en nginx.conf"

    for ruta, cuerpo in bloques.items():
        if "add_header" not in cuerpo:
            continue  # hereda las del servidor: nada que comprobar

        faltan = [c for c in CABECERAS_QUE_PROTEGEN if c not in cuerpo]
        assert not faltan, (
            f"El bloque `location = {ruta}` de sitio/nginx.conf declara algún "
            f"`add_header` y por eso **cancela** las del servidor, pero le "
            f"faltan {faltan}. En nginx las cabeceras no se heredan en cuanto "
            "el hijo define una: hay que repetirlas todas. Un ausente no rompe "
            "nada visible, que es lo que lo hace fácil de dejar."
        )


def test_el_servidor_declara_las_cabeceras_que_protegen():
    """La otra mitad: que existan en el nivel del que se heredan.

    Sin esto, la prueba de arriba se cumpliría sola el día que alguien las
    borrara del servidor, porque ya no habría nada que repetir.
    """
    texto = NGINX.read_text(encoding="utf-8")
    fuera_de_bloques = re.sub(r"location\s*=\s*\S+\s*\{[^{}]*\}", "", texto)

    faltan = [c for c in CABECERAS_QUE_PROTEGEN if c not in fuera_de_bloques]
    assert not faltan, (
        f"sitio/nginx.conf ya no declara {faltan} en el nivel del servidor. "
        "Las páginas con bloque propio las repiten, pero el resto del sitio "
        "las perdería sin que nada avisara."
    )


# ---------------------------------------------------------------------------
# La portada apunta a datos que existen
# ---------------------------------------------------------------------------

MIGRACIONES = RAIZ / "backend" / "migraciones"


def test_el_establecimiento_de_la_portada_tiene_carta():
    """`CONFIG.ESTABLECIMIENTO_ID` tiene que señalar a algo con productos.

    El fallo que impide es silencioso, que es lo que lo hace peligroso: con un
    identificador que la base no tiene, la API responde `200` con lista vacía
    —porque «existe y no tiene nada» es una respuesta legítima del contrato— y
    la portada dice «este establecimiento todavía no cargó su carta». Nada
    falla, nada se registra, y lo que se ve en una sustentación es una página
    vacía.

    No consulta la base: lee las migraciones, que es donde está escrito lo que
    cualquier despliegue va a tener.
    """
    establecimiento = _constante("config.js", "ESTABLECIMIENTO_ID")

    sql = "\n".join(
        archivo.read_text(encoding="utf-8")
        for archivo in sorted(MIGRACIONES.glob("*.sql"))
    )

    # Las filas de `menu_items` escriben el establecimiento en la segunda
    # columna: `(id, establecimiento_id, ...`.
    filas = re.findall(
        rf"^\s*\(\s*\d+\s*,\s*{establecimiento}\s*,", sql, re.MULTILINE
    )

    assert filas, (
        f"`CONFIG.ESTABLECIMIENTO_ID` vale {establecimiento} y ninguna "
        "migración le inserta productos. La portada se vería vacía sin que "
        "nada fallara: la API responde 200 con lista vacía, que es una "
        "respuesta válida del contrato."
    )
