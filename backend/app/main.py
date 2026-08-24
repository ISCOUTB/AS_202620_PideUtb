"""
Punto de entrada de la aplicación PideUTB.

Este módulo solo levanta la aplicación y expone un endpoint de salud
para verificar que el esqueleto arranca correctamente. No contiene
lógica de negocio: los módulos de dominio (pedidos, menu, pagos,
usuarios) se implementarán a partir de la semana 4, siguiendo la
organización de monolito modular definida en el ADR 0001
(docs/adr/0001-estilo-arquitectonico.md).
"""

from fastapi import FastAPI

app = FastAPI(
    title="PideUTB",
    description="Sistema web para realizar pedidos de comida dentro del campus de la UTB.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """Endpoint de verificación de disponibilidad del backend."""
    return {"status": "ok"}
