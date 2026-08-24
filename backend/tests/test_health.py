"""
Prueba automatizada base del esqueleto ejecutable.

No verifica lógica de negocio (todavía no existe): confirma que la
aplicación FastAPI arranca correctamente y que el endpoint de salud
responde como se espera. Sirve como punto de partida para las pruebas
que se agregarán junto con la lógica de negocio de cada módulo.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
