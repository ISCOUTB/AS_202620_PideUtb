"""Frontera HTTP del contexto Pagos.

Contiene los dos extremos del sistema: la operación síncrona que el frontend
invoca y el punto de entrada asíncrono que invoca la pasarela. Están en el
mismo archivo porque pertenecen al mismo contexto, no porque se parezcan.
"""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.pagos import service
from app.pagos.esquemas_api import (
    AcuseDeEventoResponse,
    EventoPagoRequest,
    EventoSimuladoRequest,
    IniciarPagoRequest,
    IntentoPagoResponse,
)

router = APIRouter(prefix="/v1/pagos", tags=["pagos"])


@router.post(
    "/intentos",
    status_code=201,
    responses={404: {"model": ErrorDeNegocio}, 409: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Inicia el cobro de un pedido.",
)
def iniciar_intento(datos: IniciarPagoRequest) -> IntentoPagoResponse:
    try:
        intento = service.iniciar_intento(datos.pedido_id, datos.metodo)
    except service.PedidoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.PedidoNoCobrableError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return IntentoPagoResponse.desde_contrato(intento)


@router.post(
    "/eventos",
    status_code=202,
    responses={401: {"model": ErrorDeNegocio}, 404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Recibe la confirmación de la pasarela (webhook).",
)
async def recibir_evento(
    evento: EventoPagoRequest,
    request: Request,
    x_firma_evento: Annotated[str | None, Header(alias="X-Firma-Evento")] = None,
) -> AcuseDeEventoResponse:
    """Punto de entrada asíncrono.

    Responde `202` y no `200` de forma deliberada: PideUTB acusa recibo del
    evento, no afirma que todo el efecto de negocio haya concluido. Prometer lo
    segundo obligaría a hacer el trabajo completo dentro del manejador y
    aumentaría la probabilidad de superar el plazo de la pasarela, provocando
    reintentos que no hacían falta.

    La firma se verifica sobre el cuerpo **en crudo**, no sobre el modelo ya
    validado: firmar la reserialización de un objeto compararía nuestra versión
    del mensaje con la firma del original, y cualquier diferencia de formato
    —orden de claves, espacios— invalidaría eventos legítimos.
    """
    if not service.firma_valida(await request.body(), x_firma_evento):
        raise HTTPException(status_code=401, detail="Firma del evento ausente o inválida")

    try:
        pedido, duplicado = service.procesar_evento(
            evento.referencia_pago, evento.estado_pago
        )
    except service.ReferenciaDesconocidaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.PedidoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return AcuseDeEventoResponse(
        recibido=True,
        pedido_id=pedido.pedido_id,
        estado=pedido.estado,
        duplicado=duplicado,
    )


@router.post(
    "/simulador/{referencia_pago}",
    status_code=202,
    include_in_schema=False,
    summary="Hace de pasarela cuando no hay pasarela.",
)
def simular_evento(
    referencia_pago: str, datos: EventoSimuladoRequest
) -> AcuseDeEventoResponse:
    """Existe solo donde `PIDEUTB_URL_PASARELA_SIMULADA` esté definida.

    **Fuera de la documentación a propósito** (`include_in_schema=False`): no
    es parte del contrato que el frontend consume, es un doble del sistema
    externo. Publicarla la congelaría en una versión y obligaría a mantenerla.

    Sin la variable responde `404`, el mismo código que daría una ruta que no
    existe. Es deliberado: un `403` confirmaría que la ruta está ahí y solo
    hace falta la configuración adecuada.
    """
    try:
        pedido, duplicado = service.simular_evento(referencia_pago, datos.estado_pago)
    except service.PasarelaSimuladaApagadaError:
        raise HTTPException(status_code=404, detail="Not Found")
    except service.ReferenciaDesconocidaError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return AcuseDeEventoResponse(
        recibido=True,
        pedido_id=pedido.pedido_id,
        estado=pedido.estado,
        duplicado=duplicado,
    )
