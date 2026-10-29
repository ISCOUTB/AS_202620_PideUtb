"""El QR de la charla tiene que leerse, y «se ve bien» no es comprobarlo.

`scripts/generar_qr.py` implementa ISO/IEC 18004 a mano, porque añadir una
dependencia fijada por hash para producir un SVG no salía a cuenta. El riesgo
de hacerlo a mano es claro: un QR mal codificado **se ve igual de bien** que uno
correcto —cuadros negros ordenados— y solo se descubre cuando doscientas
personas apuntan el teléfono y no pasa nada.

Se comprueba de dos maneras, y las dos hacen falta:

1. **Contra la tabla oficial de cadenas de formato.** Son quince bits por
   máscara, publicados en el estándar, y no se derivan de nada que este
   repositorio controle. Si el BCH(15,5) está mal, acá se ve, y se ve contra una
   fuente externa.

2. **Decodificando.** Hay un decodificador escrito al revés —lee la máscara de
   la propia cadena de formato, desenmascara, deshace el entrelazado y saca los
   bytes— y tiene que devolver el texto original. No es independiente del todo,
   porque lee el estándar igual que el codificador; lo que sí detecta es
   cualquier error de colocación, de máscara o de entrelazado, que es donde más
   fácil se equivoca uno.

Lo que ninguna de las dos cubre es una cámara de verdad. Eso está en la
checklist de ensayo, y no hay forma de automatizarlo acá.
"""
from __future__ import annotations

import pytest

from scripts.generar_qr import (
    _ALINEACION,
    _BLOQUES_Q,
    _MASCARAS,
    _formato,
    a_svg,
    construir,
)

# Las ocho cadenas de formato del nivel Q, tal como las publica el estándar.
# Copiadas de la tabla, no calculadas: si se calcularan con el mismo código que
# se quiere probar, la prueba no probaría nada.
_FORMATO_OFICIAL_Q = (
    "011010101011111",
    "011000001101000",
    "011111100110001",
    "011101000000110",
    "010010010110100",
    "010000110000011",
    "010111011011010",
    "010101111101101",
)


@pytest.mark.parametrize("mascara", range(8))
def test_la_cadena_de_formato_coincide_con_el_estandar(mascara):
    """Quince bits que no dependen de nada nuestro.

    Si el BCH o el XOR final estuvieran mal, el lector no sabría qué máscara se
    usó y el código sería ilegible aunque los datos estuvieran perfectos.
    """
    calculada = format(_formato(mascara), "015b")

    assert calculada == _FORMATO_OFICIAL_Q[mascara]


# ---------------------------------------------------------------------------
# El decodificador, escrito al revés
# ---------------------------------------------------------------------------

def _leer_mascara(matriz) -> int:
    """La máscara sale de la cadena de formato, igual que para un lector."""
    posiciones = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
                  (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    leida = "".join(str(matriz[f][c]) for f, c in posiciones)
    return _FORMATO_OFICIAL_Q.index(leida)


def _reservadas(version: int, lado: int) -> list[list[bool]]:
    """Las mismas celdas que el codificador considera ocupadas.

    Se recalcula acá en vez de importarse para que el decodificador no herede
    un error de la función que construye la matriz: si `_matriz_vacia` marcara
    mal una celda, importarla haría que el fallo se cancelara solo.
    """
    reservado = [[False] * lado for _ in range(lado)]

    for fila, columna in ((0, 0), (0, lado - 7), (lado - 7, 0)):
        for i in range(-1, 8):
            for j in range(-1, 8):
                f, c = fila + i, columna + j
                if 0 <= f < lado and 0 <= c < lado:
                    reservado[f][c] = True

    centros = _ALINEACION[version]
    for fila in centros:
        for columna in centros:
            if (fila, columna) in ((6, 6), (6, lado - 7), (lado - 7, 6)):
                continue
            for i in range(-2, 3):
                for j in range(-2, 3):
                    reservado[fila + i][columna + j] = True

    for i in range(lado):
        reservado[6][i] = True
        reservado[i][6] = True

    reservado[lado - 8][8] = True
    for i in range(9):
        reservado[8][i] = True
        reservado[i][8] = True
    for i in range(8):
        reservado[8][lado - 1 - i] = True
        reservado[lado - 1 - i][8] = True

    return reservado


def decodificar(matriz) -> str:
    """De matriz a texto, deshaciendo cada paso del codificador."""
    lado = len(matriz)
    version = (lado - 17) // 4
    mascara = _MASCARAS[_leer_mascara(matriz)]
    reservado = _reservadas(version, lado)

    # Desenmascarar y recorrer el zigzag en el mismo orden.
    bits: list[int] = []
    columna = lado - 1
    arriba = True
    while columna > 0:
        if columna == 6:
            columna -= 1
        filas = range(lado - 1, -1, -1) if arriba else range(lado)
        for fila in filas:
            for desplazamiento in (0, 1):
                c = columna - desplazamiento
                if reservado[fila][c]:
                    continue
                valor = matriz[fila][c]
                if mascara(fila, c):
                    valor ^= 1
                bits.append(valor)
        columna -= 2
        arriba = not arriba

    codewords = [
        int("".join(str(b) for b in bits[i:i + 8]), 2)
        for i in range(0, len(bits) - len(bits) % 8, 8)
    ]

    # Deshacer el entrelazado: los datos primero, bloque a bloque.
    ec_por_bloque, grupos = _BLOQUES_Q[version]
    tamanos = [cw for cuantos, cw in grupos for _ in range(cuantos)]
    bloques: list[list[int]] = [[] for _ in tamanos]
    siguiente = 0
    for i in range(max(tamanos)):
        for indice, tamano in enumerate(tamanos):
            if i < tamano:
                bloques[indice].append(codewords[siguiente])
                siguiente += 1

    datos = [cw for bloque in bloques for cw in bloque]

    # Y leer el modo byte.
    flujo = "".join(format(cw, "08b") for cw in datos)
    modo = int(flujo[:4], 2)
    assert modo == 0b0100, f"modo {modo:04b}, se esperaba byte"
    cuantos = int(flujo[4:12], 2)
    crudo = bytes(
        int(flujo[12 + i * 8:20 + i * 8], 2) for i in range(cuantos)
    )
    return crudo.decode("utf-8")


# ---------------------------------------------------------------------------
# Ida y vuelta
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "https://pideutb.iscoutb.dev",
    "https://pideutb.iscoutb.dev/",
    "A",
    "https://pideutb.iscoutb.dev/index.html?mesa=12",
    "x" * 74,
])
def test_el_qr_devuelve_lo_que_se_le_metio(texto):
    assert decodificar(construir(texto)) == texto


def test_el_qr_de_la_charla_es_de_la_version_3():
    """29×29 módulos: ni tan denso que el teléfono no enfoque, ni tan grande.

    Está fijado porque es lo que se proyecta. Si la URL creciera y saltara a una
    versión más alta, los módulos se afinan y hay que acercar el teléfono — eso
    se decide a propósito, no por accidente al editar una cadena.
    """
    matriz = construir("https://pideutb.iscoutb.dev")

    assert len(matriz) == 29
    assert all(len(fila) == 29 for fila in matriz)


def test_mas_de_74_caracteres_se_rechaza_con_un_motivo():
    with pytest.raises(ValueError, match="74"):
        construir("x" * 75)


def test_los_tres_buscadores_estan_donde_corresponde():
    """Lo que un lector busca primero. Sin esto, no hay nada que leer."""
    matriz = construir("https://pideutb.iscoutb.dev")
    lado = len(matriz)

    for fila, columna in ((0, 0), (0, lado - 7), (lado - 7, 0)):
        bloque = [matriz[fila + i][columna:columna + 7] for i in range(7)]
        assert bloque[0] == [1] * 7, f"borde superior en ({fila},{columna})"
        assert bloque[6] == [1] * 7, f"borde inferior en ({fila},{columna})"
        assert all(f[0] == 1 and f[6] == 1 for f in bloque), "lados"
        assert bloque[3][3] == 1, "centro"
        assert bloque[1][1:6] == [0, 0, 0, 0, 0], "anillo claro"


def test_el_svg_lleva_su_zona_tranquila():
    """Cuatro módulos de margen, dentro del archivo.

    Es obligatorio y es lo primero que se pierde cuando alguien recorta el QR
    para pegarlo en una diapositiva. Metido en el `viewBox`, no se puede perder.
    """
    matriz = construir("https://pideutb.iscoutb.dev")
    svg = a_svg(matriz, "prueba", modulo=10)

    lado_esperado = (29 + 8) * 10
    assert f'viewBox="0 0 {lado_esperado} {lado_esperado}"' in svg
    assert 'fill="#ffffff"' in svg


# ---------------------------------------------------------------------------
# La corrección de errores, que el round-trip no mira
# ---------------------------------------------------------------------------
#
# El decodificador de arriba ignora los codewords de corrección: saca los datos
# y ya. Así que un Reed-Solomon equivocado pasaría la ida y vuelta sin que nada
# chirriara, y después un lector de verdad descartaría el código —o peor,
# «corregiría» datos buenos hasta convertirlos en basura—.
#
# Se comprueba por la propiedad que *define* un codeword válido, que no es la
# misma cuenta que lo produce: evaluado como polinomio en α¹…α^n, un codeword
# correcto vale cero en todas. Eso es lo que calcula un lector al decidir si
# hace falta corregir algo.

def test_las_tablas_de_galois_son_consistentes():
    """α²⁵⁵ = 1, y exp y log se deshacen mutuamente.

    Si el polinomio primitivo estuviera mal, todo lo demás estaría mal de una
    forma difícil de ver: las cuentas seguirían dando números.
    """
    from scripts.generar_qr import _EXP, _LOG

    assert _EXP[0] == 1
    assert _EXP[255] == 1, "el cuerpo tiene que cerrar en 255"
    for i in range(1, 256):
        assert _EXP[_LOG[i]] == i, f"exp(log({i})) != {i}"


def _syndromes(codeword: list[int], cuantos: int) -> list[int]:
    """C(α⁰)…C(α^(cuantos-1)), con el esquema de Horner."""
    from scripts.generar_qr import _EXP, _multiplicar

    salida = []
    for i in range(cuantos):
        acumulado = 0
        for coeficiente in codeword:
            acumulado = _multiplicar(acumulado, _EXP[i]) ^ coeficiente
        salida.append(acumulado)
    return salida


@pytest.mark.parametrize("texto", [
    "https://pideutb.iscoutb.dev",
    "A",
    "x" * 74,
])
def test_cada_bloque_es_un_codeword_valido(texto):
    """Datos + corrección tienen que anularse en las raíces del generador."""
    from scripts.generar_qr import _BLOQUES_Q, _codificar, _version_para

    crudo = texto.encode()
    version = _version_para(crudo)
    ec_por_bloque, grupos = _BLOQUES_Q[version]
    entrelazado = _codificar(crudo, version)

    # Deshacer el entrelazado para recuperar los bloques tal como viajan.
    tamanos = [cw for cuantos, cw in grupos for _ in range(cuantos)]
    datos: list[list[int]] = [[] for _ in tamanos]
    siguiente = 0
    for i in range(max(tamanos)):
        for indice, tamano in enumerate(tamanos):
            if i < tamano:
                datos[indice].append(entrelazado[siguiente])
                siguiente += 1

    correccion: list[list[int]] = [[] for _ in tamanos]
    for i in range(ec_por_bloque):
        for indice in range(len(tamanos)):
            correccion[indice].append(entrelazado[siguiente])
            siguiente += 1

    assert siguiente == len(entrelazado), "sobraron o faltaron codewords"

    for indice, (bloque, ec) in enumerate(zip(datos, correccion)):
        syndromes = _syndromes(bloque + ec, ec_por_bloque)
        assert syndromes == [0] * ec_por_bloque, (
            f"el bloque {indice} de «{texto[:20]}» no es un codeword válido: "
            f"syndromes {syndromes}. Un lector lo daría por dañado."
        )
