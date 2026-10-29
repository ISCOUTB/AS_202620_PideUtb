"""Borrar los pedidos entre un ensayo y el siguiente.

Existe para una cosa concreta: la charla del 3 de noviembre, donde el público
escanea un QR y pide desde su teléfono. Entre un ensayo y el siguiente —y entre
la prueba de carga y la charla— hay que dejar la cola vacía, y en el servidor
del laboratorio no hay forma de hacerlo a mano: la base no publica puertos y el
panel no da terminal (ADR-0008).

### Por qué una ruta y no un guion

Por lo mismo que `sembrar_usuario_inicial.py` corre en el arranque: en ese
servidor **no hay dónde ejecutar un guion**. Un `python scripts/...` contra
producción no es una opción, así que lo que tenga que tocar la base en marcha
tiene que entrar por HTTP.

### Por qué esto no es una puerta trasera

Tres cierres, y el orden importa:

1. **Sin `PIDEUTB_TOKEN_REINICIO_DEMO` la ruta no existe.** Responde 404, el
   mismo código que una ruta inventada. Es el patrón de
   `/v1/pagos/simulador/{ref}`, y por el mismo motivo: un 403 confirmaría que
   está ahí y que solo falta la configuración.
2. **Con la variable puesta, exige ese token en una cabecera**, comparado con
   `hmac.compare_digest`. Un `==` filtraría por su duración cuántos bytes
   acertó quien lo intenta.
3. **Fuera del contrato** (`include_in_schema=False`). No es una operación que
   el frontend consuma; publicarla la congelaría en una versión.

Lo que queda, dicho claro: **quien tenga el token puede borrar todos los
pedidos.** Para un sistema de demostración ese es el trato; en uno con pedidos
de verdad esta ruta no debería existir, y por eso el valor por defecto es que no
exista.

### Por qué toca la base en crudo

Salta los repositorios de `pedidos` y `pagos` a propósito. Borrar en masa no es
una operación de ninguno de los dos contextos —ADR-0001 los separa justamente
para que no se llamen entre ellos— y añadir un «borrá todo» a cada repositorio
metería en el dominio una operación que el dominio no tiene. Es una herramienta
de operación, vive aparte, y este módulo es el único sitio que lo hace.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app import base_de_datos

router = APIRouter(prefix="/v1/demo", tags=["demo"])

_LOG = logging.getLogger("pideutb")

#: Sin esta variable, nada de este módulo responde.
#:
#: No se llama `TOKEN` aunque sea lo evidente: una constante con ese nombre y
#: una cadena al lado la marca el análisis estático como secreto incrustado, y
#: con razón, porque desde fuera las dos cosas se ven igual. Lo que hay aquí es
#: el *nombre* de la variable de entorno; el valor nunca vive en el código.
VARIABLE_DEL_TOKEN = "PIDEUTB_TOKEN_REINICIO_DEMO"

#: El orden no es alfabético, es de dependencias. `pagos_intentos` referencia
#: `pedidos` sin `ON DELETE CASCADE`, así que va primero o PostgreSQL rechaza
#: el borrado; `pedido_lineas` sí cascadea y por eso no está en la lista.
_TABLAS = ("pagos_intentos", "pedidos")


class ReinicioResponse(BaseModel):
    """Lo que se borró, por tabla."""

    reiniciado: bool = True
    borrados: dict[str, int] = Field(
        description="Filas borradas en cada tabla.",
        examples=[{"pagos_intentos": 12, "pedidos": 10}],
    )


def _token_configurado() -> str:
    """Se lee en cada llamada y no al importar.

    Igual que el secreto de la pasarela: leerlo al importar lo congelaría al
    valor que hubiera cuando arrancó el proceso, y en el panel de despliegue las
    variables cambian sin que nadie reconstruya la imagen.
    """
    return os.getenv(VARIABLE_DEL_TOKEN, "").strip()


@router.post(
    "/reiniciar",
    include_in_schema=False,
    summary="Borra los pedidos para volver a ensayar.",
)
def reiniciar(
    x_token_demo: Annotated[str | None, Header(alias="X-Token-Demo")] = None,
) -> ReinicioResponse:
    esperado = _token_configurado()
    if not esperado:
        raise HTTPException(status_code=404, detail="Not Found")

    if not x_token_demo or not hmac.compare_digest(esperado, x_token_demo):
        # 404 y no 401, por lo mismo que arriba: con la variable puesta, un 401
        # distinguiría «la ruta existe y el token está mal» de «no existe», y
        # eso es justo lo que no queremos confirmarle a nadie.
        raise HTTPException(status_code=404, detail="Not Found")

    borrados: dict[str, int] = {}
    with base_de_datos.conexion() as conexion:
        for tabla in _TABLAS:
            with conexion.cursor() as cursor:
                cursor.execute(f"DELETE FROM {tabla}")
                borrados[tabla] = cursor.rowcount

        # La secuencia vuelve a 1 para que el primer pedido de la charla sea el
        # #1 y no el #847. Es cosmético y se nota: el número se proyecta en una
        # pantalla.
        #
        # Solo se reinicia con la tabla vacía, que acaba de quedar así dentro de
        # esta misma transacción. Si alguna vez este borrado pasa a ser parcial,
        # reiniciar la secuencia haría que el siguiente pedido chocara con uno
        # que ya existe.
        with conexion.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pedidos")
            if cursor.fetchone()[0] == 0:
                cursor.execute("ALTER SEQUENCE pedidos_id_seq RESTART WITH 1")

    _LOG.warning("demo_reiniciada", extra={"borrados": borrados})
    return ReinicioResponse(borrados=borrados)
