"""Frontera HTTP del contexto Pagos.

Contiene los dos extremos del sistema: la operación síncrona que el frontend
invoca y el punto de entrada asíncrono que invoca la pasarela. Están en el
mismo archivo porque pertenecen al mismo contexto, no porque se parezcan.
"""
from fastapi import APIRouter, Header, HTTPException, Request

from app.esquemas_comunes import ErrorDeNegocio, ErrorDeValidacion
from app.pagos import service
from app.pagos.esquemas_api import (
    AcuseDeEventoResponse,
    EventoPagoRequest,
    IniciarPagoRequest,
    IntentoPagoResponse,
)

router = APIRouter(prefix="/v1/pagos", tags=["pagos"])


@router.post(
    "/intentos",
    status_code=201,
    response_model=IntentoPagoResponse,
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
    response_model=AcuseDeEventoResponse,
    responses={401: {"model": ErrorDeNegocio}, 404: {"model": ErrorDeNegocio}, 422: {"model": ErrorDeValidacion}},
    summary="Recibe la confirmación de la pasarela (webhook).",
)
async def recibir_evento(
    evento: EventoPagoRequest,
    request: Request,
    x_firma_evento: str | None = Header(default=None, alias="X-Firma-Evento"),
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
