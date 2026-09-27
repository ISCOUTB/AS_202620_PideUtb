"""Los logs son legibles por máquina y no filtran secretos.

Un log estructurado que en la práctica emite texto libre no sirve de nada, y
uno que filtra una firma es peor que no tener log. Las dos cosas se prueban
aquí porque las dos fallan en silencio: nadie se entera hasta que hace falta
buscar algo, o hasta que alguien encuentra el token.
"""
import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observabilidad import LATENCIAS, FormatoJSON, configurar_logs

client = TestClient(app)


def _linea(registro: logging.LogRecord) -> dict:
    return json.loads(FormatoJSON().format(registro))


def _registro(mensaje: str, **extra) -> logging.LogRecord:
    registro = logging.LogRecord("pideutb", logging.INFO, __file__, 1, mensaje, None, None)
    registro.__dict__.update(extra)
    return registro


def test_cada_linea_es_json_valido_con_los_campos_minimos():
    linea = _linea(_registro("peticion_atendida", request_id="abc123", duration_ms=12.5))

    # Estos cuatro campos son el contrato del log: sin ellos no se puede
    # filtrar por servicio, ordenar por tiempo ni separar errores de ruido.
    assert linea["event"] == "peticion_atendida"
    assert linea["level"] == "INFO"
    assert linea["service"] == "api"
    assert linea["timestamp"]

    assert linea["request_id"] == "abc123"
    assert linea["duration_ms"] == 12.5


def test_el_middleware_registra_una_linea_por_peticion(caplog):
    with caplog.at_level(logging.INFO, logger="pideutb"):
        client.get("/v1/menu/establecimientos/1/items")

    atendidas = [r for r in caplog.records if r.getMessage() == "peticion_atendida"]
    assert len(atendidas) == 1

    linea = _linea(atendidas[0])
    assert linea["status"] == 200
    assert linea["duration_ms"] >= 0

    # La ruta va con plantilla, no con el `1` sustituido: si no, cada
    # establecimiento produciría su propia serie y el percentil por operación
    # sería inservible.
    assert linea["path"] == "/v1/menu/establecimientos/{establecimiento_id}/items"


def test_el_log_no_contiene_la_firma_del_webhook(caplog):
    """La cabecera que autentica el webhook no puede acabar en el log.

    Es el secreto que más cerca está de ser registrado por accidente: viaja en
    cada llamada de la pasarela, y un middleware que volcara las cabeceras «para
    depurar» lo dejaría escrito en claro y conservado por la plataforma mucho
    después de que alguien lo rotara.
    """
    firma = "sha256=firma-que-no-debe-aparecer"

    with caplog.at_level(logging.INFO, logger="pideutb"):
        client.post(
            "/v1/pagos/eventos",
            headers={"X-Firma-Evento": firma},
            json={"referencia_pago": "ref-inexistente", "estado_pago": "aprobado"},
        )

    volcado = "\n".join(_linea(r) and json.dumps(_linea(r)) for r in caplog.records)
    assert firma not in volcado
    assert "X-Firma-Evento" not in volcado


def test_el_identificador_de_peticion_vuelve_en_la_respuesta():
    """Permite que quien reporta un fallo cite el identificador exacto."""
    respuesta = client.get("/health")
    assert respuesta.headers["X-Request-Id"]


def test_se_respeta_el_identificador_que_envia_el_cliente():
    """Sin esto, la traza se corta en cada salto entre servicios."""
    respuesta = client.get("/health", headers={"X-Request-Id": "traza-del-cliente"})
    assert respuesta.headers["X-Request-Id"] == "traza-del-cliente"


def test_las_metricas_reportan_la_operacion_ligada_a_esc02():
    """`POST /v1/pedidos` aparece con su p95.

    Es la parte de ESC-02 que el servidor controla. El escenario mide el
    recorrido completo del usuario en menos de 2 minutos, e incluye tiempo
    humano que no se puede instrumentar desde aquí.
    """
    LATENCIAS.limpiar()

    client.post("/v1/pedidos", json={"item_id": 1, "cantidad": 1})
    resumen = client.get("/metricas").json()

    operacion = resumen["operaciones"]["POST /v1/pedidos"]
    assert operacion["muestras"] == 1
    assert operacion["p95_ms"] > 0

    # La ventana se publica junto al dato: un percentil sin saber sobre cuántas
    # peticiones se calculó no es interpretable.
    assert resumen["ventana_maxima"] > 0


def test_la_ventana_de_latencias_no_crece_sin_limite():
    """El consumo de memoria del proceso no puede depender del tráfico."""
    from app.observabilidad import TAMANO_VENTANA, Latencias

    latencias = Latencias()
    for i in range(TAMANO_VENTANA + 500):
        latencias.registrar("GET /x", float(i))

    assert latencias.resumen()["GET /x"]["muestras"] == TAMANO_VENTANA


def test_configurar_logs_deja_un_solo_formato_en_la_salida():
    """Dos formatos conviviendo hacen ilegible el volcado de la plataforma."""
    configurar_logs("INFO")
    raiz = logging.getLogger()

    assert len(raiz.handlers) == 1
    assert isinstance(raiz.handlers[0].formatter, FormatoJSON)

    # `httpx` registra la URL completa de cada llamada saliente en INFO, que es
    # la vía más común por la que un token acaba en un log.
    assert logging.getLogger("httpx").level == logging.WARNING
