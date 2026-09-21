"""Bus de eventos en proceso.

Implementa el canal `pideutb.pedidos.pagados` declarado en
[`docs/api/asyncapi.yaml`](../../docs/api/asyncapi.yaml). El transporte es
deliberadamente trivial —un diccionario y una lista— porque el sistema es un
monolito modular y no hay un broker desplegado.

Lo que importa no es el transporte sino las tres propiedades que este módulo
garantiza, que son las que distinguen una publicación asíncrona de una llamada
síncrona disfrazada (ver [ADR-0003](../../docs/adr/0003-estrategia-integracion.md)):

1. **El publicador no conoce a sus suscriptores.** No los recibe por parámetro
   ni los importa; se registran por su cuenta.
2. **El publicador no espera un resultado.** `publicar` devuelve cuántos
   manejadores se invocaron, nunca qué decidieron.
3. **Un suscriptor que falla no afecta al publicador ni a los demás.** Si el
   panel del establecimiento revienta, el cobro ya ocurrido sigue siendo válido.

La tercera es la razón de que exista este archivo en vez de llamar directamente
a la función del suscriptor: sin aislamiento de fallos volvería el acoplamiento
temporal por la puerta de atrás.

Cuando el panel se convierta en un desplegable aparte, cambia la implementación
de `publicar`; los mensajes y sus garantías no cambian, porque están en el
contrato y no aquí.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

_LOG = logging.getLogger(__name__)

Manejador = Callable[[dict[str, Any]], None]

#: Canal declarado en asyncapi.yaml → `channels.pedidos-pagados.address`.
CANAL_PEDIDO_PAGADO = "pideutb.pedidos.pagados"

_suscriptores: dict[str, list[Manejador]] = {}


def suscribir(canal: str, manejador: Manejador) -> None:
    """Registra un manejador para un canal."""
    _suscriptores.setdefault(canal, []).append(manejador)


def publicar(canal: str, mensaje: dict[str, Any]) -> int:
    """Entrega el mensaje a los suscriptores y devuelve a cuántos se entregó.

    Un manejador que lanza una excepción se registra y se ignora: el hecho
    publicado ya ocurrió y no se deshace porque a alguien le siente mal.
    """
    entregados = 0

    # Instantánea inmutable de los suscriptores: un manejador puede
    # suscribir a otro mientras se reparte el evento, y modificar la lista
    # durante su propio recorrido es un error silencioso.
    for manejador in tuple(_suscriptores.get(canal, ())):
        try:
            manejador(mensaje)
        except Exception:  # noqa: BLE001 — aislar al publicador es el objetivo
            _LOG.exception(
                "Un suscriptor de '%s' falló. El evento se considera publicado "
                "de todas formas.", canal,
            )
        else:
            entregados += 1

    return entregados


def limpiar() -> None:
    """Vacía el registro. Solo para aislar pruebas entre sí."""
    _suscriptores.clear()
