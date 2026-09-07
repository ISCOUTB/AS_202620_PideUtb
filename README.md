# PideUTB

Pide UTB es una plataforma web para realizar pedidos de comida dentro del campus universitario. Permite consultar menús y precios, realizar pedidos, gestionar pagos mediante una pasarela en ambiente Sandbox y recibir un código para verificar y recoger las compras de forma rápida y organizada.

## Arquitectura

El backend sigue un estilo de **monolito modular**, organizado por módulos de dominio (`pedidos`, `menu`, `pagos`, `usuarios`). La decisión, sus alternativas y consecuencias están documentadas en:

- [`arc42.md`](arc42.md) — sección 4, estrategia de solución.
- [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) — matriz comparativa de estilos evaluados.
- [`docs/adr/0001-estilo-arquitectonico.md`](docs/adr/0001-estilo-arquitectonico.md) — ADR con la decisión formal.
- [`docs/c4/`](docs/C4/) — diagramas C4 (contexto, contenedores y módulos) como código Mermaid.

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

El repositorio incluye la prueba base (`tests/test_health.py`) que verifica que la aplicación arranca y que el endpoint de salud responde correctamente, y ahora también `tests/test_pedidos.py`, que cubre el corte vertical ejecutable descrito más abajo.

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py        # Punto de entrada de la aplicación FastAPI
│   ├── pedidos/        # Módulo de dominio: pedidos (implementado — corte vertical)
│   ├── menu/            # Módulo de dominio: menú (implementado — lectura)
│   ├── pagos/           # Módulo de dominio: pagos (vacío, próxima entrega)
│   └── usuarios/        # Módulo de dominio: usuarios/autenticación (vacío, próxima entrega)
├── tests/
│   ├── test_health.py  # Prueba automatizada base
│   └── test_pedidos.py # Prueba del corte vertical (crear pedido)
├── requirements.txt
└── pytest.ini

docs/
├── adr/                     # Architecture Decision Records
├── c4/                      # Diagramas C4 (contexto, contenedores, módulos) en Mermaid
├── aspectos.md
├── comparativa-arquitectura.md
└── ia.md
```

## Corte vertical ejecutable

Esta entrega implementa un flujo de negocio completo de punta a punta
que cruza dos módulos (`pedidos` y `menu`), para demostrar que la
arquitectura de monolito modular funciona en la práctica y no solo en
el papel. El diagrama de secuencia está en
[`arc42.md` §6](arc42.md#6-vista-de-tiempo-de-ejecución-runtime).

**Flujo:** un usuario (estudiante o profesor) crea un pedido indicando el establecimiento y
el ítem de menú que quiere. `pedidos.service` valida el ítem llamando
únicamente a la función pública `menu.service.obtener_item()` — nunca
accede al repositorio de `menu` directamente — calcula el total y
guarda el pedido.

### Probarlo manualmente

Con el servidor corriendo (ver "Cómo arrancar el backend"):

```bash
curl -X POST http://127.0.0.1:8000/pedidos \
  -H "Content-Type: application/json" \
  -d '{"establecimiento_id": 1, "item_id": 1, "cantidad": 2}'
```

Respuesta esperada (`201 Created`):

```json
{
  "id": 1,
  "establecimiento_id": 1,
  "item_id": 1,
  "nombre_item": "Arepa de huevo",
  "cantidad": 2,
  "total": 8000,
  "estado": "pendiente_pago"
}
```

Con un ítem que no existe (`item_id: 999`) responde `404`. Con un
ítem no disponible (`item_id: 3`, seed de ejemplo) responde `409`.

### Probarlo con la suite automatizada

```bash
pytest tests/test_pedidos.py -v
```

Cubre el caso exitoso y los dos casos de error (ítem no encontrado /
no disponible), que corresponden al escenario **ESC-01** de
`arc42.md` §10.2 (fila de Usabilidad en `docs/aspectos.md`, columna
"Prueba").

> **Nota:** los repositorios de `menu` y `pedidos` usan datos en
> memoria en esta entrega (ver comentarios `TODO(supabase)` en el
> código) para tener el corte vertical ejecutable sin depender de
> credenciales de Supabase. La interfaz de `repository.py` ya está
> pensada para cambiar la implementación sin tocar `service.py` ni
> `router.py`.
