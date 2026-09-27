"""El chequeo de salud responde según lo que sondea.

Lo que se prueba aquí no es que `/health` devuelva `200` —eso lo haría también
un `return {"status": "ok"}`—, sino que **el código HTTP cambia cuando una
dependencia cae**. Un chequeo que nunca puede fallar no informa de nada, y la
única forma de demostrar que este sí puede es romperlo a propósito.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.esquemas_comunes import EstadoDependencia
from app.main import app

client = TestClient(app)


def test_health_responde_ok_con_las_dependencias_que_sondeo():
    respuesta = client.get("/health")
    cuerpo = respuesta.json()

    assert respuesta.status_code == 200
    assert cuerpo["status"] == "ok"

    # El catálogo es la única dependencia que hoy existe y se sondea de verdad.
    assert cuerpo["dependencias"]["catalogo"]["estado"] == "ok"


def test_health_declara_el_tipo_real_de_cada_dependencia():
    """El chequeo no puede disfrazar memoria de base de datos.

    Es la prueba de la regla que da sentido al módulo: se reporta lo que hay,
    no lo que se querría tener. El día que la migración a Supabase ocurra, este
    `memoria` tendrá que cambiar aquí y en `docs/violaciones.md` (V-09), y esta
    prueba obliga a que ese cambio sea consciente.
    """
    dependencias = client.get("/health").json()["dependencias"]

    assert dependencias["catalogo"]["tipo"] == "memoria"


def test_health_devuelve_503_cuando_una_dependencia_esta_caida():
    caida = EstadoDependencia(
        estado="caido", tipo="postgresql", latencia_ms=3000.0, detalle="ConnectTimeout"
    )

    with patch("app.salud.sondas_activas", return_value={"base_de_datos": lambda: caida}):
        respuesta = client.get("/health")

    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "no_disponible"
    assert cuerpo["dependencias"]["base_de_datos"]["detalle"] == "ConnectTimeout"


def test_una_sonda_que_revienta_no_tumba_el_chequeo_entero():
    """Una sonda rota se reporta como caída, no propaga su excepción.

    Si la excepción subiera, el chequeo devolvería `500` sin decir qué
    dependencia falló, y perderíamos el diagnóstico de todas las demás.
    """

    def sonda_rota():
        raise RuntimeError("driver mal configurado")

    sondas = {"catalogo": lambda: EstadoDependencia(estado="ok", tipo="memoria", latencia_ms=0.1),
              "rota": sonda_rota}

    with patch("app.salud.sondas_activas", return_value=sondas):
        respuesta = client.get("/health")

    assert respuesta.status_code == 503
    dependencias = respuesta.json()["dependencias"]
    assert dependencias["rota"]["estado"] == "caido"
    # La dependencia sana sigue diagnosticada pese al fallo de la otra.
    assert dependencias["catalogo"]["estado"] == "ok"


def test_el_catalogo_vacio_cuenta_como_caida():
    """Responder sin datos es un fallo, no un éxito.

    Es el modo de fallo silencioso más peligroso del sistema: el sitio pintaría
    una carta vacía y el usuario concluiría que no hay comida, no que algo está
    roto. Con esto, la plataforma saca el servicio de rotación.
    """
    with patch("app.menu.repository.buscar_por_establecimiento", return_value=[]):
        respuesta = client.get("/health")

    assert respuesta.status_code == 503
    assert respuesta.json()["dependencias"]["catalogo"]["detalle"] == "el catalogo respondio vacio"
