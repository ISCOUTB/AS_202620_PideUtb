"""El navegador tiene que dejar al panel hablar con la API.

Este archivo existe por un fallo concreto: al añadir la autenticación, el panel
quedó roto en un navegador de verdad mientras **las 250 pruebas seguían en
verde**. La configuración de CORS no permitía la cabecera `Authorization`, así
que el navegador rechazaba en el *preflight* toda petición autenticada, y lo
que se veía en pantalla era un genérico «Failed to fetch» que no menciona CORS
por ninguna parte.

### Por qué no lo vio nada

`TestClient` no hace preflight. Habla con la aplicación por ASGI, sin navegador
y sin política de mismo origen, así que `GET /v1/pedidos` con `Authorization`
funcionaba perfectamente en la suite y fallaba en el sitio desplegado. Es un
punto ciego con una forma reconocible: **la prueba y el usuario no usan el
mismo camino**.

Lo encontró abrir la página. Estas pruebas lo convierten en algo que la
construcción detecta, usando lo único que `TestClient` sí hace llegar al
middleware: una petición `OPTIONS` con las cabeceras de preflight escritas a
mano.

### Lo que no cubre

Que los **orígenes** configurados en producción sean los correctos. Eso depende
de la variable `PIDEUTB_ORIGENES_PERMITIDOS` del entorno de despliegue —hoy el
panel de Dokploy, declarada en `deploy/compose.lab.yaml`— y no del código, así
que aquí se comprueba contra el primer origen configurado, sea cual sea.

Esa frontera importa y no es teórica: el primer defecto que la puesta en marcha
del servidor del laboratorio destapó fue justamente un CORS incompleto, que
ninguna prueba de esta suite podía ver porque `TestClient` no hace *preflight*
(arc42 §7.6).
"""
from fastapi.testclient import TestClient

from app.main import ORIGENES_PERMITIDOS, app

client = TestClient(app)

ORIGEN = ORIGENES_PERMITIDOS[0]


def _preflight(metodo: str, cabeceras: str, ruta: str = "/v1/pedidos", origen: str = ORIGEN):
    """La pregunta que el navegador hace antes de dejar pasar la petición real."""
    return client.options(
        ruta,
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": cabeceras,
        },
    )


def test_el_navegador_puede_pedir_la_cola_con_el_token():
    """El caso exacto que estaba roto."""
    respuesta = _preflight("GET", "authorization")

    assert respuesta.status_code == 200
    permitidas = respuesta.headers["access-control-allow-headers"].lower()
    assert "authorization" in permitidas


def test_el_navegador_puede_avanzar_un_pedido_con_token_y_cuerpo():
    """`POST` con `Content-Type` **y** `Authorization`, que es como viaja de verdad."""
    respuesta = _preflight(
        "POST", "authorization,content-type", ruta="/v1/pedidos/1/estado"
    )

    assert respuesta.status_code == 200
    permitidas = respuesta.headers["access-control-allow-headers"].lower()
    assert "authorization" in permitidas
    assert "content-type" in permitidas


def test_el_navegador_puede_cerrar_sesion():
    """`DELETE` entra en la 2.0.0 y no estaba en la lista de métodos."""
    respuesta = _preflight("DELETE", "authorization", ruta="/v1/sesiones")

    assert respuesta.status_code == 200
    assert "DELETE" in respuesta.headers["access-control-allow-methods"]


def test_un_origen_cualquiera_no_recibe_permiso():
    """La otra mitad: que esto no esté abierto a todo Internet.

    Sin esta prueba, poner `allow_origins=["*"]` haría pasar las tres de arriba
    y nadie se enteraría. Una configuración de CORS solo está bien si permite lo
    que debe **y** niega lo que no.
    """
    respuesta = _preflight("GET", "authorization", origen="https://sitio-cualquiera.example")

    assert "access-control-allow-origin" not in respuesta.headers


def test_no_se_permiten_credenciales_automaticas():
    """`allow_credentials` en `False` es lo que mantiene el CSRF fuera.

    El token viaja en una cabecera que el panel escribe a mano. Con las
    credenciales permitidas, el navegador adjuntaría cookies por su cuenta desde
    cualquier pestaña, y entonces haría falta defensa contra CSRF — que es
    exactamente el intercambio que ADR-0007 decidió no hacer.
    """
    respuesta = _preflight("GET", "authorization")

    assert "access-control-allow-credentials" not in respuesta.headers


def test_no_hay_comodin_de_origen():
    """Se comprueba sobre la configuración y no solo sobre una respuesta.

    Una respuesta puede salir bien por casualidad; el comodín en la lista es la
    causa, y es lo que hay que impedir que entre en un commit.
    """
    assert "*" not in ORIGENES_PERMITIDOS
