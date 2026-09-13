"""Acceso a datos del contexto Cuentas.

Implementación en memoria para esta entrega. Solo este módulo lee y
escribe las tablas de cuentas (`usuarios_*`).
"""
from app.usuarios.models import Establecimiento

# TODO(supabase): reemplazar por la tabla `usuarios_establecimientos`.
_ESTABLECIMIENTOS_SEED = {
    1: Establecimiento(
        id=1, nombre="Cafetería Central", ubicacion="Bloque A, primer piso",
        horario="L-V 07:00-18:00", activo=True,
    ),
    2: Establecimiento(
        id=2, nombre="Kiosco Bloque D", ubicacion="Bloque D, entrada norte",
        horario="L-V 09:00-16:00", activo=True,
    ),
    3: Establecimiento(
        id=3, nombre="Punto Café", ubicacion="Biblioteca, piso 2",
        horario="cerrado temporalmente", activo=False,
    ),
}


def buscar_establecimiento_por_id(establecimiento_id: int) -> Establecimiento | None:
    return _ESTABLECIMIENTOS_SEED.get(establecimiento_id)
