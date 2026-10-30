# PideUTB

[![CI](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml/badge.svg)](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=ISCOUTB_AS_202620_PideUtb&metric=alert_status)](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb)

Pide UTB es una plataforma web para realizar pedidos de comida dentro del campus universitario. Permite consultar menús y precios, realizar pedidos, gestionar pagos mediante una pasarela en ambiente Sandbox y recibir un código para verificar y recoger las compras de forma rápida y organizada.

## Desplegado y accesible

| Pieza | URL |
|---|---|
| **Sitio** | https://pideutb.iscoutb.dev |
| **Panel del mostrador** | https://pideutb.iscoutb.dev/panel.html |
| **API** | https://api-pideutb.iscoutb.dev/docs |
| Chequeo de salud | https://api-pideutb.iscoutb.dev/health |
| Métricas | https://api-pideutb.iscoutb.dev/metricas |

```bash
curl -s https://api-pideutb.iscoutb.dev/health
```

```json
{"status":"ok","dependencias":{
  "catalogo":{"estado":"ok","tipo":"postgresql","latencia_ms":1.55,"detalle":null},
  "base_de_datos":{"estado":"ok","tipo":"postgresql","latencia_ms":0.4,"detalle":null}}}
```

Ese `tipo` es deliberado: el chequeo **declara lo que hay** en vez de reportar
`ok` sobre lo que no comprobó. Cuando el estado vivía en memoria del proceso
([V-09](docs/violaciones.md), cerrada en S8) decía `memoria` en voz alta; ahora
dice `postgresql` porque eso es lo que hay, y con la latencia medida de verdad
contra la base.

Ese **~1 ms** es la consecuencia más visible de
[ADR-0008](docs/adr/0008-despliegue-en-el-servidor-del-laboratorio.md): la base
dejó de ser un servicio gestionado al otro lado de Internet y pasó a ser un
contenedor vecino. Antes eran 33 ms y 16 ms.

**El sitio y la API están en orígenes distintos**, así que el panel hace
peticiones entre orígenes y depende de que la lista de orígenes permitidos sea
correcta. Se intentó unificarlos bajo un solo host para eliminar esa dependencia
y la plataforma no lo admite; el razonamiento completo está en ADR-0008 §3.

La evidencia completa —infraestructura declarada, las tres señales de operación
y lo que **no** está hecho— está en
[`docs/evidencia-s8.md`](docs/evidencia-s8.md).
La de la semana 9 —generación verificada, auditoría de erosión y de dependencias—
en [`docs/evidencia-s9.md`](docs/evidencia-s9.md).
La de la semana 10 —autenticación del panel, y los seis defectos que las
correcciones destaparon— en [`docs/evidencia-s10.md`](docs/evidencia-s10.md).
La de la semana 11 —fallos parciales, idempotencia y la decisión de no extraer
ningún servicio— en [`docs/evidencia-s11.md`](docs/evidencia-s11.md).
La de la semana 12 —consistencia por operación, la caché que se descartó con un
número y un margen de calidad que estaba agotado sin que nadie lo hubiera
escrito— en [`docs/evidencia-s12.md`](docs/evidencia-s12.md).
La de la semana 13 —modelo STRIDE, y dos defensas correctas que juntas dejan
tumbar el servicio con catorce peticiones por segundo— en
[`docs/evidencia-s13.md`](docs/evidencia-s13.md).
La de la semana 14 —la evaluación contra los umbrales, donde medir convirtió una
preferencia en un defecto: ESC-03 no se cumplía— en
[`docs/evidencia-s14.md`](docs/evidencia-s14.md).

**Ya no hay arranque en frío.** El despliegue anterior dormía el servicio tras
15 minutos sin tráfico y tardaba 42,4 s en volver, lo que incumplía
[ESC-03](docs/arc42/arc42.md#esc-03) —cuyo umbral son 10 s— en el caso más
habitual: el mostrador que abre el panel al empezar el turno. Los contenedores
del servidor del laboratorio no duermen.

Por qué se eligió aquello primero y qué lo cambió:
[ADR-0004](docs/adr/0004-plataforma-de-despliegue.md),
[ADR-0008](docs/adr/0008-despliegue-en-el-servidor-del-laboratorio.md) y
[`docs/comparacion-despliegue.md`](docs/comparacion-despliegue.md).

## Evidencia de la entrega, con citas

Cada criterio apunta a un archivo y una línea concretos. El detalle, con los
fragmentos reproducidos, está en [`docs/evidencia-s7.md`](docs/evidencia-s7.md)
— 12 KB, pensado para leerse de una sola vez.

| Criterio | Evidencia citada |
|---|---|
| Contrato ejecutable versionado | [`docs/api/openapi.yaml`](docs/api/openapi.yaml) `openapi: 3.1.0`, `info.version: 2.0.0` · [`asyncapi.yaml`](docs/api/asyncapi.yaml) `3.0.0` |
| Rutas y esquemas, no solo endpoints | 10 `paths` con `content`/`schema`; `components.schemas` con `required` y tipos |
| **Correspondencia contrato ↔ código** | 9 paths ↔ 10 operaciones: `menu/router.py:18,22,35` · `pedidos/router.py:18,22,42,55,78` · `pagos/router.py:18,22,40` · `main.py:103,117`. Lo verifica `test_contrato_api.py` en cada push |
| Versión declarada con historial | `info.version: 1.1.0`; [`historial/`](docs/api/historial/) congela **1.0.0 y 1.1.0**. El salto de MINOR se justifica en [§6 de la política](docs/api/politica-versionado.md): la forma intuitiva de hacer real el chequeo de salud era la regla **I-8**, y el diseño cambió por eso |
| Prueba de contrato presente | `test_contrato_api.py` · `test_compatibilidad_contrato.py` · `test_expectativas_consumidor.py` — **20 casos negativos** |
| **El pipeline la ejecuta** | [`ci.yml:109-48`](.github/workflows/ci.yml) `pytest -v` · `ci.yml:181-106` Spectral · `ci.yml:196-120` oasdiff |
| **Falla ante un cambio incompatible** | [Run #22](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35557297196) — `failure`. Cayeron oasdiff y las pruebas; **Spectral pasó**, porque lo roto era la promesa y no la forma |
| ADR ligado a un escenario | [ADR-0003](docs/adr/0003-estrategia-integracion.md) ← ESC-05, con las dos alternativas descartadas |
| **arc42 §6 con los flujos** | [`arc42.md`](docs/arc42/arc42.md) **líneas 391-644**: 6 flujos etiquetados, 4 diagramas de secuencia, 9 modos de fallo |
| **C4 N2 con protocolo y formato** | [`nivel2-contenedores.md`](docs/c4/nivel2-contenedores.md) **líneas 27-34**: 7 relaciones, cada una con protocolo · formato · modo |
| Tabla de aspectos de 8 columnas | [`docs/aspectos.md`](docs/aspectos.md) — 6 filas, ninguna celda de Código o Pruebas vacía |
| **SonarCloud** | [Panel público](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb) · Quality Gate **`OK`** · workflow en `ci.yml:265-193` |

Las citas por número de línea las protege
[`backend/tests/test_evidencia.py`](backend/tests/test_evidencia.py): si un
archivo se reordena, la construcción falla y obliga a actualizarlas. Una cita
caducada afirma algo falso con apariencia de precisión.

## Contrato de API

La API se define **antes que el código** (API-first). El contrato versionado es
la fuente única de verdad de la superficie del sistema, y el pipeline falla si
el código deja de cumplirlo.

| Contrato | Describe | Versión |
|---|---|---|
| [`docs/api/openapi.yaml`](docs/api/openapi.yaml) | Superficie **síncrona**: menú, pedidos, inicio del cobro y sondas de operación (OpenAPI 3.1) | **1.1.0** |
| [`docs/api/asyncapi.yaml`](docs/api/asyncapi.yaml) | Canales **asíncronos**: confirmación de pago y evento interno (AsyncAPI 3.0) | **1.0.0** |
| [`docs/api/politica-versionado.md`](docs/api/politica-versionado.md) | Qué cambios son compatibles, cuáles no, y cómo se avisa a los consumidores | — |
| [`docs/api/historial/`](docs/api/historial/) | Versiones congeladas: la referencia contra la que se mide la compatibilidad | — |
| [`contracts/consumidor-web.yaml`](contracts/consumidor-web.yaml) | Qué campos y códigos usa de verdad el frontend | — |

Guía completa —las tres capas de validación, cómo generar un cliente y cómo
reproducir un run en rojo— en [`docs/api/README.md`](docs/api/README.md).

Por qué hay dos archivos y no uno:
[ADR-0003](docs/adr/0003-estrategia-integracion.md) — el sistema tiene dos tipos
de integración con modos de fallo distintos, y describirlos con el mismo formato
ocultaría la diferencia que importa.

## Arquitectura

El backend sigue un estilo de **monolito modular**, organizado en cuatro **contextos delimitados**, uno por módulo de dominio: Catálogo (`menu`), Pedidos (`pedidos`), Cuentas (`usuarios`) y Pagos (`pagos`). Cada dato tiene exactamente un módulo que lo escribe; los demás lo leen o lo solicitan. La decisión, sus alternativas y consecuencias están documentadas en:

- [`docs/arc42/arc42.md`](docs/arc42/arc42.md#seccion-4) — sección 4, estrategia de solución.
- [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) — matriz comparativa de estilos evaluados.
- [`docs/adr/0001-estilo-arquitectonico.md`](docs/adr/0001-estilo-arquitectonico.md) — ADR con la decisión formal.
- [`docs/adr/0002-propiedad-datos-establecimiento.md`](docs/adr/0002-propiedad-datos-establecimiento.md) — ADR de la propiedad de `Establecimiento` y el lenguaje publicado.
- [`docs/adr/0003-estrategia-integracion.md`](docs/adr/0003-estrategia-integracion.md) — ADR de la estrategia de integración: síncrona frente a asíncrona, con el análisis de acoplamiento temporal y modos de fallo.
- [`docs/ddd-contextos.md`](docs/ddd-contextos.md) — mapa de contextos y propiedad de datos.
- [`docs/c4/`](docs/c4/) — diagramas C4 (contexto, contenedores y módulos) como código Mermaid.

### Índice de documentación

| Documento | Contenido |
|---|---|
| [`ficha_problema.md`](ficha_problema.md) | Problema, usuarios, alcance y las dos tensiones de calidad |
| [`docs/arc42/arc42.md`](docs/arc42/arc42.md) | Documentación arc42 completa (secciones 1-12, escenarios y glosario) |
| [`docs/aspectos.md`](docs/aspectos.md) | Tabla de trazabilidad de 8 columnas: escenario → C4 → ADR → código → pruebas |
| [`docs/api/`](docs/api/) | **Contratos versionados** (OpenAPI y AsyncAPI), política de versionado e historial |
| [`contracts/consumidor-web.yaml`](contracts/consumidor-web.yaml) | Expectativas del consumidor: qué campos lee y qué códigos maneja |
| [`docs/adr/`](docs/adr/) | Decisiones de arquitectura (ADR) con su trazabilidad |
| [`docs/calidad-sonarcloud.md`](docs/calidad-sonarcloud.md) | Análisis estático, cobertura y Quality Gate |
| [`docs/c4/`](docs/c4/) | Diagramas C4 niveles 1, 2 y 3 en Mermaid |
| [`docs/sistema-de-diseno.md`](docs/sistema-de-diseno.md) | **Sistema de diseño**: principios, los colores de la UTB con su contraste medido, componentes, patrones y las seis pantallas de referencia |
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

**556 pruebas**, agrupadas por lo que protegen:

| Archivo | Qué protege |
|---|---|
| `tests/test_health.py` | Que la aplicación arranca y la sonda responde |
| `tests/test_menu.py` | Consulta y listado del catálogo |
| `tests/test_pedidos.py` | El corte vertical ejecutable descrito más abajo |
| `tests/test_pagos.py` | Idempotencia, firma del webhook y tolerancia a que el evento no llegue |
| `tests/test_propiedad_datos.py` | Que cada dato tenga un único escritor (ADR-0002) |
| `tests/test_modularidad.py` | Que ningún módulo cruce la frontera de otro contexto (ADR-0001) |
| `tests/test_linea_base.py` | La línea base de latencia de [`docs/linea-base.md`](docs/linea-base.md) |
| **`tests/test_contrato_api.py`** | Que el código implemente **exactamente** el contrato publicado |
| **`tests/test_compatibilidad_contrato.py`** | Que el contrato no rompa a un cliente escrito contra la versión anterior |
| **`tests/test_expectativas_consumidor.py`** | Que se siga emitiendo lo que el consumidor declaró que lee |
| **`tests/test_escenarios_de_calidad.py`** | Que las constantes del sitio sigan cumpliendo el umbral del escenario que sostienen |
| **`tests/test_dependencias.py`** | Que la imagen no instale nada que la aplicación no importe, ni al revés |
| **`tests/test_aislamiento.py`** | Que la suite dé el mismo resultado sin importar qué tenga exportado quien la ejecuta |
| `tests/test_promociones.py` | La franja de 2:30 a 3:30, en sus bordes y contra los dos productos reales |
| `tests/test_migraciones.py` | Que una migración aplicada no se pueda editar: el contenedor entraría en bucle de reinicio |
| `tests/test_contraste.py` | Que cada color siga siendo legible sobre la superficie donde cae, **y que los números de la hoja y de la guía de diseño sean esos números** |
| `tests/test_qr.py` | Que el QR de la charla se pueda leer: tabla de formato del estándar, ida y vuelta, y Reed-Solomon |
| `tests/test_demo.py` | Que el reinicio de la demo no exista salvo donde alguien lo haya encendido |
| `tests/test_panel_mostrador.py` | La cola del mostrador y el canje con código |

Las tres últimas son las **pruebas de contrato**, y llevan **20 casos negativos**
—roturas introducidas a propósito— porque una prueba de contrato que no puede
ponerse en rojo no demuestra nada. Cómo reproducir un fallo:
[`docs/api/README.md` §3](docs/api/README.md#run-en-rojo).

### El recorrido con navegador

Las 556 pruebas de arriba montan la aplicación en memoria. Ninguna toca un
botón, así que ninguna puede ver si el botón está donde se alcanza con el pulgar
o si el carrito se vacía al pagar. Para eso está `e2e/`:

```bash
cd e2e
npm ci
npx playwright install chromium
npx playwright test
```

**26 pruebas** en dos tamaños de pantalla, contra el sitio y la API que estén
levantados (`PIDEUTB_SITIO` y `PIDEUTB_API`, por defecto los locales). Las dos
del mostrador se saltan si no hay `PIDEUTB_MOSTRADOR_CORREO` y
`PIDEUTB_MOSTRADOR_CONTRASENA`: necesitan una sesión de verdad para mover un
pedido por la máquina de estados.

No es un lujo: el rediseño de la semana 15 destapó tres defectos que ninguna de
las 556 podía ver —el carrito seguía lleno después de pagar, la barra pegajosa se
quedaba debajo del pie en escritorio, y el botón del carrito dependía de tres
`<span>` anidados para tener nombre accesible—. En la 16 destapó otros tres, y
los tres eran del mismo tipo: el código de recogida de un pedido **ya pagado** se
perdía al recargar, al volver desde la pasarela y al pulsar «Hacer otro pedido»,
porque vivía en una variable de la pestaña. Ninguna prueba de contrato puede ver
eso: el contrato se cumplía entero.

Antes de gastar el navegador conviene comprobar la cadena por HTTP, que dice en
qué eslabón se rompe:

```bash
python scripts/verificar_flujo.py                       # local
python scripts/verificar_flujo.py https://api-pideutb.iscoutb.dev
```

### Integración continua

Cada push y cada pull request ejecutan tres jobs en GitHub Actions
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

| Job | Qué hace |
|---|---|
| `pruebas` | La suite completa (`pytest`) sobre Python 3.11 y 3.12 |
| `contrato` | **Spectral** valida la forma de los contratos y **oasdiff** detecta cambios incompatibles frente a la versión congelada |
| `calidad` | Cobertura y análisis de **SonarCloud** con Quality Gate bloqueante (ver [`docs/calidad-sonarcloud.md`](docs/calidad-sonarcloud.md)) |

El estado del último run está en la insignia del encabezado; el historial
completo en la [pestaña Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).

Validar los contratos en local, sin esperar a CI:

```bash
npx --yes @stoplight/spectral-cli@6.15.0 lint \
  docs/api/openapi.yaml docs/api/asyncapi.yaml \
  --ruleset .spectral.yaml --fail-severity=warn
```

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
│   ├── main.py             # Punto de entrada de la aplicación FastAPI
│   ├── eventos.py          # Bus de eventos en proceso (canal pedidos-pagados)
│   ├── esquemas_comunes.py # Formas de error HTTP, sin contexto de dominio
│   ├── menu/               # Contexto Catálogo — dueño de ÍtemMenu
│   ├── pedidos/            # Contexto Pedidos — dueño de Pedido y Código de canje
│   ├── usuarios/           # Contexto Cuentas — dueño de Establecimiento
│   └── pagos/              # Contexto Pagos — dueño de IntentoPago
├── migraciones/            # SQL numerado e inmutable; `migrar.py` verifica su huella
├── scripts/
│   ├── medir_linea_base.py   # Medición de latencia de POST /v1/pedidos
│   ├── medir_esc03.py        # Mide la cadena completa del escenario ESC-03
│   ├── medir_carga_demo.py   # N personas pidiendo a la vez: p50, p95 y errores
│   ├── verificar_flujo.py    # Recorre la cadena entera contra una URL y dice qué eslabón falla
│   ├── generar_qr.py         # El QR de la charla, en SVG y sin dependencias
│   ├── migrar.py             # Aplica las migraciones pendientes al arrancar
│   ├── crear_usuario.py      # Alta de cuentas del panel (interactivo)
│   ├── sembrar_usuario_inicial.py # La primera cuenta, y solo si no hay ninguna
│   └── comparar_contratos.py # Clasifica cambios del contrato: compatible o no
├── tests/
│   ├── conftest.py                     # Utilidades de las pruebas de contrato
│   ├── test_health.py                  # Prueba automatizada base
│   ├── test_menu.py                    # Catálogo por HTTP
│   ├── test_pedidos.py                 # Corte vertical (crear pedido)
│   ├── test_pagos.py                   # Flujo asíncrono: idempotencia y firma
│   ├── test_propiedad_datos.py         # Dueño único entre contextos
│   ├── test_modularidad.py             # Auditoría de las reglas de dependencia
│   ├── test_linea_base.py              # Regresión sobre la línea base de latencia
│   ├── test_contrato_api.py            # El código cumple el contrato publicado
│   ├── test_compatibilidad_contrato.py # El contrato no rompe a la versión anterior
│   ├── test_expectativas_consumidor.py # Sigue emitiéndose lo que el consumidor lee
│   ├── test_promociones.py             # La franja horaria, en sus bordes
│   ├── test_migraciones.py             # Una migración aplicada es inmutable
│   ├── test_contraste.py               # Los colores se leen, y los números no mienten
│   ├── test_qr.py                      # El QR de la charla decodifica
│   └── test_demo.py                    # El reinicio de la demo está apagado por defecto
├── requirements.in         # Dependencias directas (rangos legibles)
│                           #   (e2e/ cuelga de la raíz, no de backend/)
├── requirements-ci.txt     # Lock con versiones exactas y hashes, usado por CI
├── requirements.txt        # Instalación local
└── pytest.ini

docs/
├── api/                        # CONTRATOS versionados (OpenAPI y AsyncAPI)
│   ├── openapi.yaml            #   superficie síncrona
│   ├── asyncapi.yaml           #   canales asíncronos
│   ├── politica-versionado.md  #   qué rompe y qué no
│   └── historial/              #   versiones congeladas
├── adr/                        # Architecture Decision Records
├── arc42/                      # Documentación arc42
├── c4/                         # Diagramas C4 (contexto, contenedores, módulos) en Mermaid
├── aspectos.md                 # Trazabilidad: escenario → C4 → ADR → código → pruebas
├── calidad-sonarcloud.md       # Análisis estático, cobertura y Quality Gate
├── comparativa-arquitectura.md
├── ddd-contextos.md            # Contextos delimitados y propiedad de datos
├── violaciones.md              # Violaciones del código y plan de corrección
├── linea-base.md               # Línea base de rendimiento y su umbral en CI
└── ia.md

contracts/
└── consumidor-web.yaml         # Qué campos y códigos usa el frontend

correcciones.md                 # Respuesta a la retroalimentación docente
sonar-project.properties        # Configuración del análisis estático
.spectral.yaml                  # Reglas de validación de los contratos

.github/workflows/
└── ci.yml                      # Pipeline: pruebas, contrato y calidad
```

## Corte vertical ejecutable

Esta entrega implementa un flujo de negocio completo de punta a punta
que cruza dos módulos (`pedidos` y `menu`), para demostrar que la
arquitectura de monolito modular funciona en la práctica y no solo en
el papel. El diagrama de secuencia está en
[`arc42.md` §6](docs/arc42/arc42.md#runtime-crear-pedido).

**Flujo:** un usuario (estudiante o profesor) crea un pedido indicando el ítem
de menú que quiere y la cantidad. `pedidos.service` valida el ítem llamando
únicamente a la función pública `menu.service.obtener_item()` — nunca accede al
repositorio de `menu` directamente —, comprueba con `usuarios.service` que el
establecimiento esté operando, **deriva el establecimiento del ítem** en lugar
de aceptarlo del cliente, calcula el total y guarda el pedido.

El flujo completo, incluido el pago asíncrono, está en
[`arc42.md` §6](docs/arc42/arc42.md#runtime-flujos).

### Probarlo manualmente

Con el servidor corriendo (ver "Cómo arrancar el backend"):

```bash
curl -X POST http://127.0.0.1:8000/v1/pedidos \
  -H "Content-Type: application/json" \
  -d '{"item_id": 1, "cantidad": 2}'
```

Respuesta esperada (`201 Created`):

```json
{
  "pedido_id": 1,
  "establecimiento_id": 1,
  "item_id": 1,
  "nombre_item": "Arepa de huevo",
  "precio_unitario_centavos": 400000,
  "cantidad": 2,
  "total_centavos": 800000,
  "estado": "pendiente_pago",
  "codigo_canje": null
}
```

Los importes son **enteros en centavos de COP**: `400000` son 4 000 pesos. La
unidad va en el nombre del campo para que cambiarla obligue a cambiar el nombre
([política de versionado §4](docs/api/politica-versionado.md)).

Con un ítem que no existe (`item_id: 999`) responde `404`. Con un
ítem no disponible (`item_id: 3`, seed de ejemplo) responde `409`.
`establecimiento_id` **no se acepta del cliente**: se deriva del ítem, y un
campo extra en la petición se ignora
([V-01](docs/violaciones.md#v-01)).

### Continuar hasta el pago

```bash
# 1. Abrir el cobro (síncrono: devuelve a dónde ir, no el resultado)
curl -X POST http://127.0.0.1:8000/v1/pagos/intentos \
  -H "Content-Type: application/json" \
  -d '{"pedido_id": 1, "metodo": "tarjeta"}'

# 2. Consultar el estado (el frontend hace esto al volver de la pasarela)
curl http://127.0.0.1:8000/v1/pedidos/1
```

La confirmación del pago **no llega por aquí**: la envía la pasarela a
`POST /v1/pagos/eventos`, firmada, y puede llegar repetida o no llegar nunca.
Los tres casos están cubiertos por pruebas y explicados en
[ADR-0003](docs/adr/0003-estrategia-integracion.md).

### Probarlo con la suite automatizada

```bash
pytest tests/test_pedidos.py -v
```

Cubre el caso exitoso y los dos casos de error (ítem no encontrado /
no disponible), que corresponden al escenario **ESC-01** de
[`arc42.md` §10.2](docs/arc42/arc42.md#esc-01) (fila ESC-01 de
[`docs/aspectos.md`](docs/aspectos.md), columna "Pruebas").

> **Nota:** los repositorios hablan con **PostgreSQL** desde S8. Cada uno
> conserva además una implementación en memoria que se usa cuando no hay
> `PIDEUTB_DATABASE_URL`, para que la suite corra en un portátil sin base de
> datos instalada. Que existan las dos es lo que obliga a
> [`test_repositorios.py`](backend/tests/test_repositorios.py) a ejecutar las
> **mismas aserciones contra ambas**: dos implementaciones que nadie compara se
> separan solas.
>
> La excepción es `usuarios`, que **no** tiene versión en memoria a propósito:
> una autenticación de juguete que funciona sin base de datos invita a
> desplegar sin ella ([ADR-0007](docs/adr/0007-autenticacion-del-panel.md)).
