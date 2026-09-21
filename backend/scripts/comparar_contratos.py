"""Clasifica las diferencias entre dos versiones del contrato OpenAPI.

Responde una sola pregunta: **¿un cliente escrito contra la versión anterior,
sin tocarlo, sigue funcionando?** Cada regla implementada aquí tiene su entrada
en `docs/api/politica-versionado.md` §3, con el mismo identificador (`I-1`…),
para que la documentación y el código no puedan divergir en silencio.

Existe porque las herramientas genéricas no conocen la dirección del dato. Un
`enum` al que se le añade un valor es compatible si el cliente lo *envía* e
incompatible si el cliente lo *recibe* (política §3.1), y esa distinción
depende de si el esquema cuelga de `requestBody` o de `responses`.

Uso como comando:

    python scripts/comparar_contratos.py ANTERIOR.yaml NUEVO.yaml

Termina con código 1 si encuentra al menos un cambio incompatible.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

Direccion = Literal["peticion", "respuesta"]

METODOS_HTTP = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

#: Profundidad máxima al recorrer esquemas anidados. Protege frente a esquemas
#: recursivos (`$ref` a sí mismos), que son válidos en OpenAPI.
PROFUNDIDAD_MAXIMA = 25


@dataclass(frozen=True)
class Cambio:
    """Una diferencia entre dos contratos, ya clasificada."""

    regla: str
    compatible: bool
    ubicacion: str
    descripcion: str

    def __str__(self) -> str:
        marca = "compatible  " if self.compatible else "INCOMPATIBLE"
        return f"[{marca}] {self.regla} · {self.ubicacion}\n              {self.descripcion}"


# --------------------------------------------------------------------------
# Resolución de referencias
# --------------------------------------------------------------------------

def _seguir_referencia(documento: dict, referencia: str) -> Any | None:
    """Nodo al que apunta una referencia interna, o `None` si no se puede seguir.

    Devuelve `None` en dos casos distintos que comparten consecuencia: una
    referencia a otro archivo —que saldría del alcance de este contrato— y una
    referencia que no resuelve dentro del documento.
    """
    if not referencia.startswith("#/"):
        return None

    destino: Any = documento
    for parte in referencia[2:].split("/"):
        parte = parte.replace("~1", "/").replace("~0", "~")
        if not isinstance(destino, dict) or parte not in destino:
            return None
        destino = destino[parte]

    return destino


def resolver(documento: dict, nodo: Any) -> Any:
    """Sigue los `$ref` internos hasta llegar a un nodo concreto.

    Si una referencia no se puede seguir, se devuelve el nodo tal como estaba:
    comparar dos `$ref` sin resolver es preferible a fallar, porque el objetivo
    es informar de diferencias y no validar el documento — de eso se encarga
    Spectral en el pipeline.
    """
    visitados: set[str] = set()

    while isinstance(nodo, dict) and "$ref" in nodo:
        referencia = nodo["$ref"]
        if referencia in visitados:
            break  # ciclo de referencias: el esquema se refiere a sí mismo

        visitados.add(referencia)
        destino = _seguir_referencia(documento, referencia)
        if destino is None:
            break

        nodo = destino

    return nodo


def operaciones(documento: dict) -> dict[tuple[str, str], dict]:
    """Devuelve `{(ruta, metodo): operacion}` de todo el contrato."""
    encontradas: dict[tuple[str, str], dict] = {}
    for ruta, item in (documento.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for metodo, operacion in item.items():
            if metodo.lower() in METODOS_HTTP and isinstance(operacion, dict):
                encontradas[(ruta, metodo.lower())] = operacion
    return encontradas


def _cuerpo_json(documento: dict, operacion: dict) -> dict | None:
    cuerpo = resolver(documento, operacion.get("requestBody") or {})
    contenido = (cuerpo or {}).get("content") or {}
    medio = contenido.get("application/json")
    if not medio:
        return None
    return resolver(documento, medio.get("schema") or {})


def _respuestas_json(documento: dict, operacion: dict) -> dict[str, dict | None]:
    """`{codigo: esquema}` para cada respuesta declarada."""
    resultado: dict[str, dict | None] = {}
    for codigo, respuesta in (operacion.get("responses") or {}).items():
        respuesta = resolver(documento, respuesta)
        contenido = (respuesta or {}).get("content") or {}
        medio = contenido.get("application/json")
        resultado[str(codigo)] = (
            resolver(documento, medio.get("schema") or {}) if medio else None
        )
    return resultado


# --------------------------------------------------------------------------
# Comparación de esquemas
# --------------------------------------------------------------------------

def _tipos(esquema: dict) -> set[str]:
    """Normaliza `type`, que en OpenAPI 3.1 puede ser lista (`[string, null]`)."""
    tipo = esquema.get("type")
    if tipo is None:
        return set()
    if isinstance(tipo, list):
        return {str(t) for t in tipo}
    return {str(tipo)}


def _comparar_esquema(
    doc_viejo: dict,
    doc_nuevo: dict,
    viejo: Any,
    nuevo: Any,
    ubicacion: str,
    direccion: Direccion,
    profundidad: int = 0,
) -> list[Cambio]:
    if profundidad > PROFUNDIDAD_MAXIMA:
        return []

    viejo = resolver(doc_viejo, viejo)
    nuevo = resolver(doc_nuevo, nuevo)
    if not isinstance(viejo, dict) or not isinstance(nuevo, dict):
        return []

    cambios: list[Cambio] = []
    cambios += _comparar_tipos(viejo, nuevo, ubicacion, direccion)
    cambios += _comparar_enum(viejo, nuevo, ubicacion, direccion)
    if direccion == "peticion":
        cambios += _comparar_restricciones(viejo, nuevo, ubicacion)
    cambios += _comparar_propiedades(
        doc_viejo, doc_nuevo, viejo, nuevo, ubicacion, direccion, profundidad
    )

    if "items" in viejo and "items" in nuevo:
        cambios += _comparar_esquema(
            doc_viejo, doc_nuevo, viejo["items"], nuevo["items"],
            f"{ubicacion}[]", direccion, profundidad + 1,
        )

    return cambios


def _comparar_tipos(
    viejo: dict, nuevo: dict, ubicacion: str, direccion: Direccion
) -> list[Cambio]:
    tipos_viejos, tipos_nuevos = _tipos(viejo), _tipos(nuevo)
    if not tipos_viejos or not tipos_nuevos or tipos_viejos == tipos_nuevos:
        return []

    # `null` aparte: que una respuesta empiece a poder venir vacía rompe al
    # lector aunque el tipo base no haya cambiado.
    if direccion == "respuesta" and "null" in tipos_nuevos and "null" not in tipos_viejos:
        return [Cambio(
            regla="I-5",
            compatible=False,
            ubicacion=ubicacion,
            descripcion=(
                "la respuesta ahora puede ser `null` y antes no; un cliente que "
                "no comprueba nulos falla al leerla"
            ),
        )]

    if tipos_nuevos < tipos_viejos and direccion == "respuesta":
        return [Cambio(
            regla="I-5",
            compatible=True,
            ubicacion=ubicacion,
            descripcion=f"la respuesta se restringe de {sorted(tipos_viejos)} a {sorted(tipos_nuevos)}",
        )]

    return [Cambio(
        regla="I-5",
        compatible=False,
        ubicacion=ubicacion,
        descripcion=f"el tipo cambia de {sorted(tipos_viejos)} a {sorted(tipos_nuevos)}",
    )]


def _comparar_enum(
    viejo: dict, nuevo: dict, ubicacion: str, direccion: Direccion
) -> list[Cambio]:
    """Aplica la asimetría de la política §3.1 según hacia dónde viaja el dato."""
    if "enum" not in viejo or "enum" not in nuevo:
        return []

    valores_viejos = {repr(v) for v in viejo["enum"]}
    valores_nuevos = {repr(v) for v in nuevo["enum"]}
    quitados = valores_viejos - valores_nuevos
    anadidos = valores_nuevos - valores_viejos
    cambios: list[Cambio] = []

    if quitados:
        cambios.append(Cambio(
            regla="I-7",
            compatible=direccion == "respuesta",
            ubicacion=ubicacion,
            descripcion=(
                f"desaparecen los valores {sorted(quitados)}; "
                + ("el cliente los enviaba y ahora serán rechazados"
                   if direccion == "peticion"
                   else "el cliente dejará de recibirlos, lo que no lo rompe")
            ),
        ))

    if anadidos:
        cambios.append(Cambio(
            regla="I-8",
            compatible=direccion == "peticion",
            ubicacion=ubicacion,
            descripcion=(
                f"aparecen los valores {sorted(anadidos)}; "
                + ("ningún cliente los enviaba todavía"
                   if direccion == "peticion"
                   else "el cliente recibirá un valor que no sabe interpretar")
            ),
        ))

    return cambios


def _comparar_restricciones(viejo: dict, nuevo: dict, ubicacion: str) -> list[Cambio]:
    """Detecta I-9: lo que antes se aceptaba y ahora se rechaza."""
    cambios: list[Cambio] = []

    #: (palabra clave, ¿estrechar es hacerlo más pequeño?)
    numericas = [("maximum", True), ("maxLength", True), ("maxItems", True),
                 ("minimum", False), ("minLength", False), ("minItems", False)]

    for clave, estrechar_es_menor in numericas:
        antes, ahora = viejo.get(clave), nuevo.get(clave)
        if antes is None or ahora is None or antes == ahora:
            if antes is None and ahora is not None:
                cambios.append(Cambio(
                    regla="I-9",
                    compatible=False,
                    ubicacion=ubicacion,
                    descripcion=f"aparece la restricción `{clave}: {ahora}`, que antes no existía",
                ))
            continue

        estrecha = (ahora < antes) if estrechar_es_menor else (ahora > antes)
        cambios.append(Cambio(
            regla="I-9",
            compatible=not estrecha,
            ubicacion=ubicacion,
            descripcion=(
                f"`{clave}` pasa de {antes} a {ahora}: "
                + ("se rechazan peticiones que antes eran válidas"
                   if estrecha else "se aceptan más peticiones que antes")
            ),
        ))

    antes, ahora = viejo.get("pattern"), nuevo.get("pattern")
    if antes != ahora and ahora is not None:
        cambios.append(Cambio(
            regla="I-9",
            compatible=False,
            ubicacion=ubicacion,
            descripcion=(
                f"el `pattern` cambia de {antes!r} a {ahora!r}; no se puede "
                "demostrar automáticamente que el nuevo acepte todo lo anterior"
            ),
        ))

    return cambios


def _propiedades_retiradas(
    nombres: set[str], requeridos_viejos: set[str],
    ubicacion: str, direccion: Direccion,
) -> list[Cambio]:
    """Campos que el contrato anterior declaraba y el nuevo ya no."""
    if direccion == "peticion":
        return [
            Cambio(
                regla="I-2", compatible=True, ubicacion=f"{ubicacion}.{nombre}",
                descripcion="el campo deja de aceptarse en la petición; se ignorará si se envía",
            )
            for nombre in sorted(nombres)
        ]

    return [
        Cambio(
            regla="I-2",
            compatible=nombre not in requeridos_viejos,
            ubicacion=f"{ubicacion}.{nombre}",
            descripcion=(
                "desaparece de la respuesta un campo requerido; el cliente que lo "
                "lee encontrará la clave ausente"
                if nombre in requeridos_viejos
                else "desaparece de la respuesta un campo opcional"
            ),
        )
        for nombre in sorted(nombres)
    ]


def _propiedades_anadidas(
    nombres: set[str], requeridos_nuevos: set[str],
    ubicacion: str, direccion: Direccion,
) -> list[Cambio]:
    """Campos que aparecen y que el contrato anterior no declaraba."""
    cambios: list[Cambio] = []

    for nombre in sorted(nombres):
        obligatorio_nuevo = direccion == "peticion" and nombre in requeridos_nuevos
        if obligatorio_nuevo:
            descripcion = "aparece un campo requerido nuevo; el cliente no lo envía y será rechazado"
        elif direccion == "peticion":
            descripcion = "aparece un campo opcional nuevo en la petición"
        else:
            descripcion = "aparece un campo nuevo en la respuesta; el lector tolerante lo ignora"

        cambios.append(Cambio(
            regla="I-4",
            compatible=not obligatorio_nuevo,
            ubicacion=f"{ubicacion}.{nombre}",
            descripcion=descripcion,
        ))

    return cambios


def _garantias_cambiadas(
    propiedades_viejas: dict, propiedades_nuevas: dict,
    requeridos_viejos: set[str], requeridos_nuevos: set[str],
    ubicacion: str, direccion: Direccion,
) -> list[Cambio]:
    """Campos que siguen existiendo pero cambian de obligatorios a opcionales o al revés.

    Es el caso más fácil de pasar por alto al revisar un contrato a ojo: el
    campo sigue ahí, con el mismo nombre y el mismo tipo, y solo cambia la
    promesa sobre él.
    """
    if direccion == "peticion":
        return [
            Cambio(
                regla="I-3", compatible=False, ubicacion=f"{ubicacion}.{nombre}",
                descripcion="un campo que era opcional pasa a ser obligatorio",
            )
            for nombre in sorted(requeridos_nuevos - requeridos_viejos)
            if nombre in propiedades_viejas
        ]

    return [
        Cambio(
            regla="I-2", compatible=False, ubicacion=f"{ubicacion}.{nombre}",
            descripcion=(
                "la respuesta deja de garantizar el campo: sigue declarado pero ya "
                "no es obligatorio, y el cliente lo lee sin comprobar"
            ),
        )
        for nombre in sorted(requeridos_viejos - requeridos_nuevos)
        if nombre in propiedades_nuevas
    ]


def _comparar_propiedades(
    doc_viejo: dict,
    doc_nuevo: dict,
    viejo: dict,
    nuevo: dict,
    ubicacion: str,
    direccion: Direccion,
    profundidad: int,
) -> list[Cambio]:
    propiedades_viejas = viejo.get("properties") or {}
    propiedades_nuevas = nuevo.get("properties") or {}
    if not propiedades_viejas and not propiedades_nuevas:
        return []

    requeridos_viejos = set(viejo.get("required") or [])
    requeridos_nuevos = set(nuevo.get("required") or [])
    cambios: list[Cambio] = []

    cambios += _propiedades_retiradas(
        set(propiedades_viejas) - set(propiedades_nuevas),
        requeridos_viejos, ubicacion, direccion,
    )
    cambios += _propiedades_anadidas(
        set(propiedades_nuevas) - set(propiedades_viejas),
        requeridos_nuevos, ubicacion, direccion,
    )
    cambios += _garantias_cambiadas(
        propiedades_viejas, propiedades_nuevas,
        requeridos_viejos, requeridos_nuevos, ubicacion, direccion,
    )

    for nombre in sorted(set(propiedades_viejas) & set(propiedades_nuevas)):
        cambios += _comparar_esquema(
            doc_viejo, doc_nuevo,
            propiedades_viejas[nombre], propiedades_nuevas[nombre],
            f"{ubicacion}.{nombre}", direccion, profundidad + 1,
        )

    return cambios


# --------------------------------------------------------------------------
# Comparación de operaciones
# --------------------------------------------------------------------------

def _comparar_operacion(
    doc_viejo: dict, doc_nuevo: dict, clave: tuple[str, str],
    viejo: dict, nuevo: dict,
) -> list[Cambio]:
    ruta, metodo = clave
    etiqueta = f"{metodo.upper()} {ruta}"
    cambios: list[Cambio] = []

    cuerpo_viejo = _cuerpo_json(doc_viejo, viejo)
    cuerpo_nuevo = _cuerpo_json(doc_nuevo, nuevo)
    if cuerpo_viejo is not None and cuerpo_nuevo is not None:
        cambios += _comparar_esquema(
            doc_viejo, doc_nuevo, cuerpo_viejo, cuerpo_nuevo,
            f"{etiqueta} · petición", "peticion",
        )

    respuestas_viejas = _respuestas_json(doc_viejo, viejo)
    respuestas_nuevas = _respuestas_json(doc_nuevo, nuevo)

    for codigo in sorted(set(respuestas_viejas) - set(respuestas_nuevas)):
        cambios.append(Cambio(
            regla="I-10",
            compatible=False,
            ubicacion=f"{etiqueta} · {codigo}",
            descripcion="deja de declararse un código de respuesta que el cliente maneja",
        ))

    for codigo in sorted(set(respuestas_viejas) & set(respuestas_nuevas)):
        esquema_viejo, esquema_nuevo = respuestas_viejas[codigo], respuestas_nuevas[codigo]
        if esquema_viejo is not None and esquema_nuevo is None:
            cambios.append(Cambio(
                regla="I-11",
                compatible=False,
                ubicacion=f"{etiqueta} · {codigo}",
                descripcion="la respuesta deja de emitir `application/json`",
            ))
            continue
        if esquema_viejo is None or esquema_nuevo is None:
            continue
        cambios += _comparar_esquema(
            doc_viejo, doc_nuevo, esquema_viejo, esquema_nuevo,
            f"{etiqueta} · {codigo}", "respuesta",
        )

    return cambios


def comparar(viejo: dict, nuevo: dict) -> list[Cambio]:
    """Compara dos contratos y devuelve cada diferencia ya clasificada."""
    operaciones_viejas = operaciones(viejo)
    operaciones_nuevas = operaciones(nuevo)
    cambios: list[Cambio] = []

    for clave in sorted(set(operaciones_viejas) - set(operaciones_nuevas)):
        cambios.append(Cambio(
            regla="I-1",
            compatible=False,
            ubicacion=f"{clave[1].upper()} {clave[0]}",
            descripcion="desaparece una operación que el contrato anterior ofrecía",
        ))

    for clave in sorted(set(operaciones_nuevas) - set(operaciones_viejas)):
        cambios.append(Cambio(
            regla="I-1",
            compatible=True,
            ubicacion=f"{clave[1].upper()} {clave[0]}",
            descripcion="aparece una operación nueva; nadie dependía de ella",
        ))

    for clave in sorted(set(operaciones_viejas) & set(operaciones_nuevas)):
        cambios += _comparar_operacion(
            viejo, nuevo, clave, operaciones_viejas[clave], operaciones_nuevas[clave]
        )

    return cambios


def incompatibles(cambios: list[Cambio]) -> list[Cambio]:
    return [c for c in cambios if not c.compatible]


#: Raíz del repositorio. Los contratos que este comando compara viven dentro.
RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[2]

#: Un contrato es un documento de datos, nunca un ejecutable.
EXTENSIONES_DE_CONTRATO = {".yaml", ".yml", ".json"}


def cargar(ruta: str | Path) -> dict:
    """Lee un contrato, comprobando antes que la ruta sea legítima.

    Este módulo se invoca desde la línea de comandos y desde el pipeline, donde
    los argumentos pueden venir de una plantilla o de una automatización. Sin
    esta comprobación, un `../../..` en el argumento convertiría una
    herramienta de comparación en un lector arbitrario de archivos con los
    permisos del runner de CI, que tiene acceso al repositorio entero.

    Se valida la ruta **ya resuelta**, no la que llega: comprobar la cadena
    antes de resolverla es justo lo que esquivan las travesías de directorio.
    """
    destino = Path(ruta).resolve()

    if destino.suffix.lower() not in EXTENSIONES_DE_CONTRATO:
        raise ValueError(
            f"'{destino.name}' no parece un contrato: se esperaba "
            f"{sorted(EXTENSIONES_DE_CONTRATO)}."
        )

    if not destino.is_relative_to(RAIZ_DEL_REPOSITORIO):
        raise ValueError(
            f"'{destino}' está fuera del repositorio. Esta herramienta solo "
            "compara contratos versionados aquí."
        )

    return yaml.safe_load(destino.read_text(encoding="utf-8"))


def _principal(argumentos: list[str]) -> int:
    if len(argumentos) != 2:
        print(__doc__)
        return 2

    cambios = comparar(cargar(argumentos[0]), cargar(argumentos[1]))
    rotos = incompatibles(cambios)

    if not cambios:
        print("Sin diferencias entre los dos contratos.")
        return 0

    print(f"{len(cambios)} diferencia(s), {len(rotos)} incompatible(s):\n")
    for cambio in sorted(cambios, key=lambda c: (c.compatible, c.ubicacion)):
        print(cambio)

    if rotos:
        print(
            f"\nHay {len(rotos)} cambio(s) incompatible(s). Requieren subir la "
            "versión MAYOR y publicar la API bajo un prefijo de ruta nuevo "
            "(docs/api/politica-versionado.md §2)."
        )
        return 1

    print("\nTodos los cambios son compatibles: basta con subir la versión MENOR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_principal(sys.argv[1:]))
