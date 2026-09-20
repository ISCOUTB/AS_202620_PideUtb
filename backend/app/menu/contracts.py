"""Lenguaje publicado del contexto Catálogo.

Único tipo del catálogo que puede cruzar la frontera del contexto.
Separarlo del modelo interno (`menu.models`) permite que las entidades
internas evolucionen sin arrastrar a los módulos consumidores, y evita que
el modelo de Catálogo se filtre dentro de Pedidos.

No es una capa anticorrupción: entre dos contextos internos y estables no
se justifica el coste de un traductor completo (ver ADR-0002). Es un
contrato publicado, que es la versión proporcionada de la misma idea.

**No confundir con el contrato de API.** Este tipo es la frontera hacia los
otros contextos *dentro* del proceso; `docs/api/openapi.yaml` es la frontera
hacia el mundo exterior. Son dos superficies negociadas distintas, con dos
públicos distintos, y por eso pueden evolucionar a ritmos distintos: la forma
que se publica por HTTP vive en `menu.esquemas_api`.
"""
from pydantic import BaseModel, Field


class ItemDisponible(BaseModel):
    """Lo que Pedidos necesita saber de un ítem para poder venderlo."""

    item_id: int
    establecimiento_id: int
    nombre: str
    precio_centavos: int = Field(ge=0)
    disponible: bool
