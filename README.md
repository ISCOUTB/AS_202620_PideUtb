# PideUTB

[![CI](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml/badge.svg)](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml)

Pide UTB es una plataforma web para realizar pedidos de comida dentro del campus universitario. Permite consultar menús y precios, realizar pedidos, gestionar pagos mediante una pasarela en ambiente Sandbox y recibir un código para verificar y recoger las compras de forma rápida y organizada.

## Arquitectura

El backend sigue un estilo de **monolito modular**, organizado en cuatro **contextos delimitados**, uno por módulo de dominio: Catálogo (`menu`), Pedidos (`pedidos`), Cuentas (`usuarios`) y Pagos (`pagos`). Cada dato tiene exactamente un módulo que lo escribe; los demás lo leen o lo solicitan. La decisión, sus alternativas y consecuencias están documentadas en:

- [`docs/arc42/arc42.md`](docs/arc42/arc42.md#seccion-4) — sección 4, estrategia de solución.
- [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) — matriz comparativa de estilos evaluados.
- [`docs/adr/0001-estilo-arquitectonico.md`](docs/adr/0001-estilo-arquitectonico.md) — ADR con la decisión formal.
- [`docs/adr/0002-propiedad-datos-establecimiento.md`](docs/adr/0002-propiedad-datos-establecimiento.md) — ADR de la propiedad de `Establecimiento` y el lenguaje publicado.
- [`docs/ddd-contextos.md`](docs/ddd-contextos.md) — mapa de contextos y propiedad de datos.
- [`docs/c4/`](docs/c4/) — diagramas C4 (contexto, contenedores y módulos) como código Mermaid.

### Índice de documentación

| Documento | Contenido |
|---|---|
| [`ficha_problema.md`](ficha_problema.md) | Problema, usuarios, alcance y las dos tensiones de calidad |
| [`docs/arc42/arc42.md`](docs/arc42/arc42.md) | Documentación arc42 completa (secciones 1-12, escenarios y glosario) |
| [`docs/aspectos.md`](docs/aspectos.md) | Tabla de trazabilidad de 8 columnas: escenario → C4 → ADR → código → pruebas |
| [`docs/adr/`](docs/adr/) | Decisiones de arquitectura (ADR) con su trazabilidad |
| [`docs/c4/`](docs/c4/) | Diagramas C4 niveles 1, 2 y 3 en Mermaid |
| [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) | Matrices comparativas por criterio y por escenario |
| [`docs/linea-base.md`](docs/linea-base.md) | Línea base de rendimiento de `POST /pedidos` y su protección en CI |
| [`docs/ddd-contextos.md`](docs/ddd-contextos.md) | Contextos delimitados, lenguaje ubicuo y tabla módulo → datos con dueño único |
| [`docs/violaciones.md`](docs/violaciones.md) | Violaciones detectadas en el código y plan de corrección |
| [`correcciones.md`](correcciones.md) | Respuesta a la retroalimentación docente y estado de cada entrega |
| [`docs/ia.md`](docs/ia.md) | Uso de IA por entrega, incluido qué se rechazó y por qué |

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

El repositorio incluye la prueba base (`tests/test_health.py`) que verifica que la aplicación arranca y que el endpoint de salud responde correctamente, `tests/test_pedidos.py`, que cubre el corte vertical ejecutable descrito más abajo, y `tests/test_linea_base.py`, que protege la línea base de latencia documentada en [`docs/linea-base.md`](docs/linea-base.md).

### Integración continua

Cada push y cada pull request ejecutan la suite completa en GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) sobre Python 3.11 y
3.12. El estado del último run está en la insignia del encabezado; el historial
completo en la [pestaña Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).

CI no instala desde `requirements.txt` sino desde `requirements-ci.txt`, un lock
con versiones exactas y hashes generado con `pip-compile --generate-hashes` a
partir de `requirements.in`. Así cada build resuelve exactamente las mismas
versiones y ningún paquete ejecuta su `setup.py` al instalarse. Para regenerarlo
tras cambiar una dependencia:

```bash
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements-ci.txt requirements.in
```

### Medir la línea base de rendimiento

```bash
python scripts/medir_linea_base.py 300
```

Reporta min, p50, p95 y máximo de `POST /pedidos`. La medición de referencia y
su interpretación están en [`docs/linea-base.md`](docs/linea-base.md).

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py        # Punto de entrada de la aplicación FastAPI
│   ├── menu/            # Contexto Catálogo — dueño de ÍtemMenu
│   ├── pedidos/        # Contexto Pedidos — dueño de Pedido
│   ├── usuarios/       # Contexto Cuentas — dueño de Establecimiento
│   └── pagos/           # Contexto Pagos (vacío, próxima entrega)
├── scripts/
│   └── medir_linea_base.py # Medición de latencia de POST /pedidos
├── tests/
│   ├── test_health.py          # Prueba automatizada base
│   ├── test_pedidos.py         # Corte vertical (crear pedido)
│   ├── test_propiedad_datos.py # Dueño único entre contextos
│   ├── test_modularidad.py     # Auditoría de las reglas de dependencia
│   └── test_linea_base.py      # Regresión sobre la línea base de latencia
├── requirements.in         # Dependencias directas (rangos legibles)
├── requirements-ci.txt     # Lock con versiones exactas y hashes, usado por CI
├── requirements.txt        # Instalación local
└── pytest.ini

docs/
├── adr/                        # Architecture Decision Records
├── arc42/                      # Documentación arc42
├── c4/                         # Diagramas C4 (contexto, contenedores, módulos) en Mermaid
├── aspectos.md                 # Trazabilidad: escenario → C4 → ADR → código → pruebas
├── comparativa-arquitectura.md
├── ddd-contextos.md            # Contextos delimitados y propiedad de datos
├── violaciones.md              # Violaciones del código y plan de corrección
├── linea-base.md               # Línea base de rendimiento y su umbral en CI
└── ia.md

correcciones.md                 # Respuesta a la retroalimentación docente

.github/workflows/
└── ci.yml                      # Pipeline de pruebas
```

## Corte vertical ejecutable

Esta entrega implementa un flujo de negocio completo de punta a punta
que cruza dos módulos (`pedidos` y `menu`), para demostrar que la
arquitectura de monolito modular funciona en la práctica y no solo en
el papel. El diagrama de secuencia está en
[`arc42.md` §6](docs/arc42/arc42.md#runtime-crear-pedido).

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
[`arc42.md` §10.2](docs/arc42/arc42.md#esc-01) (fila ESC-01 de
[`docs/aspectos.md`](docs/aspectos.md), columna "Pruebas").

> **Nota:** los repositorios de `menu` y `pedidos` usan datos en
> memoria en esta entrega (ver comentarios `TODO(supabase)` en el
> código) para tener el corte vertical ejecutable sin depender de
> credenciales de Supabase. La interfaz de `repository.py` ya está
> pensada para cambiar la implementación sin tocar `service.py` ni
> `router.py`.
