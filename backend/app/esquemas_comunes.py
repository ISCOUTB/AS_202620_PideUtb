"""Esquemas de la frontera HTTP que no pertenecen a ningún contexto.

Viven fuera de los módulos de dominio a propósito: la forma de un error HTTP no
es conocimiento de Catálogo, de Pedidos ni de Pagos, y meterla en cualquiera de
ellos obligaría a los otros dos a importarla cruzando una frontera de contexto
(ADR-0001).

La forma que se declara aquí es la que el framework produce, no la que sería
ideal. Migrar a `application/problem+json` (RFC 9457) es deseable pero sería un
cambio incompatible: ver `docs/api/politica-versionado.md` §3, regla I-11.

`ErrorDeValidacion` se declara explícitamente en cada ruta en lugar de dejar
que el framework improvise la suya. El esquema automático marca `detail` como
opcional aunque la respuesta siempre lo trae, y un contrato que promete menos
de lo que cumple es tan inexacto como uno que promete de más.
"""
from typing import Literal

from pydantic import BaseModel


class EstadoDependencia(BaseModel):
    """Resultado de sondear una dependencia concreta.

    `tipo` existe para que la respuesta no se pueda malinterpretar: saber que
    el almacenamiento respondió no dice nada si no se sabe que hoy es memoria
    del proceso y no una base de datos gestionada.
    """

    estado: Literal["ok", "caido"]
    tipo: str
    latencia_ms: float
    detalle: str | None = None


class EstadoServicio(BaseModel):
    """Respuesta de la sonda de vida cuando **todo** lo sondeado responde.

    `status` es `Literal["ok"]` y sigue siéndolo. El estado degradado viaja en
    `ServicioNoDisponible`, un esquema distinto bajo el código `503`, y no como
    un valor más de este `enum`: añadirlo aquí sería la regla **I-8** de
    `docs/api/politica-versionado.md` —un cliente cuyo `if status === "ok"`
    funcionaba empezaría a caer en la rama equivocada sin cambiar una línea.
    """

    status: Literal["ok"]
    dependencias: dict[str, EstadoDependencia]


class ServicioNoDisponible(BaseModel):
    """Respuesta del `503`: alguna dependencia no responde.

    Lleva `dependencias` con el mismo formato que el `200` para que quien
    diagnostica no tenga que leer dos estructuras distintas según el resultado,
    justo en el momento en que menos ganas tiene de leer documentación.
    """

    status: Literal["no_disponible"]
    dependencias: dict[str, EstadoDependencia]


class ResumenOperacion(BaseModel):
    """Latencias observadas para una operación."""

    muestras: int
    p50_ms: float
    p95_ms: float
    max_ms: float


class Metricas(BaseModel):
    """Lo que devuelve `/metricas`.

    `ventana_maxima` se publica junto a los datos a propósito: un percentil sin
    su ventana no es interpretable, y quien lo lea necesita saber que son las
    últimas N peticiones de **este** proceso y no un histórico.
    """

    ventana_maxima: int
    operaciones: dict[str, ResumenOperacion]


class ErrorDeNegocio(BaseModel):
    """Cuerpo de los errores 4xx de negocio (401, 404, 409)."""

    detail: str


class DetalleDeValidacion(BaseModel):
    """Una entrada del informe de validación del framework."""

    loc: list[str | int]
    msg: str
    type: str


class ErrorDeValidacion(BaseModel):
    """Cuerpo del 422: el cuerpo o los parámetros no cumplen el esquema."""

    detail: list[DetalleDeValidacion]
