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
    ("brasa", "crema", 4.5, "es tinta: enlaces, precios en promoción, el título"),
    ("brasa", "papel", 4.5, "la misma tinta sobre tarjeta"),
    ("brasa-viva", "crema", 4.5, "acento, y aun así cae sobre el fondo"),
    ("verde-canje", "crema", 4.5, "el verde como tinta"),
    ("ambar", "ambar-niebla", 4.5, "la etiqueta de la franja de promoción"),
    ("error", "error-fondo", 4.5, "el texto del aviso de error"),
]

#: (texto blanco encima de, mínimo, dónde)
SOBRE_COLOR = [
    ("brasa", 4.5, "los botones primarios y el botón central de la barra"),
    ("brasa-hundida", 4.5, "esos mismos botones, pulsados"),
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
