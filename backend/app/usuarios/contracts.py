"""Lenguaje publicado del contexto Cuentas.

Único tipo del contexto que puede cruzar la frontera. Separarlo del
modelo interno permite que las cuentas crezcan (credenciales, roles,
autenticación) sin arrastrar a `menu` ni a `pedidos`.
"""
from pydantic import BaseModel


class EstablecimientoPublico(BaseModel):
    """Lo que otros contextos necesitan saber de un establecimiento."""

    establecimiento_id: int
    nombre: str
    activo: bool
