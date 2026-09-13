"""Interfaz pública del contexto Cuentas (módulo `usuarios`).

Única puerta de entrada para que `menu` y `pedidos` consulten datos de un
establecimiento. Ningún módulo accede a `usuarios.repository` ni a
`usuarios.models` directamente (ADR-0001, precisado por ADR-0002).
"""
from app.usuarios import repository
from app.usuarios.contracts import EstablecimientoPublico


def obtener_establecimiento(establecimiento_id: int) -> EstablecimientoPublico | None:
    """Devuelve los datos publicados del establecimiento, o `None`."""
    establecimiento = repository.buscar_establecimiento_por_id(establecimiento_id)
    if establecimiento is None:
        return None
    return EstablecimientoPublico(
        establecimiento_id=establecimiento.id,
        nombre=establecimiento.nombre,
        activo=establecimiento.activo,
    )


def establecimiento_esta_activo(establecimiento_id: int) -> bool:
    """Indica si el establecimiento existe y está recibiendo pedidos."""
    establecimiento = obtener_establecimiento(establecimiento_id)
    return establecimiento is not None and establecimiento.activo
