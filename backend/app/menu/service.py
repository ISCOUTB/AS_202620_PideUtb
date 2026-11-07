"""Interfaz pública del contexto Catálogo (módulo `menu`).

Responde siempre con tipos de `menu.contracts`, nunca con entidades
internas. Ver ADR-0001 (regla de comunicación) y ADR-0002 (lenguaje
publicado y propiedad de los datos de establecimiento).
"""
import logging
import os
from datetime import datetime, time
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.menu import repository
from app.menu.contracts import ItemDisponible
from app.menu.models import ItemMenu
from app.usuarios import service as cuentas_service

#: La franja de una promoción es hora local del establecimiento.
#:
#: Fija y no tomada del sistema a propósito. El contenedor corre en UTC y el
#: portátil de quien desarrolla no, así que leer la zona del entorno haría que
#: «de 2:30 a 3:30» significara dos cosas distintas en dos máquinas, y la que
#: se vería mal es producción. Lo que anuncia el cartel del mostrador es hora
#: de Bogotá, y eso no cambia aunque cambie el servidor.
_ZONA = ZoneInfo("America/Bogota")

_LOG = logging.getLogger("pideutb")

#: Los sugeridos del día, por identificador. **Para cambiarlos no hace falta
#: tocar el código:** basta poner `PIDEUTB_SUGERIDOS_DEL_DIA=108,103` en el panel
#: de despliegue. Es una variable y no una columna porque cambiar una fila en el
#: laboratorio exige escribir una migración (la base no publica puertos), y algo
#: que cambia cada día no puede pedir un PR cada día.
#:
#: Estos cuatro son platos redondos con foto, que es lo que se ve bien girando.
#: Una prueba comprueba que existan y que tengan foto.
_SUGERIDOS_POR_DEFECTO = "108,103,111,102"


class EstablecimientoNoEncontradoError(Exception):
    """El establecimiento consultado no existe en el contexto Cuentas."""


def _ahora() -> time:
    """La hora local de Bogotá."""
    return datetime.now(_ZONA).time()


@lru_cache(maxsize=1)
def _interpretar_sugeridos(crudo: str) -> frozenset[int]:
    """Los identificadores de la variable; lo que no sea un número se ignora.

    Se ignora y se registra, igual que una URL de pasarela mal pegada: un error
    al escribir la variable no puede tumbar la carta entera. Va en caché porque
    se consulta una vez por producto y el texto casi nunca cambia.
    """
    trozos = [trozo.strip() for trozo in crudo.split(",")]
    validos = {int(trozo) for trozo in trozos if trozo.isdecimal()}
    if len(validos) != len([trozo for trozo in trozos if trozo]):
        _LOG.warning("sugeridos_con_valores_ignorados", extra={"valor": crudo[:80]})
    return frozenset(validos)


def _sugeridos() -> frozenset[int]:
    """Se lee en cada llamada, para que cambiar la variable no pida reconstruir."""
    crudo = os.getenv("PIDEUTB_SUGERIDOS_DEL_DIA", "").strip()
    return _interpretar_sugeridos(crudo or _SUGERIDOS_POR_DEFECTO)


def _en_la_franja(item: ItemMenu, ahora: time) -> bool:
    """Si `ahora` cae dentro de la franja declarada del ítem.

    Los extremos: `desde` incluido, `hasta` **excluido**. A las 15:30 en punto
    la promoción ya terminó. Un intervalo medio abierto es lo que hace que dos
    franjas consecutivas no se solapen en el instante que comparten, y conviene
    decidirlo aquí y no en cada consulta.
    """
    if item.promocion_desde is None or item.promocion_hasta is None:
        return False
    return item.promocion_desde <= ahora < item.promocion_hasta


def _publicar(item: ItemMenu, ahora: time | None = None) -> ItemDisponible:
    """Traduce al lenguaje publicado **resolviendo la promoción**.

    Este es el único sitio donde una franja horaria se convierte en un precio y
    en un sí o un no. Está aquí y no en `pedidos.service` por una razón
    concreta: `crear_pedido` ya leía `precio_centavos` y `disponible` de lo que
    devuelve este módulo, así que resolviéndolo aquí **el contexto Pedidos no
    cambia ni una línea** y es imposible que la carta muestre un precio y el
    pedido cobre otro. Resolverlo en los dos sitios sería la forma más fácil de
    que se separen.

    `ahora` se puede pasar para poder probar una hora concreta sin mover el
    reloj de la máquina. En producción nadie lo pasa.
    """
    if ahora is None:
        ahora = _ahora()

    en_franja = _en_la_franja(item, ahora)

    # Un precio promocional solo existe dentro de la franja. Fuera, el precio es
    # el normal y no hay nada que tachar.
    hay_descuento = en_franja and item.precio_promocional_centavos is not None
    precio = item.precio_promocional_centavos if hay_descuento else item.precio_centavos

    # Dos cosas distintas impiden pedir: que el mostrador lo tenga agotado, y
    # que el producto solo se venda en una franja que ahora está cerrada.
    disponible = item.disponible and (not item.solo_en_promocion or en_franja)

    return ItemDisponible(
        item_id=item.id,
        establecimiento_id=item.establecimiento_id,
        nombre=item.nombre,
        precio_centavos=precio,
        disponible=disponible,
        imagen=item.imagen,
        categoria=item.categoria,
        descripcion=item.descripcion,
        precio_antes_centavos=item.precio_centavos if hay_descuento else None,
        promocion_hasta=(
            item.promocion_hasta.strftime("%H:%M")
            if en_franja and item.promocion_hasta is not None
            else None
        ),
        sugerido=item.id in _sugeridos(),
    )


def obtener_item(item_id: int) -> ItemDisponible | None:
    """Devuelve el ítem publicado si existe, o `None` si no existe.

    `pedidos.service` usa esta función para validar el ítem y conocer su
    precio y a qué establecimiento pertenece, sin saber cómo se almacena
    el catálogo.
    """
    item = repository.buscar_por_id(item_id)
    if item is None:
        return None
    return _publicar(item)


def horario_de_atencion(establecimiento_id: int) -> tuple[str | None, str | None]:
    """Apertura y cierre en `HH:MM`, o nulos si no están publicados.

    El dato es de Cuentas, su único escritor (ADR-0002). Se publica junto a la
    carta porque es la única petición que el sitio hace antes de que alguien
    elija a qué hora quiere recoger.
    """
    establecimiento = cuentas_service.obtener_establecimiento(establecimiento_id)
    if establecimiento is None or None in (
        establecimiento.hora_apertura, establecimiento.hora_cierre
    ):
        return None, None
    return (
        establecimiento.hora_apertura.strftime("%H:%M"),
        establecimiento.hora_cierre.strftime("%H:%M"),
    )


def listar_items_de_establecimiento(
    establecimiento_id: int, solo_disponibles: bool = False
) -> list[ItemDisponible]:
    """Ítems que ofrece un establecimiento.

    Distingue dos situaciones que un cliente necesita separar: el
    establecimiento **no existe** (error, `404`) y el establecimiento existe
    pero **no tiene ítems** (lista vacía, `200`). Devolver lista vacía en
    ambos casos obligaría al frontend a adivinar cuál de las dos ocurrió.

    Quién sabe si el establecimiento existe es el contexto Cuentas, su único
    escritor (ADR-0002); Catálogo lo pregunta en lugar de guardar una copia.
    """
    if cuentas_service.obtener_establecimiento(establecimiento_id) is None:
        raise EstablecimientoNoEncontradoError(
            f"El establecimiento {establecimiento_id} no existe"
        )

    items = repository.buscar_por_establecimiento(establecimiento_id)

    # El instante se toma **una vez** para toda la carta. Tomándolo por ítem,
    # una carta que se resuelva justo en el borde de la franja podría salir con
    # unos productos en promoción y otros no, y nadie sabría por qué.
    ahora = _ahora()
    publicados = [_publicar(item, ahora) for item in items]

    # Se filtra por la disponibilidad **ya resuelta**, no por la columna: fuera
    # de su franja, un producto que solo se vende en promoción tiene que
    # desaparecer de la carta igual que uno agotado.
    if solo_disponibles:
        publicados = [item for item in publicados if item.disponible]

    return publicados
