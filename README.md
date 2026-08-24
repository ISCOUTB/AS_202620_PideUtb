# PideUTB

Pide UTB es una plataforma web para realizar pedidos de comida dentro del campus universitario. Permite consultar menús y precios, realizar pedidos, gestionar pagos mediante una pasarela en ambiente Sandbox y recibir un código para verificar y recoger las compras de forma rápida y organizada.

## Arquitectura

El backend sigue un estilo de **monolito modular**, organizado por módulos de dominio (`pedidos`, `menu`, `pagos`, `usuarios`). La decisión, sus alternativas y consecuencias están documentadas en:

- [`arc42.md`](arc42.md) — sección 4, estrategia de solución.
- [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) — matriz comparativa de estilos evaluados.
- [`docs/adr/0001-estilo-arquitectonico.md`](docs/adr/0001-estilo-arquitectonico.md) — ADR con la decisión formal.

## Cómo arrancar el backend

Requiere Python 3.11 o superior.

Desde la carpeta `backend/`, con un solo comando (crea el entorno, instala dependencias y levanta el servidor):

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload
```

En Windows (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload
```

El servidor queda disponible en `http://127.0.0.1:8000`. Podés verificar que arrancó correctamente visitando `http://127.0.0.1:8000/health`, que debe responder `{"status": "ok"}`.

## Cómo correr las pruebas

Con el entorno virtual ya activado (ver paso anterior):

```bash
pytest
```

Actualmente el repositorio incluye una prueba base (`tests/test_health.py`) que verifica que la aplicación arranca y que el endpoint de salud responde correctamente. No incluye lógica de negocio: eso se agrega a partir de la semana 4, dentro de los paquetes de dominio ya definidos.

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py        # Punto de entrada de la aplicación FastAPI
│   ├── pedidos/        # Módulo de dominio: pedidos (vacío, semana 4)
│   ├── menu/            # Módulo de dominio: menú (vacío, semana 4)
│   ├── pagos/           # Módulo de dominio: pagos (vacío, semana 4)
│   └── usuarios/        # Módulo de dominio: usuarios/autenticación (vacío, semana 4)
├── tests/
│   └── test_health.py  # Prueba automatizada base
├── requirements.txt
└── pytest.ini
```
