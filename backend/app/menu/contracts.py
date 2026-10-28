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

    #: **Lo que cuesta ahora.** Si hay una promoción en curso, este es el precio
    #: promocional, no el normal. Quien venda el ítem no tiene que saber nada de
    #: franjas horarias: `pedidos.service` escribe este número en la línea del
    #: pedido y acierta.
    precio_centavos: int = Field(ge=0)

    #: **Si se puede pedir ahora.** Combina las dos cosas que lo impiden: que el
    #: mostrador lo haya marcado agotado, y que esté fuera de su franja.
    disponible: bool

    imagen: str | None = None
    categoria: str | None = None
    descripcion: str | None = None

    #: Precio normal, **solo mientras la promoción está en curso**. Existe para
    #: que la carta pueda tacharlo. Nulo el resto del tiempo, y nulo también en
    #: los productos que solo se venden en promoción: ahí no hay un «antes».
    precio_antes_centavos: int | None = Field(default=None, gt=0)

    #: Hora local a la que termina la promoción en curso, `HH:MM`. Nulo si no
    #: hay ninguna. Es texto y no `time` porque su único uso es escribirlo en la
    #: pantalla.
    promocion_hasta: str | None = None
