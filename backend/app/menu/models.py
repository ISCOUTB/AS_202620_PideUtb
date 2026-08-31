"""Modelos del módulo `menu`.

Estos modelos son de USO INTERNO del módulo. Si otro módulo necesita
datos de un ítem de menú, debe pedirlos a través de `menu.service`,
nunca importando estas clases directamente (ver ADR-0001).
"""
from pydantic import BaseModel


class ItemMenu(BaseModel):
    id: int
    establecimiento_id: int
    nombre: str
    precio: float
    disponible: bool = True
