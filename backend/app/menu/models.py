"""Entidades internas del contexto Catálogo (módulo `menu`).

Estos modelos no salen del contexto: otro módulo que necesite datos del
catálogo los pide a `menu.service`, que responde con los tipos de
`menu.contracts` (lenguaje publicado).

`establecimiento_id` es solo una **referencia**: el dueño de los datos del
establecimiento es el contexto Cuentas (ADR-0002). Catálogo no guarda su
nombre, ubicación ni horario.
"""
from datetime import time

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

    #: Ruta relativa dentro del sitio, p. ej. `imagenes/arepa.webp`. Nulo
    #: cuando el producto todavía no tiene foto: la carta muestra un marcador
    #: en vez de una imagen rota.
    imagen: str | None = None

    #: Agrupación para los filtros de la carta. Nulo = solo aparece en «Todas».
    categoria: str | None = None

    descripcion: str | None = None

    # --- Promoción por franja horaria --------------------------------------
    #
    # Lo que está aquí es la **declaración** de la promoción, no su resultado.
    # Si hoy, a esta hora, el precio es uno u otro lo decide `menu.service`:
    # el modelo no sabe qué hora es, y es mejor que no lo sepa — un modelo que
    # consulta el reloj devuelve cosas distintas en dos llamadas seguidas y
    # convierte cualquier prueba en una carrera.

    #: Precio dentro de la franja. Nulo = la franja no cambia el precio, solo
    #: decide si el producto se puede pedir.
    precio_promocional_centavos: int | None = Field(default=None, gt=0)

    #: Horas **locales de Bogotá**, no UTC. La franja es lo que el
    #: establecimiento anuncia en su cartel y no debe moverse si el servidor
    #: cambia de región.
    promocion_desde: time | None = None
    promocion_hasta: time | None = None

    #: El producto solo se puede pedir dentro de la franja. Es distinto de
    #: `disponible`, que sigue significando si el mostrador lo tiene hoy: un
    #: combo agotado a las 2:45 no está disponible aunque la franja esté
    #: abierta.
    solo_en_promocion: bool = False
