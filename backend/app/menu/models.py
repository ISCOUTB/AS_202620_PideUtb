"""Entidades internas del contexto Catálogo (módulo `menu`).

Estos modelos no salen del contexto: otro módulo que necesite datos del
catálogo los pide a `menu.service`, que responde con los tipos de
`menu.contracts` (lenguaje publicado).

`establecimiento_id` es solo una **referencia**: el dueño de los datos del
establecimiento es el contexto Cuentas (ADR-0002). Catálogo no guarda su
nombre, ubicación ni horario.
"""
from pydantic import BaseModel


class ItemMenu(BaseModel):
    """Producto ofrecido por un establecimiento."""

    id: int
    establecimiento_id: int
    nombre: str
    precio: float
    disponible: bool = True
