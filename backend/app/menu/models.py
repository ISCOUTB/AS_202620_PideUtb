"""Entidades internas del contexto Catálogo (módulo `menu`).

Estos modelos no salen del contexto: otro módulo que necesite datos del
catálogo los pide a `menu.service`, que responde con los tipos de
`menu.contracts` (lenguaje publicado).

`establecimiento_id` es solo una **referencia**: el dueño de los datos del
establecimiento es el contexto Cuentas (ADR-0002). Catálogo no guarda su
nombre, ubicación ni horario.
"""
from pydantic import BaseModel, Field


class ItemMenu(BaseModel):
    """Producto ofrecido por un establecimiento.

    El precio es un **entero en centavos de COP** y no un decimal de punto
    flotante (`docs/violaciones.md`, V-07). La unidad va en el nombre del campo
    para que cambiarla obligue a cambiar el nombre: un `precio` que a veces son
    pesos y a veces centavos pasa todas las validaciones automáticas y
    multiplica la factura por cien
    (`docs/api/politica-versionado.md` §4).
    """

    id: int
    establecimiento_id: int
    nombre: str
    precio_centavos: int = Field(ge=0)
    disponible: bool = True
