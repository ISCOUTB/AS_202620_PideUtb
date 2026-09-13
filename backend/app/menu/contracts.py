"""Lenguaje publicado del contexto Catálogo.

Único tipo del catálogo que puede cruzar la frontera del contexto.
Separarlo del modelo interno (`menu.models`) permite que las entidades
internas evolucionen sin arrastrar a los módulos consumidores, y evita que
el modelo de Catálogo se filtre dentro de Pedidos.

No es una capa anticorrupción: entre dos contextos internos y estables no
se justifica el coste de un traductor completo (ver ADR-0002). Es un
contrato publicado, que es la versión proporcionada de la misma idea.
"""
from pydantic import BaseModel


class ItemDisponible(BaseModel):
    """Lo que Pedidos necesita saber de un ítem para poder venderlo."""

    item_id: int
    establecimiento_id: int
    nombre: str
    precio: float
    disponible: bool
