"""El QR que el público escanea, en SVG y sin dependencias.

    python scripts/generar_qr.py                   # la URL de producción
    python scripts/generar_qr.py https://otra.cosa # cualquier otra URL

El archivo sale siempre en `sitio/qr-demo.svg`. No se puede elegir destino: el
guion tenía un segundo argumento para la ruta de salida y era flexibilidad que
nadie pidió, con el precio de aceptar de la línea de órdenes dónde escribir.
Dibujar un QR y sobrescribir un archivo cualquiera no son la misma herramienta,
y la única forma de que no puedan confundirse es que el destino no se pueda
decir.

### Por qué está escrito acá y no se usa una biblioteca

Porque las dependencias de este repositorio van **fijadas por hash**
(`requirements-prod.txt`), y añadir una —con sus dos sha256, su entrada en
`requirements.in` y su paso por CI— para producir un único archivo SVG no sale
a cuenta. Un QR de una URL corta es un problema cerrado y bien especificado: se
resuelve una vez y no vuelve a cambiar.

Y hacía falta que fuera un guion y no un archivo suelto: si la URL de la charla
cambia, el QR se regenera en vez de buscarse quién lo hizo.

### Qué soporta, y qué no

Modo byte, nivel de corrección **Q** (recupera el 25 %), versiones 1 a 6: hasta
74 caracteres ASCII. Suficiente para cualquier URL de este proyecto y de
cualquier otro que quepa en una diapositiva.

El nivel Q y no el L es deliberado: este QR se va a proyectar o imprimir, y en
una pantalla con reflejos o un papel doblado la mitad de los módulos se leen
mal. El Q cuesta unos pocos módulos más y aguanta un cuarto del código
destruido.

No soporta las versiones 7 en adelante porque desde ahí hace falta además el
bloque de información de versión, y 74 caracteres ya son más de lo que nadie
quiere en un QR proyectado: cuantos más datos, más finos los módulos, y más
lejos tiene que estar el teléfono para enfocar.

### Salida

SVG, porque se va a proyectar e imprimir: un PNG se pixela al ampliarlo y un QR
pixelado es un QR que no lee. Sin dependencias para escribirlo —son rectángulos
y una cadena de texto— y abre en cualquier navegador.
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL_POR_DEFECTO = "https://pideutb.iscoutb.dev"
#: El único destino. Nada de lo que dibuja este guion tiene sentido fuera del
#: repositorio, así que la ruta no se parametriza: se calcula.
RAIZ = Path(__file__).resolve().parents[2]
SALIDA_POR_DEFECTO = RAIZ / "sitio" / "qr-demo.svg"

# ---------------------------------------------------------------------------
# Las tablas del estándar
# ---------------------------------------------------------------------------
#
# Están acá en crudo porque son datos, no lógica: ISO/IEC 18004 las fija y no
# se derivan de nada. Cada fila es (codewords de corrección por bloque, grupos),
# y cada grupo es (cuántos bloques, cuántos codewords de datos lleva cada uno).
#
# Solo el nivel Q, que es el único que este guion emite.
_BLOQUES_Q: dict[int, tuple[int, tuple[tuple[int, int], ...]]] = {
    1: (13, ((1, 13),)),
    2: (22, ((1, 22),)),
    3: (18, ((2, 17),)),
    4: (26, ((2, 24),)),
    5: (18, ((2, 15), (2, 16))),
    6: (24, ((4, 19),)),
}

#: Centros de los patrones de alineación. La versión 1 no lleva ninguno.
_ALINEACION: dict[int, tuple[int, ...]] = {
    1: (), 2: (6, 18), 3: (6, 22), 4: (6, 26), 5: (6, 30), 6: (6, 34),
}

#: Indicador del nivel Q dentro de la cadena de formato.
_NIVEL_Q = 0b11


# ---------------------------------------------------------------------------
# Aritmética de GF(256), que es donde vive Reed-Solomon
# ---------------------------------------------------------------------------

def _tablas_galois() -> tuple[list[int], list[int]]:
    """Logaritmos y antilogaritmos sobre el polinomio primitivo 0x11D.

    Multiplicar en este cuerpo es sumar logaritmos, igual que con los
    logaritmos de siempre. Precalcularlos convierte cada multiplicación en dos
    búsquedas y una suma.
    """
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _tablas_galois()


def _multiplicar(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _polinomio_generador(grado: int) -> list[int]:
    """(x - α⁰)(x - α¹)…(x - α^(grado-1)), expandido."""
    g = [1]
    for i in range(grado):
        siguiente = [0] * (len(g) + 1)
        for j, coeficiente in enumerate(g):
            siguiente[j] ^= coeficiente
            siguiente[j + 1] ^= _multiplicar(coeficiente, _EXP[i])
        g = siguiente
    return g


def _corregir(datos: list[int], cuantos: int) -> list[int]:
    """Los codewords de corrección de un bloque: el resto de la división."""
    generador = _polinomio_generador(cuantos)
    resto = list(datos) + [0] * cuantos
    for i in range(len(datos)):
        factor = resto[i]
        if factor:
            for j, coeficiente in enumerate(generador):
                resto[i + j] ^= _multiplicar(coeficiente, factor)
    return resto[len(datos):]


# ---------------------------------------------------------------------------
# De texto a codewords
# ---------------------------------------------------------------------------

def _version_para(texto: bytes) -> int:
    for version, (ec, grupos) in sorted(_BLOQUES_Q.items()):
        datos_cw = sum(bloques * cw for bloques, cw in grupos)
        if len(texto) <= (datos_cw * 8 - 12) // 8:
            return version
    raise ValueError(
        f"{len(texto)} caracteres no caben en un QR de nivel Q hasta la "
        "versión 6 (máximo 74). Para un QR que se va a proyectar, una URL más "
        "corta es mejor idea que una versión más alta."
    )


def _codificar(texto: bytes, version: int) -> list[int]:
    """Modo byte, con su terminador y su relleno."""
    ec_por_bloque, grupos = _BLOQUES_Q[version]
    datos_cw = sum(bloques * cw for bloques, cw in grupos)

    bits: list[int] = []

    def meter(valor: int, cuantos: int) -> None:
        for i in range(cuantos - 1, -1, -1):
            bits.append((valor >> i) & 1)

    meter(0b0100, 4)          # modo byte
    meter(len(texto), 8)      # cuenta de caracteres (8 bits hasta la versión 9)
    for byte in texto:
        meter(byte, 8)

    # Terminador: hasta cuatro ceros, y solo los que quepan.
    meter(0, min(4, datos_cw * 8 - len(bits)))

    # Hasta completar el byte.
    while len(bits) % 8:
        bits.append(0)

    # Y el relleno, que el estándar fija en estos dos valores alternados.
    relleno = (0xEC, 0x11)
    i = 0
    while len(bits) < datos_cw * 8:
        meter(relleno[i % 2], 8)
        i += 1

    codewords = [
        int("".join(str(b) for b in bits[i:i + 8]), 2)
        for i in range(0, len(bits), 8)
    ]

    # Reparto en bloques, cada uno con su corrección.
    bloques_datos: list[list[int]] = []
    bloques_ec: list[list[int]] = []
    desde = 0
    for cuantos_bloques, cw_por_bloque in grupos:
        for _ in range(cuantos_bloques):
            trozo = codewords[desde:desde + cw_por_bloque]
            desde += cw_por_bloque
            bloques_datos.append(trozo)
            bloques_ec.append(_corregir(trozo, ec_por_bloque))

    # Entrelazado: un codeword de cada bloque por vuelta. Es lo que hace que una
    # mancha sobre el código reparta el daño entre bloques en vez de destruir
    # uno entero.
    salida: list[int] = []
    for i in range(max(len(b) for b in bloques_datos)):
        for bloque in bloques_datos:
            if i < len(bloque):
                salida.append(bloque[i])
    for i in range(ec_por_bloque):
        for bloque in bloques_ec:
            salida.append(bloque[i])
    return salida


# ---------------------------------------------------------------------------
# De codewords a matriz
# ---------------------------------------------------------------------------

def _matriz_vacia(version: int) -> tuple[list[list[int | None]], list[list[bool]]]:
    """La matriz con los patrones fijos puestos, y qué celdas quedan libres."""
    lado = 17 + 4 * version
    m: list[list[int | None]] = [[None] * lado for _ in range(lado)]
    reservado = [[False] * lado for _ in range(lado)]

    def buscador(fila: int, columna: int) -> None:
        for i in range(-1, 8):
            for j in range(-1, 8):
                f, c = fila + i, columna + j
                if not (0 <= f < lado and 0 <= c < lado):
                    continue
                borde = i in (0, 6) and 0 <= j <= 6
                lado_ = j in (0, 6) and 0 <= i <= 6
                centro = 2 <= i <= 4 and 2 <= j <= 4
                m[f][c] = 1 if (borde or lado_ or centro) else 0
                reservado[f][c] = True

    buscador(0, 0)
    buscador(0, lado - 7)
    buscador(lado - 7, 0)

    # Alineación, saltando los tres rincones donde chocaría con un buscador.
    centros = _ALINEACION[version]
    for fila in centros:
        for columna in centros:
            if (fila, columna) in ((6, 6), (6, lado - 7), (lado - 7, 6)):
                continue
            for i in range(-2, 3):
                for j in range(-2, 3):
                    anillo = max(abs(i), abs(j))
                    m[fila + i][columna + j] = 1 if anillo != 1 else 0
                    reservado[fila + i][columna + j] = True

    # Las dos líneas de sincronización.
    for i in range(8, lado - 8):
        valor = 1 if i % 2 == 0 else 0
        if not reservado[6][i]:
            m[6][i], reservado[6][i] = valor, True
        if not reservado[i][6]:
            m[i][6], reservado[i][6] = valor, True

    # El módulo que siempre vale 1.
    m[lado - 8][8], reservado[lado - 8][8] = 1, True

    # Y el espacio de la cadena de formato, que se rellena al final.
    for i in range(9):
        if not reservado[8][i]:
            reservado[8][i] = True
        if not reservado[i][8]:
            reservado[i][8] = True
    for i in range(8):
        reservado[8][lado - 1 - i] = True
        reservado[lado - 1 - i][8] = True

    return m, reservado


def _colocar(m, reservado, codewords: list[int]) -> None:
    """Zigzag de dos columnas desde abajo a la derecha."""
    lado = len(m)
    bits = [(cw >> i) & 1 for cw in codewords for i in range(7, -1, -1)]
    siguiente = 0
    columna = lado - 1
    arriba = True
    while columna > 0:
        if columna == 6:   # la línea de sincronización no cuenta como columna
            columna -= 1
        filas = range(lado - 1, -1, -1) if arriba else range(lado)
        for fila in filas:
            for desplazamiento in (0, 1):
                c = columna - desplazamiento
                if reservado[fila][c]:
                    continue
                m[fila][c] = bits[siguiente] if siguiente < len(bits) else 0
                siguiente += 1
        columna -= 2
        arriba = not arriba


_MASCARAS = (
    lambda f, c: (f + c) % 2 == 0,
    lambda f, c: f % 2 == 0,
    lambda f, c: c % 3 == 0,
    lambda f, c: (f + c) % 3 == 0,
    lambda f, c: (f // 2 + c // 3) % 2 == 0,
    lambda f, c: (f * c) % 2 + (f * c) % 3 == 0,
    lambda f, c: ((f * c) % 2 + (f * c) % 3) % 2 == 0,
    lambda f, c: ((f + c) % 2 + (f * c) % 3) % 2 == 0,
)


def _penalizacion(m: list[list[int]]) -> int:
    """Las cuatro reglas del estándar, que miden lo difícil que será de leer."""
    lado = len(m)
    total = 0

    # 1: rachas de cinco o más del mismo color.
    for lineas in (m, list(zip(*m))):
        for linea in lineas:
            racha, anterior = 1, linea[0]
            for valor in linea[1:]:
                if valor == anterior:
                    racha += 1
                else:
                    if racha >= 5:
                        total += 3 + (racha - 5)
                    racha, anterior = 1, valor
            if racha >= 5:
                total += 3 + (racha - 5)

    # 2: bloques de 2×2 del mismo color.
    for f in range(lado - 1):
        for c in range(lado - 1):
            if m[f][c] == m[f][c + 1] == m[f + 1][c] == m[f + 1][c + 1]:
                total += 3

    # 3: el patrón que se confunde con un buscador.
    patrones = ([1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1])
    for lineas in (m, list(zip(*m))):
        for linea in lineas:
            linea = list(linea)
            for i in range(lado - 10):
                if linea[i:i + 11] in patrones:
                    total += 40

    # 4: desequilibrio entre claros y oscuros.
    oscuros = sum(sum(fila) for fila in m)
    porcentaje = oscuros * 100 // (lado * lado)
    total += 10 * min(abs(porcentaje - 50) // 5, abs(porcentaje - 50 + 4) // 5)

    return total


def _formato(mascara: int) -> int:
    """BCH(15,5) de los cinco bits de formato, con su XOR final."""
    datos = (_NIVEL_Q << 3) | mascara
    resto = datos << 10
    for i in range(14, 9, -1):
        if resto & (1 << i):
            resto ^= 0b10100110111 << (i - 10)
    return ((datos << 10) | resto) ^ 0b101010000010010


def _escribir_formato(m, mascara: int) -> None:
    lado = len(m)
    bits = [(_formato(mascara) >> i) & 1 for i in range(14, -1, -1)]

    # Copia junto al buscador de arriba a la izquierda.
    posiciones = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
                  (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    for bit, (f, c) in zip(bits, posiciones):
        m[f][c] = bit

    # Y la segunda, repartida entre los otros dos buscadores.
    for i in range(7):
        m[lado - 1 - i][8] = bits[i]
    for i in range(8):
        m[8][lado - 8 + i] = bits[7 + i]


def construir(texto: str) -> list[list[int]]:
    """El texto, hecho matriz de ceros y unos, ya enmascarada."""
    crudo = texto.encode("utf-8")
    version = _version_para(crudo)
    codewords = _codificar(crudo, version)

    m, reservado = _matriz_vacia(version)
    _colocar(m, reservado, codewords)

    # Se prueban las ocho máscaras y gana la de menor penalización. No es
    # opcional: el estándar lo exige, y una máscara mala produce un código que
    # algunos lectores no enfocan.
    mejor, mejor_puntos = None, None
    for indice, mascara in enumerate(_MASCARAS):
        intento = [
            [
                (celda ^ 1) if (not reservado[f][c] and mascara(f, c)) else celda
                for c, celda in enumerate(fila)
            ]
            for f, fila in enumerate(m)
        ]
        _escribir_formato(intento, indice)
        puntos = _penalizacion(intento)
        if mejor_puntos is None or puntos < mejor_puntos:
            mejor, mejor_puntos = intento, puntos

    return mejor


def a_svg(matriz: list[list[int]], titulo: str, modulo: int = 10) -> str:
    """Un rectángulo por módulo oscuro, sobre fondo blanco.

    El margen de cuatro módulos es obligatorio —la «zona tranquila»— y es lo
    primero que se recorta cuando alguien pega un QR en una diapositiva. Va
    dentro del SVG para que no se pueda perder.
    """
    lado = len(matriz)
    margen = 4
    total = (lado + margen * 2) * modulo

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" '
        f'height="{total}" viewBox="0 0 {total} {total}" role="img" '
        f'aria-label="Código QR de {titulo}">',
        f'<title>Código QR de {titulo}</title>',
        f'<rect width="{total}" height="{total}" fill="#ffffff"/>',
        '<g fill="#000000" shape-rendering="crispEdges">',
    ]
    for f, fila in enumerate(matriz):
        c = 0
        while c < lado:
            if fila[c]:
                inicio = c
                while c < lado and fila[c]:
                    c += 1
                # Un rectángulo por racha horizontal en vez de uno por módulo:
                # el archivo queda cuatro veces más chico y se dibuja igual.
                partes.append(
                    f'<rect x="{(inicio + margen) * modulo}" '
                    f'y="{(f + margen) * modulo}" '
                    f'width="{(c - inicio) * modulo}" height="{modulo}"/>'
                )
            else:
                c += 1
    partes.append("</g></svg>")
    return "\n".join(partes) + "\n"


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else URL_POR_DEFECTO
    salida = SALIDA_POR_DEFECTO

    matriz = construir(url)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(a_svg(matriz, url), encoding="utf-8")

    print(f"\n   {url}")
    print(f"   {len(matriz)}×{len(matriz)} módulos · nivel Q")
    print(f"   {salida}\n")

    # Una vista en la terminal, para no tener que abrir el archivo: dos módulos
    # por carácter usando los medios bloques de Unicode.
    for f in range(0, len(matriz), 2):
        linea = ""
        for c in range(len(matriz)):
            arriba = matriz[f][c]
            abajo = matriz[f + 1][c] if f + 1 < len(matriz) else 0
            linea += {(0, 0): " ", (1, 0): "▀", (0, 1): "▄", (1, 1): "█"}[(arriba, abajo)]
        print("    " + linea)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
