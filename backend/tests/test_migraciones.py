"""Que una migración ya desplegada no cambie, y que se vea en CI y no en producción.

`scripts/migrar.py` ya lo verifica: guarda la huella de cada migración aplicada
y se niega a arrancar si el archivo cambió. Es una buena guardia y funcionó.

El problema es **dónde** funcionó. Esto pasó de verdad el 18/10/2026:

1. Un commit de reconciliación documental corrigió un comentario de
   `001_esquema_inicial.sql` — el que justificaba el punto débil del rollback
   con las copias de Supabase, plataforma que ya no se usa.
2. Las 323 pruebas pasaron. El Quality Gate pasó. El PR se fusionó.
3. El contenedor de la API entró en bucle de reinicio: la migración registrada
   ya no coincidía con el archivo, así que `migrar.py` abortaba antes de
   escuchar.
4. Traefik se quedó sin router para el host de la API y **todas** sus rutas
   devolvieron 404 durante media hora. El sitio seguía en pie, lo que hacía el
   síntoma más confuso todavía.

Nada en el repositorio avisó. La huella solo existe en la base de datos de
producción, así que la comprobación solo podía fallar allí. Es exactamente el
patrón de arc42 §7.6 —la prueba y el entorno real no recorren el mismo camino—
y esta vez costó una caída.

Estas pruebas traen la comprobación a CI fijando las huellas en el repositorio.

### Lo que esto obliga, y es la regla de verdad

Una migración de esta lista **no se edita**, y eso incluye sus comentarios: la
huella es un `sha256` del archivo entero y no distingue un comentario de un
`DROP COLUMN`. Si algo de su contenido está mal o se quedó viejo, la salida es
una migración nueva, nunca editar la que ya corrió.

Hay una consecuencia incómoda que conviene decir en voz alta: **el comentario de
`001_esquema_inicial.sql` sobre Supabase se queda ahí, desactualizado, a
propósito.** Es el único sitio del repositorio donde la documentación tiene que
seguir siendo inexacta, porque corregirla rompe producción. La corrección vive
en `arc42` §7.6 y en ADR-0008.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MIGRACIONES = RAIZ / "migraciones"

#: Huella de cada migración, con el mismo cálculo que `scripts/migrar.py`.
#:
#: Una entrada de aquí es una promesa: ese archivo ya corrió contra una base de
#: datos real y su contenido es inmutable.
#:
#: **Al añadir una migración** se añade su huella en el mismo commit. Mientras
#: no se haya desplegado se puede seguir editando —actualizando la huella cada
#: vez—, y en cuanto llega a `master` se vuelve inmutable, porque el siguiente
#: despliegue la aplica.
HUELLAS = {
    "001_esquema_inicial.sql": "b208d2d6b374a56c",
    "002_datos_semilla.sql": "2969eb1350c71cee",
    "003_autenticacion.sql": "c142a8a08753786f",
}


def _huella(sql: str) -> str:
    """El mismo cálculo que `scripts/migrar.py::_huella`.

    Se duplica a propósito en vez de importarlo: si alguien cambia el algoritmo
    allí, `test_el_calculo_sigue_siendo_el_mismo_que_usa_migrar` falla y obliga
    a decidirlo, en lugar de que las huellas fijadas aquí se recalculen solas y
    la protección desaparezca en silencio.
    """
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _leer(archivo: Path) -> str:
    """Lee la migración igual que lo hace `migrar.py`.

    `read_text` en modo texto traduce los finales de línea a `\\n`, así que la
    huella sale igual en Windows —donde el árbol de trabajo tiene CRLF— y en el
    contenedor de Linux. Sin esa traducción, estas huellas no servirían de nada
    fuera de la máquina en que se calcularon.
    """
    return archivo.read_text(encoding="utf-8")


@pytest.mark.parametrize("nombre", sorted(HUELLAS))
def test_una_migracion_desplegada_no_cambia(nombre):
    """El archivo tiene que seguir siendo byte a byte el que se aplicó.

    Si esta prueba falla, el contenedor de producción entrará en bucle de
    reinicio en el siguiente despliegue. El mensaje dice qué hacer en su lugar.
    """
    archivo = MIGRACIONES / nombre
    assert archivo.exists(), (
        f"`{nombre}` desapareció. Una migración aplicada no se borra: la base "
        "de datos sigue teniendo sus cambios, y sin el archivo nadie puede "
        "saber cuáles fueron."
    )

    actual = _huella(_leer(archivo))

    assert actual == HUELLAS[nombre], (
        f"`{nombre}` cambió: huella {actual}, esperada {HUELLAS[nombre]}.\n\n"
        "Si **ya se desplegó**, no se puede editar, y eso incluye sus "
        "comentarios: `migrar.py` compara un sha256 del archivo entero y no "
        "distingue un comentario de un `DROP COLUMN`. El cambio no se "
        "ejecutaría nunca, y el contenedor entraría en bucle de reinicio. Lo "
        "que corresponde es una migración nueva.\n\n"
        "Si **todavía no se ha desplegado** —se está escribiendo ahora— hay que "
        "actualizar su huella en `HUELLAS`, en este mismo archivo."
    )


def test_toda_migracion_del_repositorio_tiene_su_huella_fijada():
    """Una migración nueva no puede entrar sin que alguien la registre aquí.

    Sin esto, la protección solo cubriría las tres primeras: cualquier
    migración posterior quedaría editable después de desplegarse, que es
    justamente el fallo que esta suite existe para evitar.
    """
    en_disco = {p.name for p in MIGRACIONES.glob("*.sql")}
    sin_fijar = sorted(en_disco - set(HUELLAS))

    assert not sin_fijar, (
        f"Estas migraciones no tienen huella fijada: {sin_fijar}. Añadirla en "
        "`HUELLAS` es parte de añadir una migración: desde que llega a `master` "
        "es inmutable, porque el siguiente despliegue la aplica."
    )


def test_el_calculo_sigue_siendo_el_mismo_que_usa_migrar():
    """Las huellas fijadas no valen nada si `migrar.py` calcula otra cosa.

    Es la prueba que sostiene a las demás. Si alguien cambia el algoritmo allí
    —a sha512, o al archivo completo sin truncar— las huellas de arriba dejarían
    de corresponder a lo que la base registra, y esta suite pasaría en verde
    protegiendo nada.
    """
    import sys

    sys.path.insert(0, str(RAIZ))
    from scripts.migrar import _huella as huella_real

    muestra = "-- una migración de prueba\nSELECT 1;\n"

    assert huella_real(muestra) == _huella(muestra), (
        "`scripts/migrar.py::_huella` ya no calcula lo mismo que esta suite. "
        "Las huellas de `HUELLAS` corresponden al cálculo viejo, así que hay "
        "que recalcularlas — y tener en cuenta que las filas ya registradas en "
        "la base de producción siguen con el cálculo anterior: cambiar el "
        "algoritmo rompe el arranque igual que editar un archivo."
    )
