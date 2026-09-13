"""Entidades internas del contexto Cuentas.

No cruzan la frontera del contexto: otros módulos piden los datos a
`usuarios.service`, que responde con los tipos de `usuarios.contracts`.
"""
from pydantic import BaseModel


class Establecimiento(BaseModel):
    """Cuenta de tipo establecimiento: un punto de venta del campus.

    El contexto Cuentas es su **único escritor** (ADR-0002). `menu` y
    `pedidos` guardan solo `establecimiento_id` como referencia y nunca
    duplican estos campos.
    """

    id: int
    nombre: str
    ubicacion: str
    horario: str
    activo: bool = True
