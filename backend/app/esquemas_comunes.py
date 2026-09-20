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


class EstadoServicio(BaseModel):
    """Respuesta de la sonda de vida."""

    status: Literal["ok"]


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
