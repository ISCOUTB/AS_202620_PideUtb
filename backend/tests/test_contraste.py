"""Los contrastes de la paleta se vuelven a calcular en cada construcción.

`sitio/estilos.css` lleva desde la semana 7 una tabla de relaciones de
contraste en sus comentarios, con la regla de que ningún color se usa como
tinta sin medirlo. La regla era buena. Lo que faltaba era alguien que la
comprobara: los números eran texto, y el texto no se entera cuando el color
cambia.

Y estuvo a punto de costar caro. Al pasar el fondo de blanco a crema,
`--verde-tinta` —documentado y medido en 4,81:1 **sobre blanco**, cierto—
quedaba en 4,48:1 sobre el fondo nuevo, por debajo del mínimo AA. El comentario
seguía diciendo la verdad sobre una superficie que ya no existía.

Eso es lo que esta prueba impide: **cambiar un fondo invalida los contrastes de
todo lo que va encima**, y nadie lo nota mirando la pantalla, porque la
diferencia entre 4,48 y 4,50 no se ve. Se ve el día que alguien no puede leer un
precio al sol.

### Qué comprueba

1. **Los pares que de verdad se pintan**, contra el umbral que les toca.
2. **Que los números escritos en los comentarios sean esos números.** Un
   comentario que miente es peor que ninguno, porque el siguiente que lea el
   archivo confiará en él.

### Qué NO comprueba

Que el color esté *usado* donde dice. Eso lo diría un análisis del CSS entero, y
el valor de esta prueba está en los números, no en el inventario.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
HOJA = RAIZ / "sitio" / "estilos.css"


def _luminancia(hexa: str) -> float:
    """Luminancia relativa según WCAG 2.1."""
    crudo = hexa.lstrip("#")
    if len(crudo) == 3:
        crudo = "".join(c * 2 for c in crudo)
    canales = [int(crudo[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lineales = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in canales
    ]
    return 0.2126 * lineales[0] + 0.7152 * lineales[1] + 0.0722 * lineales[2]


def contraste(a: str, b: str) -> float:
    """La relación entre dos colores. Simétrica, como la define el estándar."""
    la, lb = _luminancia(a), _luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


def _paleta() -> dict[str, str]:
    """Los colores declarados en el primer `:root` de la hoja.

    Solo el primero: `pasarela.css` y las consultas de medios redefinen algunos
    tokens, y mezclarlos daría una paleta que no existe en ninguna pantalla.
    """
    texto = HOJA.read_text(encoding="utf-8")
    bloque = re.search(r":root\s*\{(.*?)\n\}", texto, re.S)
    assert bloque, "no se encontró el bloque `:root` de sitio/estilos.css"

    return {
        nombre: valor.lower()
        for nombre, valor in re.findall(
            r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})\s*;", bloque.group(1)
        )
    }


BLANCO = "#ffffff"

#: (tinta, superficie, mínimo, por qué ese mínimo)
#:
#: 4,5 es el mínimo AA para texto normal; 3,0 el de texto grande y elementos de
#: interfaz. Donde se pide 7,0 es porque el token se usa para el cuerpo del
#: texto, y ahí vale la pena AAA.
PARES = [
    ("carbon", "crema", 7.0, "es el texto del cuerpo, sobre el fondo de la página"),
    ("carbon", "papel", 7.0, "y también sobre las tarjetas"),
    ("carbon-medio", "crema", 4.5, "texto secundario"),
    ("carbon-medio", "papel", 4.5, "texto secundario sobre tarjeta"),
    ("carbon-tenue", "crema", 4.5, "metadatos y notas al pie"),
    ("carbon-tenue", "papel", 4.5, "metadatos sobre tarjeta"),
    ("azul", "crema", 4.5, "es tinta: enlaces, precios en promoción, el título"),
    ("azul", "papel", 4.5, "la misma tinta sobre tarjeta"),
    ("verde-canje", "crema", 4.5, "el verde como tinta"),
    ("ambar", "ambar-niebla", 4.5, "la etiqueta de la franja de promoción"),
    ("ambar", "ambar-niebla", 4.5, "y el título de la advertencia del código"),
    ("carbon", "ambar-niebla", 7.0, "el cuerpo de esa misma advertencia"),
    ("carbon-medio", "crema-hundido", 4.5, "el estado, en la pastilla del billete"),
    ("error", "error-fondo", 4.5, "el texto del aviso de error"),
]

#: (texto blanco encima de, mínimo, dónde)
SOBRE_COLOR = [
    ("azul", 4.5, "los botones primarios y el botón central de la barra"),
    ("azul-hundido", 4.5, "esos mismos botones, pulsados"),
    ("verde-canje", 4.5, "el billete del código de canje"),
    ("ambar", 4.5, "cualquier etiqueta con tinta blanca"),
    ("carbon", 4.5, "la chapa con la cantidad del carrito"),
]


@pytest.mark.parametrize("tinta,superficie,minimo,donde", PARES)
def test_la_tinta_se_lee_sobre_su_superficie(tinta, superficie, minimo, donde):
    paleta = _paleta()
    for nombre in (tinta, superficie):
        assert nombre in paleta, (
            f"`--{nombre}` ya no está en la paleta. Si se renombró, esta prueba "
            "tiene que renombrarlo también: si no, dejaría de comprobar un "
            "contraste sin que nadie se entere."
        )

    medido = contraste(paleta[tinta], paleta[superficie])

    assert medido >= minimo, (
        f"`--{tinta}` ({paleta[tinta]}) sobre `--{superficie}` "
        f"({paleta[superficie]}) da {medido:.2f}:1 y necesita {minimo}:1 — "
        f"{donde}."
    )


@pytest.mark.parametrize("fondo,minimo,donde", SOBRE_COLOR)
def test_el_texto_blanco_se_lee_sobre_los_fondos_fuertes(fondo, minimo, donde):
    paleta = _paleta()
    assert fondo in paleta, f"`--{fondo}` ya no está en la paleta"

    medido = contraste(BLANCO, paleta[fondo])

    assert medido >= minimo, (
        f"Texto blanco sobre `--{fondo}` ({paleta[fondo]}) da {medido:.2f}:1 y "
        f"necesita {minimo}:1 — {donde}."
    )


# ---------------------------------------------------------------------------
# Y que los comentarios no mientan
# ---------------------------------------------------------------------------

#: Cómo se lee cada forma de anotar una relación en los comentarios.
#:
#: Por defecto se mide contra `--crema`, que es lo que dice el encabezado de la
#: sección: «Las tres relaciones son contra --crema, que es donde caen».
_FORMAS = (
    (re.compile(r"con blanco encima"), lambda paleta, color: contraste(BLANCO, color)),
    (re.compile(r"sobre blanco"), lambda paleta, color: contraste(color, BLANCO)),
    (
        re.compile(r"sobre `?--([a-z-]+)`?"),
        None,  # se resuelve con el grupo capturado
    ),
)


def _ratios_anotados() -> list[tuple[str, str, float, str]]:
    """(nombre, hex, ratio escrito, resto del comentario) por cada anotación."""
    texto = HOJA.read_text(encoding="utf-8")
    bloque = re.search(r":root\s*\{(.*?)\n\}", texto, re.S)
    assert bloque

    hallados = []
    patron = re.compile(
        r"--([a-z-]+):\s*(#[0-9a-fA-F]{3,6})\s*;\s*/\*\s*(\d+,\d+):1(.*?)\*/"
    )
    for nombre, hexa, ratio, resto in patron.findall(bloque.group(1)):
        hallados.append((nombre, hexa.lower(), float(ratio.replace(",", ".")), resto))
    return hallados


def test_hay_comentarios_con_relaciones_que_comprobar():
    """Si esta falla, la prueba de abajo dejó de comprobar nada.

    Es la guarda contra el modo de fallo más silencioso de una prueba que
    analiza texto: que el formato cambie, la expresión regular no encuentre nada
    y el bucle vacío pase en verde para siempre.
    """
    assert len(_ratios_anotados()) >= 4, (
        "No se encontraron relaciones de contraste anotadas en el `:root` de "
        "sitio/estilos.css. O se quitaron, o cambió el formato "
        "`--nombre: #hex;  /* N,NN:1 ... */` que esta prueba sabe leer."
    )


@pytest.mark.parametrize(
    "nombre,hexa,escrito,resto",
    _ratios_anotados(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_el_comentario_dice_la_relacion_que_es(nombre, hexa, escrito, resto):
    """Un comentario que miente es peor que ninguno.

    El siguiente que abra el archivo va a confiar en el número en vez de
    volver a medirlo — que es exactamente lo que pasó con `--verde-tinta`.
    """
    paleta = _paleta()

    if "con blanco encima" in resto:
        medido = contraste(BLANCO, paleta[nombre])
        contra = "blanco encima"
    elif "sobre blanco" in resto:
        medido = contraste(paleta[nombre], BLANCO)
        contra = "blanco"
    else:
        otro = re.search(r"sobre `?--([a-z-]+)`?", resto)
        referencia = otro.group(1) if otro else "crema"
        assert referencia in paleta, (
            f"el comentario de `--{nombre}` se mide contra `--{referencia}`, "
            "que no está en la paleta"
        )
        medido = contraste(paleta[nombre], paleta[referencia])
        contra = f"--{referencia}"

    assert round(medido, 2) == pytest.approx(escrito, abs=0.02), (
        f"El comentario de `--{nombre}` ({hexa}) dice {escrito}:1 contra "
        f"{contra}, y la cuenta da {medido:.2f}:1. Si el color cambió, el "
        "número tiene que cambiar con él."
    )


# ---------------------------------------------------------------------------
# Y que la guía tampoco mienta
# ---------------------------------------------------------------------------
#
# `docs/sistema-de-diseno.md` repite las relaciones de contraste en tablas, y es
# el documento que alguien lee antes de tocar un color. Si la hoja y la guía se
# separan, quien lea la guía diseñará contra una paleta que no existe.
#
# Esto no es hipotético ni ajeno: al escribir la versión 2.0 de esa guía, **tres
# de catorce números estaban mal** —puestos de memoria, de valores que se habían
# descartado horas antes— y pasaron la revisión a ojo sin problema. Un número de
# cuatro cifras mal copiado es invisible.
#
# Las tablas se leen por su cabecera, que dice contra qué se mide cada columna:
#
#   | Token | Valor | Sobre `--crema` | Con blanco encima | Uso |
#
# Así que la guía se puede reordenar o ampliar sin tocar esta prueba, mientras
# las cabeceras sigan diciendo la verdad.

GUIA = RAIZ / "docs" / "sistema-de-diseno.md"

#: Cómo se interpreta cada cabecera de columna.
_COMPARACIONES = {
    "con blanco encima": lambda paleta, color: contraste(BLANCO, color),
    "sobre `--crema`": lambda paleta, color: contraste(color, paleta["crema"]),
    "sobre `--papel`": lambda paleta, color: contraste(color, paleta["papel"]),
    "contraste sobre blanco": lambda paleta, color: contraste(color, BLANCO),
}


def _afirmaciones_de_la_guia() -> list[tuple[str, str, str, float]]:
    """(token, hex, contra qué, relación escrita) de cada celda con un ratio."""
    lineas = GUIA.read_text(encoding="utf-8").split("\n")
    afirmaciones: list[tuple[str, str, str, float]] = []
    cabecera: list[str] = []

    for linea in lineas:
        if not linea.startswith("|"):
            cabecera = []
            continue

        celdas = [c.strip() for c in linea.strip("|").split("|")]

        # La fila de guiones separa la cabecera del cuerpo; la anterior era la
        # cabecera.
        if set("".join(celdas)) <= set("-: "):
            continue
        if not cabecera:
            cabecera = [c.lower() for c in celdas]
            continue

        if len(celdas) != len(cabecera):
            continue

        token = re.match(r"`--([a-z-]+)`", celdas[0])
        if not token:
            continue

        hexa = re.search(r"`(#[0-9a-fA-F]{3,6})`", celdas[1]) if len(celdas) > 1 else None
        if not hexa:
            continue

        for titulo, celda in zip(cabecera, celdas):
            ratio = re.fullmatch(r"\**(\d+,\d+):1\**", celda)
            if not ratio:
                continue
            if titulo not in _COMPARACIONES:
                continue
            afirmaciones.append((
                token.group(1),
                hexa.group(1).lower(),
                titulo,
                float(ratio.group(1).replace(",", ".")),
            ))

    return afirmaciones


def test_la_guia_afirma_relaciones_que_se_pueden_comprobar():
    """La guarda contra que el formato cambie y esto deje de mirar nada."""
    assert len(_afirmaciones_de_la_guia()) >= 8, (
        "No se encontraron relaciones comprobables en las tablas de "
        "docs/sistema-de-diseno.md. O se quitaron, o cambió el formato de las "
        "cabeceras que esta prueba sabe leer: «Sobre `--crema`», «Con blanco "
        "encima», «Sobre `--papel`»."
    )


@pytest.mark.parametrize(
    "token,hexa,contra,escrito",
    _afirmaciones_de_la_guia(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_la_guia_dice_las_relaciones_que_son(token, hexa, contra, escrito):
    paleta = _paleta()

    assert token in paleta, (
        f"La guía documenta `--{token}` y la hoja ya no lo declara. Uno de los "
        "dos está desactualizado, y la hoja gana."
    )
    assert paleta[token] == hexa, (
        f"La guía dice que `--{token}` vale {hexa} y la hoja dice "
        f"{paleta[token]}."
    )

    medido = _COMPARACIONES[contra](paleta, paleta[token])

    assert round(medido, 2) == pytest.approx(escrito, abs=0.02), (
        f"La guía dice que `--{token}` ({hexa}) da {escrito}:1 «{contra}», y la "
        f"cuenta da {medido:.2f}:1."
    )


# ---------------------------------------------------------------------------
# Y el velo de la portada, que es el caso raro
# ---------------------------------------------------------------------------
#
# La portada es el único sitio de la hoja donde el texto no cae sobre un color
# sino sobre una **fotografía**, y una fotografía no tiene *un* contraste:
# tiene uno distinto en cada píxel. Medirlo no se puede.
#
# Lo que sí se puede es imponer un suelo —un velo de negro con una opacidad
# mínima— y medir ese suelo contra el peor caso que la foto podría ofrecer, que
# es un píxel blanco. Si el texto se lee sobre eso, se lee sobre cualquier cosa
# que la foto traiga debajo.
#
# Esto se va a romper el día que alguien mire la portada, piense que la carne
# se ve apagada y aclare el velo para que luzca. Es una reacción razonable, y
# acá está el número que dice hasta dónde.

BLANCO_PURO = (255, 255, 255)


def _velo() -> tuple[float, tuple[int, int, int]]:
    """La opacidad mínima del velo y el color con el que está pintado."""
    texto = HOJA.read_text(encoding="utf-8")

    opacidad = re.search(r"--velo-portada:\s*(\d+)%\s*;", texto)
    assert opacidad, (
        "`--velo-portada` ya no está en sitio/estilos.css, o cambió de "
        "formato. Es el suelo de contraste del texto sobre la foto de la "
        "portada: sin él no hay nada que medir y el texto blanco queda a lo "
        "que traiga la fotografía."
    )

    color = re.search(r"--negro-velo:\s*(\d+)\s+(\d+)\s+(\d+)\s*;", texto)
    assert color, (
        "`--negro-velo` ya no está, o dejó de escribirse en componentes "
        "(`R G B`). Se escribe así para que `rgb()` le pueda dar opacidad, y "
        "esta prueba lo lee de ahí para componer el peor caso."
    )

    return int(opacidad.group(1)) / 100, tuple(int(c) for c in color.groups())


def _componer(
    encima: tuple[int, int, int], alfa: float, debajo: tuple[int, int, int]
) -> str:
    """Un color translúcido sobre otro opaco, canal a canal, en `#hex`."""
    mezcla = tuple(round(e * alfa + d * (1 - alfa)) for e, d in zip(encima, debajo))
    return "#%02x%02x%02x" % mezcla


def test_el_velo_de_la_portada_deja_leer_el_texto_blanco():
    """El peor píxel posible de la foto, bajo el velo, contra texto blanco."""
    alfa, negro = _velo()
    peor_caso = _componer(negro, alfa, BLANCO_PURO)
    medido = contraste(BLANCO, peor_caso)

    assert medido >= 4.5, (
        f"Con el velo al {alfa:.0%}, un píxel blanco de la foto queda en "
        f"{peor_caso} y el texto blanco encima da {medido:.2f}:1, por debajo "
        "del mínimo AA de 4,5:1. O sube `--velo-portada`, o el título de la "
        "portada deja de leerse sobre las partes claras de la parrilla."
    )


def test_el_texto_de_la_portada_cae_sobre_el_velo_plano():
    """La garantía es estructural, y conviene que siga siéndolo.

    El número de arriba solo vale si **todo** el texto cae sobre el velo plano.
    Eso no se consigue calculando dónde acaba cayendo —cambia con el ancho, con
    el tamaño de letra del sistema y con lo que mida la frase— sino con la
    estructura: la portada es una rejilla de dos filas y el texto vive dentro
    de la de abajo, que lleva el velo entero.

    Si alguien quita ese envoltorio por parecerle un `div` de más, el texto
    pasa a flotar sobre el degradado y el contraste vuelve a depender de la
    suerte, sin que nada se vea distinto.
    """
    hoja = HOJA.read_text(encoding="utf-8")
    portada = (RAIZ / "sitio" / "index.html").read_text(encoding="utf-8")

    assert re.search(
        r"\.portada-velo\s*\{[^}]*background:\s*rgb\(\s*var\(--negro-velo\)\s*/\s*"
        r"var\(--velo-portada\)\s*\)",
        hoja,
    ), (
        "`.portada-velo` ya no se pinta con `rgb(var(--negro-velo) / "
        "var(--velo-portada))`. Es la capa que hace medible el contraste del "
        "título: sin ella, lo que hay debajo del texto es el degradado."
    )

    assert re.search(
        r'class="portada-velo"\s*>\s*<div class="portada-texto"', portada
    ), (
        "En sitio/index.html, `.portada-texto` ya no está dentro de "
        "`.portada-velo`. El texto blanco pasó a caer sobre el degradado, "
        "donde el contraste depende de dónde acabe cada línea."
    )


def test_el_degradado_de_la_portada_termina_en_el_mismo_velo():
    """Las dos capas se encuentran en el mismo valor, o se ve la costura.

    El degradado va `to top`, así que su parada del 0 % es la de abajo: la que
    toca el velo plano. Si deja de valer `--velo-portada`, aparece una línea
    horizontal a media foto — y, si se queda por debajo, el texto que sobresalga
    de la fila de abajo se apoya en menos negro del medido.
    """
    hoja = HOJA.read_text(encoding="utf-8")

    assert re.search(
        r"linear-gradient\(\s*to top,\s*rgb\(\s*var\(--negro-velo\)\s*/\s*"
        r"var\(--velo-portada\)\s*\)\s*0%",
        hoja,
    ), (
        "El degradado de `.portada::before` ya no arranca en "
        "`var(--velo-portada)` al 0 %. Esa parada es la que se junta con el "
        "velo plano de abajo: con otro valor, la foto enseña una costura "
        "recta donde se tocan las dos capas."
    )
