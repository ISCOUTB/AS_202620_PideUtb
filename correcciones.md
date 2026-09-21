# Correcciones a la retroalimentación docente — PideUTB

**Equipo:** `Santiago-C0` · `daniarriet` · `ruddy2000utb-droid`
**Repositorio:** https://github.com/ISCOUTB/AS_202620_PideUtb
**Rama evaluable:** `master`
**Estado de CI:** ✅ verde — [run #18](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35550051257) — commit `356369d` sobre `master`, conclusión `success`. Es el run del **hash exacto que se entrega**, como pidió la retroalimentación de S6.
**Quality Gate:** ⚠️ `PENDIENTE` — el job `calidad` ya corre y se omite sin fallar mientras no exista el secreto `SONAR_TOKEN`, tal como se diseñó. Alta en [`docs/calidad-sonarcloud.md`](docs/calidad-sonarcloud.md) §1

Este documento resume, para la nueva revisión, qué se corrigió de la
retroalimentación de las semanas 1 a 5 y dónde quedó cada evidencia. El detalle
punto por punto está en la [sección 7](#7-respuesta-punto-por-punto-a-la-retroalimentación).

---

## 1. Dónde quedó cada documento exigido

Los documentos ya están en las rutas que pedía el curso. Esta era la principal
observación estructural.

| Documento exigido | Ruta actual | Antes estaba en |
|---|---|---|
| Plantilla arc42 | [`docs/arc42/arc42.md`](docs/arc42/arc42.md) | raíz del repositorio |
| Diagramas C4 (niveles 1, 2 y 3, en Mermaid) | [`docs/c4/`](docs/c4/) | `docs/C4/` (mayúsculas) |
| Registros de decisión (ADR) | [`docs/adr/`](docs/adr/) | ya estaba |
| Tabla de aspectos (8 columnas) | [`docs/aspectos.md`](docs/aspectos.md) | existía como texto corrido |
| Ficha del problema (Markdown) | [`ficha_problema.md`](ficha_problema.md) | era un PDF |
| Registro de uso de IA | [`docs/ia.md`](docs/ia.md) | ya estaba |
| Matriz comparativa de estilos | [`docs/comparativa-arquitectura.md`](docs/comparativa-arquitectura.md) | ya estaba |
| Pipeline de CI | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | no existía |
| Línea base de rendimiento | [`docs/linea-base.md`](docs/linea-base.md) | no existía |
| Contextos delimitados y propiedad de datos | [`docs/ddd-contextos.md`](docs/ddd-contextos.md) | no existía (S6) |
| Violaciones y plan de corrección | [`docs/violaciones.md`](docs/violaciones.md) | no existía (S6) |
| ADR de propiedad de `Establecimiento` | [`docs/adr/0002-propiedad-datos-establecimiento.md`](docs/adr/0002-propiedad-datos-establecimiento.md) | no existía (S6) |
| Contrato de API versionado (OpenAPI 3.1) | [`docs/api/openapi.yaml`](docs/api/openapi.yaml) | no existía (S7) |
| Contrato de eventos (AsyncAPI 3.0) | [`docs/api/asyncapi.yaml`](docs/api/asyncapi.yaml) | no existía (S7) |
| Política de versionado del contrato | [`docs/api/politica-versionado.md`](docs/api/politica-versionado.md) | no existía (S7) |
| Expectativas del consumidor | [`contracts/consumidor-web.yaml`](contracts/consumidor-web.yaml) | no existía (S7) |
| ADR de la estrategia de integración | [`docs/adr/0003-estrategia-integracion.md`](docs/adr/0003-estrategia-integracion.md) | no existía (S7) |
| Configuración de análisis estático | [`sonar-project.properties`](sonar-project.properties) | no existía (S7) |
| Reglas de validación de contratos | [`.spectral.yaml`](.spectral.yaml) | no existía (S7) |

## 2. Qué se corrigió

### Estructura y enlaces

- `arc42.md` se movió a `docs/arc42/` y `docs/C4/` se renombró a `docs/c4/`.
- Al mover `arc42.md` en una entrega anterior se habían roto **todas** las rutas
  relativas del README, de `docs/aspectos.md` y de los tres archivos de C4.
  Quedaron corregidas y verificadas: los 60+ enlaces internos del repositorio
  resuelven correctamente.
- Las anclas de los enlaces a escenarios eran inconsistentes (convivían
  `#105-esc-04--…` y `#105-esc-04-----…`, generadas automáticamente a partir de
  los títulos). Se sustituyeron por anclas HTML explícitas y estables:
  `#esc-01` … `#esc-05`, `#seccion-4`, `#tacticas-por-escenario`,
  `#arbol-utilidad`.

### Trazabilidad

- [`docs/aspectos.md`](docs/aspectos.md) se reescribió con la **tabla de ocho
  columnas** del curso: ID · Aspecto · Escenario · Medida de respuesta · C4 ·
  ADR · Código · Pruebas. La cadena está **completa de punta a punta para
  ESC-01**; ESC-02 a ESC-05 tienen escenario, C4 y ADR, y se marcan como
  pendientes porque dependen de los módulos `pagos` y `usuarios`, todavía
  vacíos. No se registran rutas de código o pruebas que no existan.
- [`ADR-0001`](docs/adr/0001-estilo-arquitectonico.md) incorpora una sección de
  **trazabilidad**: el escenario que lo motiva (ESC-01), los commits que lo
  implementan (`b5f0310`, `2e165bb`), los archivos de código que materializan la
  regla de comunicación entre módulos y las tres pruebas que la verifican.
- La sección 4 de arc42 estaba escrita a nivel de atributos de calidad. Ahora
  [§4.3](docs/arc42/arc42.md#seccion-4) argumenta **por escenario priorizado**
  (ESC-01, ESC-02, ESC-03) con su umbral, qué favorece el estilo elegido y qué
  se sacrifica; y [§4.4](docs/arc42/arc42.md#tacticas-por-escenario) añade las
  **tácticas arquitectónicas por escenario**.
- La [matriz comparativa](docs/comparativa-arquitectura.md) incorpora una
  segunda matriz **con filas por escenario del árbol de utilidad**, indicando
  qué escenario mejora y cuál empeora con cada estilo, más una fila de balance.

### Integración continua y medición

- Se añadió [`.github/workflows/ci.yml`](.github/workflows/ci.yml): ejecuta
  `pytest` en Python 3.11 y 3.12 en cada push y cada pull request.
- **Run en verde:** https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594
- Se añadió `backend/scripts/medir_linea_base.py` y la prueba de regresión
  `backend/tests/test_linea_base.py`. **Línea base medida** sobre 300 peticiones
  a `POST /pedidos`: p50 **2,85 ms**, p95 **3,32 ms**
  ([detalle y método](docs/linea-base.md)).

### Otros puntos

- La ficha del problema pasó de PDF a Markdown y ahora declara **usuarios**,
  **alcance** y las **dos tensiones de calidad** (usabilidad ⟷ seguridad;
  rendimiento/disponibilidad ⟷ simplicidad de construcción), con la resolución
  adoptada para cada una.
- [`docs/ia.md`](docs/ia.md) registra el uso de IA de la semana 5 e incluye una
  tabla de **qué se rechazó de lo que propuso la IA y por qué** (siete
  propuestas descartadas, con su motivo).
- El entorno virtual ya no está versionado y `.gitignore` cubre `.venv/` y
  `.venv-*/`.

## 3. Evidencia S7 — Contrato de API, pruebas de contrato y ADR de integración

| Artefacto pedido | Dónde está |
|---|---|
| **Archivo de contrato versionado** | [`docs/api/openapi.yaml`](docs/api/openapi.yaml) (OpenAPI 3.1, `info.version: 1.0.0`) y [`docs/api/asyncapi.yaml`](docs/api/asyncapi.yaml) (AsyncAPI 3.0). Enlazados desde el [README](README.md#contrato-de-api) |
| **Prueba de contrato en el pipeline** | Job `contrato` de [`ci.yml`](.github/workflows/ci.yml) — Spectral y oasdiff — más tres módulos de `pytest` en el job `pruebas` |
| **ADR que justifica la estrategia de integración** | [ADR-0003](docs/adr/0003-estrategia-integracion.md), anclado a [ESC-05](docs/arc42/arc42.md#esc-05) y con las dos alternativas descartadas |
| **arc42 §6 con los flujos de interacción** | [`arc42.md` §6](docs/arc42/arc42.md#runtime-flujos) — reescrita: resumen de flujos, crear pedido, pagar, consultar estado y modos de fallo |
| **C4 nivel 2 con protocolo y formato por flecha** | [`nivel2-contenedores.md`](docs/c4/nivel2-contenedores.md) — cinco relaciones etiquetadas con protocolo, formato y modo |

### El contrato se escribió antes que el código

No es una reconstrucción de lo que ya existía. El contrato fijó tres decisiones
que **obligaron a cambiar el código** para cumplirlas:

| Decisión del contrato | Qué cambió en el código | Violación que cierra |
|---|---|---|
| Los importes son enteros en centavos, con la unidad en el nombre del campo | `precio` → `precio_centavos`, `total` → `total_centavos` en modelos, seeds y pruebas | [V-07](docs/violaciones.md#v-07) |
| `EstadoPedido` es un conjunto cerrado de seis valores | `estado: str` → `estado: EstadoPedido` (`Enum`) en `pedidos.contracts` | [V-08](docs/violaciones.md#v-08) |
| La superficie de negocio vive bajo `/v1`; la sonda de salud queda fuera | Todas las rutas se movieron a `/v1`; `/health` no | — |

### Las tres capas de validación, y por qué hacen falta las tres

La retroalimentación pedía «schemathesis, spectral o equivalente». Se usan
**dos herramientas reconocidas más pruebas propias**, porque ninguna de las tres
capas detecta lo que detectan las otras:

| Capa | Herramienta | Pregunta que responde |
|---|---|---|
| Forma | **Spectral** (`npx`, sin tocar el lock de Python) | ¿Es un OpenAPI 3.1 / AsyncAPI 3.0 válido y bien formado? |
| Compatibilidad | **oasdiff** (imagen oficial) + [`comparar_contratos.py`](backend/scripts/comparar_contratos.py) | ¿Rompe a un cliente escrito contra la versión anterior? |
| Conformidad | `pytest` | ¿Lo cumple el código? ¿Sigue emitiendo lo que el consumidor declaró que lee? |

Una herramienta externa no puede responder la tercera: no sabe qué campos usa de
verdad nuestro frontend. Eso lo declara
[`contracts/consumidor-web.yaml`](contracts/consumidor-web.yaml), que es la
forma exacta que describe el material de la semana — *el consumidor declara qué
campos necesita; el pipeline del proveedor falla si deja de emitirlos*.

El comparador propio, además, conoce una regla que ninguna herramienta genérica
puede aplicar: la **asimetría de los `enum`**. Añadir un valor es compatible si
el cliente lo *envía* e incompatible si lo *recibe*, y eso depende de si el
esquema cuelga de `requestBody` o de `responses`
([política §3.1](docs/api/politica-versionado.md)).

### La prueba de contrato puede fallar, y está demostrado

> *«sin una prueba que pueda fallar, la validación no demuestra nada»*

Las tres pruebas de contrato incluyen **20 casos negativos**: roturas
introducidas a propósito que la prueba exige detectar. Si alguna dejara de
detectarse, las propias pruebas lo delatarían.

| Módulo | Casos negativos |
|---|---|
| `test_compatibilidad_contrato.py` | 10 roturas, una por regla de la política (I-1 … I-10), más 5 evoluciones compatibles que **no** deben bloquearse |
| `test_contrato_api.py` | 7 derivas entre contrato y código |
| `test_expectativas_consumidor.py` | 3 retiradas de algo que el consumidor declara usar |

El procedimiento reproducible para dejar **un run en rojo registrado en
Actions** —en una rama desechable, para no ensuciar `master`— está en
[`docs/api/README.md` §3](docs/api/README.md#run-en-rojo), con la salida exacta
que produce: 3 fallos, uno por capa, y 3 omisiones explicadas.

⚠️ **PENDIENTE de completar:** la URL del run en rojo, una vez ejecutado el
procedimiento.

### El código avanzó con el contrato

| Antes de S7 | Después |
|---|---|
| `pagos` era un paquete vacío | Implementado: cobro síncrono, webhook firmado, idempotencia y publicación de evento |
| No había forma de listar la carta | `GET /v1/menu/establecimientos/{id}/items`, que distingue «no existe» de «existe y está vacío» |
| No había forma de consultar un pedido | `GET /v1/pedidos/{id}`, que es como el usuario se entera del resultado del pago |
| El estado vivía solo en el pedido | Canal de eventos `pedidos-pagados` con aislamiento de fallos del suscriptor |
| 13 pruebas | **77 pruebas**, 99 % de cobertura |

---

## 4. Evidencia S6 — Contextos delimitados y propiedad de datos

Los tres artefactos que pide la semana, más lo que el recordatorio de
arc42 · C4 · ADR exige cuando los límites cambian:

| Artefacto pedido | Dónde está |
|---|---|
| **Mapa de contextos** | [`docs/ddd-contextos.md` §2](docs/ddd-contextos.md) — cuatro contextos delimitados, con el patrón de cada relación (customer/supplier, anticorruption layer) y por qué no se usa shared kernel |
| **Tabla módulo → datos con dueño único** | [`docs/ddd-contextos.md` §3](docs/ddd-contextos.md) — cada dato con su único escritor y quién lo lee o lo solicita |
| **Lista de violaciones con plan de corrección** | [`docs/violaciones.md`](docs/violaciones.md) — nueve violaciones, seis corregidas con prueba, tres planificadas |
| **arc42 §8 con lenguaje ubicuo y mapa de contextos** | [`docs/arc42/arc42.md` §8](docs/arc42/arc42.md#seccion-8) |
| **Glosario actualizado (§12)** | Términos **Cuenta** y **Carrito** añadidos para resolver las ambigüedades detectadas |
| **C4 nivel 3 actualizado** | [`docs/c4/nivel3-modulos.md`](docs/c4/nivel3-modulos.md) |
| **ADR del reajuste** | [ADR-0002](docs/adr/0002-propiedad-datos-establecimiento.md) |

### El lenguaje ubicuo se auditó contra la propia documentación

La pregunta guía de la semana era *«¿qué palabra de vuestro dominio significa
dos cosas según con quién habléis?»*. La respuesta no se inventó: se encontraron
**dos contradicciones reales dentro de los documentos que el equipo ya había
escrito**.

| Ambigüedad | Dónde chocan | Resolución |
|---|---|---|
| **«Usuario»** | El glosario §12 lo define como estudiante o profesor; arc42 §5.3 describe `usuarios` como *«usuario: estudiante o profesor / establecimiento / admin»* | Se separan **Usuario** (negocio) y **Cuenta** (técnico). El módulo gestiona Cuentas |
| **«Carrito»** | ESC-05 dice que *«el pedido/carrito deberá conservarse»*, pero no existe ninguna entidad `Carrito` | Se documenta como sinónimo de «pedido en estado `pendiente_pago`», sin crear entidad |

### El código cambió con la documentación

Seis de las nueve violaciones están corregidas, cada una con su prueba.

| Cambio | Violación | Prueba |
|---|---|---|
| El módulo `usuarios` pasa a ser único escritor de `Establecimiento` | [V-02](docs/violaciones.md#v-02) | `test_pedido_en_establecimiento_inactivo_se_rechaza` |
| `establecimiento_id` se deriva del ítem, no del cliente | [V-01](docs/violaciones.md#v-01) | `test_establecimiento_se_deriva_del_item_y_no_del_cliente` |
| `cantidad` acotada a 1–50 | [V-03](docs/violaciones.md#v-03) | `test_cantidad_fuera_de_rango_se_rechaza` |
| Lenguaje publicado (`contracts.py`) en las fronteras | [V-05](docs/violaciones.md#v-05) | `test_modularidad.py` |
| `precio_unitario` en el pedido: la instantánea ya es auditable | [V-06](docs/violaciones.md#v-06) | `test_el_pedido_conserva_el_precio_aunque_cambie_el_catalogo` |
| **Auditoría automática de la regla de dependencia** | [V-04](docs/violaciones.md#v-04) | `test_ningun_modulo_cruza_la_frontera_de_otro_contexto` |

La última es la que más importa: analiza el árbol de sintaxis de cada archivo y
falla la construcción si un módulo importa algo que no sea `service` o
`contracts` de otro contexto. Hasta ahora la regla de ADR-0001 solo existía en
la documentación. La prueba incluye su propio caso negativo.

La suite pasó de 5 a **13 pruebas**, todas en verde, y la decisión de ADR-0002
no quedó como propuesta: el módulo `usuarios` se implementó con esa
responsabilidad.

## 5. Trabajo planificado

No queda ninguna observación del docente sin atender. El reparto de
contribución, que era el último punto abierto, se resolvió en esta entrega: los
nueve commits de S6 los hicieron los tres integrantes con sus propias cuentas
(4 · 3 · 2).

Lo que sigue es trabajo planificado, no correcciones pendientes: las tres
violaciones que quedan abiertas en
[`docs/violaciones.md`](docs/violaciones.md), cada una con su momento y su
motivo.

| Violación | Cuándo | Estado |
|---|---|---|
| [V-07](docs/violaciones.md#v-07) — dinero en `float` | Se planificó «con la integración de Pagos» | ✅ **Cerrada en S7**: publicar el contrato obligaba a fijar el tipo del importe, y hacerlo después habría exigido `/v2` |
| [V-08](docs/violaciones.md#v-08) — `estado` como texto libre | Se planificó «con el panel del establecimiento» | ✅ **Cerrada en S7**: el conjunto de estados es parte del contrato. Queda pendiente la máquina de transiciones, que sí entra con el panel |
| [V-09](docs/violaciones.md#v-09) — estado en memoria del proceso | Antes de cualquier despliegue | ⏳ Abierta. Es la de mayor alcance y bloquea la puesta en producción |

La restricción del reto de la semana 5 y la etiqueta `corte-1` **quedaron
retiradas de las exigencias por el docente**, así que ya no figuran como
pendientes. La medición de línea base que motivó ese trabajo se conserva en
[`docs/linea-base.md`](docs/linea-base.md), porque sigue siendo la evidencia de
ESC-02 y la referencia contra la que se contrastó ADR-0002.

## 6. Cómo verificar

```bash
git clone https://github.com/ISCOUTB/AS_202620_PideUtb
cd AS_202620_PideUtb

# Documentación en las rutas exigidas
ls docs/arc42/ docs/c4/ docs/adr/
ls docs/ddd-contextos.md docs/violaciones.md

# Documentación en las rutas exigidas (S7)
ls docs/api/openapi.yaml docs/api/asyncapi.yaml docs/api/politica-versionado.md
ls docs/adr/0003-estrategia-integracion.md contracts/consumidor-web.yaml

# Pruebas (77 en verde)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -v

# Validar la forma de los contratos (no necesita Python)
cd .. && npx --yes @stoplight/spectral-cli@6.15.0 lint \
  docs/api/openapi.yaml docs/api/asyncapi.yaml \
  --ruleset .spectral.yaml --fail-severity=warn

# Línea base de rendimiento
python scripts/medir_linea_base.py 300
```

La auditoría de modularidad se puede ejercitar introduciendo una violación a
propósito y comprobando que el CI la rechaza:

```bash
# Añade esta línea a backend/app/pedidos/service.py y ejecuta pytest:
#   from app.usuarios.repository import buscar_establecimiento_por_id
cd backend && pytest tests/test_modularidad.py     # debe fallar
```

Y la prueba de contrato, igual: quitando `total_centavos` del esquema `Pedido`
en `docs/api/openapi.yaml` fallan **tres** pruebas, una por cada capa de
validación. El procedimiento completo, con la salida exacta que produce, está en
[`docs/api/README.md` §3](docs/api/README.md#run-en-rojo).

Historial de CI: https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml

---

## 7. Respuesta punto por punto a la retroalimentación

Estados: ✅ corregido · ➖ retirado de las exigencias por el docente.

### Semanas 1 y 2

| Observación | Estado | Evidencia |
|---|---|---|
| Repositorio público y en la organización | ✅ | Se mantiene público en `ISCOUTB/AS_202620_PideUtb` |
| Ficha del problema en Markdown, no en PDF | ✅ | [`ficha_problema.md`](ficha_problema.md); el PDF se eliminó |
| Declarar las dos tensiones de calidad en la ficha | ✅ | [`ficha_problema.md` § Atributos de calidad y tensiones](ficha_problema.md): T-1 usabilidad ⟷ seguridad, T-2 rendimiento ⟷ simplicidad |
| Tabla de ocho columnas en `docs/aspectos.md` (era solo texto) | ✅ | [`docs/aspectos.md`](docs/aspectos.md): ID · Aspecto · Escenario · Medida · C4 · ADR · Código · Pruebas |
| Plantilla arc42 en `docs/arc42/` | ✅ | [`docs/arc42/arc42.md`](docs/arc42/arc42.md) |
| Carpetas `docs/adr/` y `docs/c4/` | ✅ | [`docs/adr/`](docs/adr/) y [`docs/c4/`](docs/c4/) (la carpeta estaba como `docs/C4/`, se renombró a minúsculas) |
| Anclas de los enlaces en `docs/aspectos.md` | ✅ | Se reemplazaron las anclas autogeneradas —inconsistentes: convivían `#105-esc-04--…` y `#105-esc-04-----…`— por anclas HTML explícitas (`<a id="esc-01"></a>` … `esc-05`). Además, mover `arc42.md` había roto **todas** las rutas relativas del README, de `docs/aspectos.md` y de los tres archivos de C4; quedaron corregidas |
| Registrar en `docs/ia.md` qué se rechazó de la IA y por qué | ✅ | [`docs/ia.md` § Qué se rechazó y por qué](docs/ia.md) |
| Repartir la contribución entre los integrantes | ✅ | Los nueve commits de S6 los hicieron los tres integrantes con sus propias cuentas: `ruddy2000utb-droid` 4, `daniarriet` 3, `Santiago-C0` 2 |

### Semana 3

| Observación | Estado | Evidencia |
|---|---|---|
| Ligar arc42 §4 a ESC-01/02/03 con tácticas por escenario | ✅ | [§4.3 motivación por escenario](docs/arc42/arc42.md#seccion-4) reescrita con una fila por escenario priorizado y umbral, y nueva [§4.4 tácticas por escenario](docs/arc42/arc42.md#tacticas-por-escenario) |
| Rehacer la matriz comparativa con filas por escenario | ✅ | [`docs/comparativa-arquitectura.md` § Matriz por escenario](docs/comparativa-arquitectura.md): una fila por escenario, con qué mejora y qué empeora en cada estilo, y una fila de balance |
| Enlazar el ADR 0001 desde `docs/aspectos.md` y desde el escenario que lo motiva | ✅ | Columna ADR de la tabla de aspectos, y sección Trazabilidad del [ADR-0001](docs/adr/0001-estilo-arquitectonico.md), que nombra ESC-01 como escenario motivador |
| Workflow en `.github/workflows/` que ejecute `pytest`, con run en verde | ✅ | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — `pytest` en Python 3.11 y 3.12, en cada push y pull request. **Run en verde:** [Actions run #15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594) |
| Mover `arc42.md` a `docs/arc42/` y el C4 a `docs/c4/` | ✅ | Ver semanas 1 y 2 |

### Semana 4

| Observación | Estado | Evidencia |
|---|---|---|
| Diagramas C4 como código en `docs/c4/` | ✅ | [Nivel 1](docs/c4/nivel1-contexto.md), [Nivel 2](docs/c4/nivel2-contenedores.md), [Nivel 3](docs/c4/nivel3-modulos.md), todos en Mermaid |
| Verificar que los contenedores coincidan con `backend/app` | ✅ | El nivel 3 lista `pedidos`, `menu`, `pagos` y `usuarios`, que son exactamente los paquetes existentes en `backend/app/` |
| Completar la tabla de aspectos con ID, C4, ADR, Código y Pruebas | ✅ | [`docs/aspectos.md`](docs/aspectos.md) |
| Añadir al ADR la trazabilidad (commit que lo implementa y pruebas) | ✅ | [ADR-0001 § Trazabilidad](docs/adr/0001-estilo-arquitectonico.md): commits `b5f0310` y `2e165bb`, archivos de código y las tres pruebas de `test_pedidos.py` |
| No versionar el entorno virtual `.venv-1` | ✅ | Ya no hay archivos de entorno virtual rastreados; `.gitignore` cubre `.venv/` y `.venv-*/` |
| Ejecutar las pruebas en CI y dejar el enlace al run en verde | ✅ | **Run en verde sobre `master`:** [Actions run #15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594) — commit `cd70d84`, 13 pruebas en Python 3.11 y 3.12, conclusión `success` |
| Glosario y secciones 1-6, 9, 10 y 12 visibles en `docs/arc42/` | ✅ | Todas presentes en [`docs/arc42/arc42.md`](docs/arc42/arc42.md) |

### Semana 5 · Primer corte

| Observación | Estado | Evidencia |
|---|---|---|
| Documentar la restricción asignada y su diagnóstico | ➖ | **Retirada de las exigencias por el docente.** El diagnóstico del punto de medición se conserva en [`docs/linea-base.md` §1](docs/linea-base.md) porque sigue siendo válido |
| Medir una línea base | ✅ | [`docs/linea-base.md` §3](docs/linea-base.md): 300 peticiones a `POST /pedidos` — p50 **2,66 ms**, p95 **3,02 ms**. Instrumento reproducible: `backend/scripts/medir_linea_base.py` |
| Cubrir el cambio con una prueba en CI | ✅ | `backend/tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral`, ejecutada en verde por el workflow ([run #15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594)) |
| Registrar el ADR del reto | ➖ | Retirado junto con la restricción. El número 0002 quedó asignado a la [propiedad de los datos de Establecimiento](docs/adr/0002-propiedad-datos-establecimiento.md) |
| Implementar el cambio y contrastarlo con el umbral | ➖ | Retirado. Aun así, la línea base sirvió para contrastar el reajuste de ADR-0002: el p95 bajó de 3,32 ms a 3,02 ms pese a duplicar las llamadas entre contextos |
| Completar la cadena de ocho columnas en `docs/aspectos.md` | ✅ | Completa de punta a punta para ESC-01; ESC-02 a ESC-05 tienen escenario, C4 y ADR, y quedan marcadas ⏳ hasta que existan los módulos `pagos` y `usuarios` |
| Organizar arc42 y C4 en las carpetas exigidas | ✅ | `docs/arc42/` y `docs/c4/` |
| Registrar el uso de IA de S5 | ✅ | [`docs/ia.md` § Uso de IA en la quinta entrega](docs/ia.md), con la tabla de rechazos |
| Retirar `.venv-1/` del repositorio | ✅ | Ver semana 4 |
| Crear la etiqueta `corte-1` sobre el commit correcto | ➖ | **Retirada de las exigencias por el docente** |
| Documento de correcciones a la revisión preliminar | ✅ | Este documento |

### Semana 6

| Observación | Estado | Evidencia |
|---|---|---|
| Enlace al análisis público de SonarCloud con su Quality Gate | ⚠️ En curso | [`sonar-project.properties`](sonar-project.properties) y el job `calidad` de [`ci.yml`](.github/workflows/ci.yml) ya están en el repositorio. Falta el alta en SonarCloud y el secreto `SONAR_TOKEN`; el procedimiento está en [`docs/calidad-sonarcloud.md`](docs/calidad-sonarcloud.md). Hasta entonces el job se omite sin poner el pipeline en rojo |
| Run de CI del hash revisado | ✅ | [Run #18](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35550051257) — commit `356369d`, el mismo que se entrega. La observación era correcta: el run citado antes (`cd70d84`) ya no era el estado de `master` |
| Títulos de los ADR que enuncien la decisión, no el tema | ✅ | Los tres reescritos. ADR-0001: «Adoptar un monolito modular en el que un módulo solo invoca la interfaz pública de otro». ADR-0002: «Hacer del contexto Cuentas el único escritor de `Establecimiento`…». ADR-0003: «Confirmar el pago de forma asíncrona por webhook y mantener síncrono el resto de la API». El índice de [arc42 §9](docs/arc42/arc42.md) se rehízo como tabla con una columna *Decisión* y otra *Escenario que la motiva* |
| arc42 §8 con lenguaje ubicuo y mapa de contextos | ✅ | [§8.1](docs/arc42/arc42.md#lenguaje-ubicuo) lenguaje ubicuo, [§8.2](docs/arc42/arc42.md#seccion-8) contextos y propiedad de datos. Ya estaba desde S6; se confirma |
| Mantener la trazabilidad de aspectos y el registro de IA | ✅ | [`docs/aspectos.md`](docs/aspectos.md) amplía la cadena a ESC-04 y ESC-05, que dejan de estar pendientes; [`docs/ia.md`](docs/ia.md) registra el uso de S7 con lo rechazado |

### Semana 7

| Observación | Estado | Evidencia |
|---|---|---|
| No hay especificación OpenAPI o AsyncAPI versionada | ✅ | [`docs/api/openapi.yaml`](docs/api/openapi.yaml) `1.0.0` y [`docs/api/asyncapi.yaml`](docs/api/asyncapi.yaml) `1.0.0` |
| Publicar el contrato como archivo y **declarar su versión** | ✅ | `info.version: 1.0.0` en ambos, más [`docs/api/historial/`](docs/api/historial/) con la versión congelada y [`politica-versionado.md`](docs/api/politica-versionado.md) que distingue la versión del contrato de la de la ruta (`/v1`) |
| **Enlazarlo desde el README** | ✅ | [README § Contrato de API](README.md#contrato-de-api), primera sección del documento |
| Contrastar contrato contra código | ✅ | `backend/tests/test_contrato_api.py` compara el contrato con `app.openapi()` en **ambas direcciones**: lo prometido y no implementado, y lo expuesto sin declarar |
| Validación de contrato en el pipeline (schemathesis, spectral o equivalente) | ✅ | Job `contrato`: **Spectral** con [`.spectral.yaml`](.spectral.yaml) y `--fail-severity=warn`, y **oasdiff** contra la versión congelada |
| Evidencia de un run en rojo por un cambio incompatible | ⚠️ Procedimiento listo | [`docs/api/README.md` §3](docs/api/README.md#run-en-rojo), reproducible y verificado en local. Falta ejecutarlo y registrar la URL |
| ADR que justifique la integración síncrona o asíncrona **contra un escenario de calidad**, con **la alternativa descartada** | ✅ | [ADR-0003](docs/adr/0003-estrategia-integracion.md): anclado a [ESC-05](docs/arc42/arc42.md#esc-05) (mensaje < 3 s, pedido conservado en el 100 %), con **dos** alternativas descartadas y el motivo de cada una |
| Evidencia auditable de SonarCloud: configuración, run del hash y URL del Quality Gate | ⚠️ En curso | Ver la fila equivalente de la semana 6 |

### Evidencia de integración continua

El pipeline [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta
cuatro jobs en cada push y cada pull request:

| Job | Qué corre | Resultado en el run #18 |
|---|---|---|
| `pytest (Python 3.11)` | 77 pruebas | ✅ |
| `pytest (Python 3.12)` | 77 pruebas | ✅ |
| `Contrato de API` | Spectral sobre los dos contratos + oasdiff contra la versión congelada | ✅ en 15 s |
| `SonarCloud` | Cobertura y Quality Gate | ✅ omitido — *«Falta el secreto SONAR_TOKEN; se omite el análisis»*, que es el comportamiento diseñado |

Duración total: 55 s.

| Run | Rama | Commit | Evento | Resultado |
|---|---|---|---|---|
| [**#18**](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35550051257) | `master` | `356369d` | push | ✅ **success** — entrega S7 |
| [#15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594) | `master` | `cd70d84` | push | ✅ success — entrega S6 |

El run **#18** es el de referencia para esta entrega: corresponde al commit
`356369d`, que es el estado actual de `master` con la entrega S7 completa. El
#15 se conserva como referencia de S6. El historial completo de
ejecuciones —todas en verde— está en la
[pestaña Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).


## 8. Resumen

La **entrega S7 está completa** en lo que depende del repositorio:

| Evidencia pedida | Estado |
|---|---|
| Archivo de contrato versionado | ✅ [`openapi.yaml`](docs/api/openapi.yaml) `1.0.0` y [`asyncapi.yaml`](docs/api/asyncapi.yaml) `1.0.0`, enlazados desde el [README](README.md#contrato-de-api) |
| Prueba de contrato en el pipeline | ✅ Job `contrato` (Spectral + oasdiff) y tres módulos de `pytest` con **20 casos negativos** |
| ADR que justifica la estrategia de integración | ✅ [ADR-0003](docs/adr/0003-estrategia-integracion.md), anclado a ESC-05 y con dos alternativas descartadas |
| arc42 §6 con los flujos de interacción | ✅ [Reescrita](docs/arc42/arc42.md#runtime-flujos): cinco flujos, sus protocolos y nueve modos de fallo, cada uno con su prueba |
| C4 nivel 2 etiquetado con protocolo y formato | ✅ [Cinco relaciones etiquetadas](docs/c4/nivel2-contenedores.md), incluida la del webhook entrante |

Además se cerraron **dos violaciones planificadas** —[V-07](docs/violaciones.md#v-07)
(dinero en `float`) y [V-08](docs/violaciones.md#v-08) (estado como texto
libre)— porque publicar el contrato obligaba a decidir ambas cosas, y la suite
pasó de **13 a 77 pruebas** con un 99 % de cobertura.

**Quedan dos puntos abiertos, ambos fuera del repositorio:**

1. ⚠️ **El alta en SonarCloud.** La configuración está
   ([`sonar-project.properties`](sonar-project.properties), job `calidad`), pero
   el secreto `SONAR_TOKEN` y la URL pública del Quality Gate requieren crear el
   proyecto en SonarCloud: [`docs/calidad-sonarcloud.md`](docs/calidad-sonarcloud.md) §1.
2. ⚠️ **Los dos enlaces de evidencia de CI**: el run en verde del commit que se
   entrega, y el run en rojo que demuestra que la validación de contrato puede
   fallar. Ambos se registran en el encabezado de este documento.

Se declaran como abiertos en lugar de omitirlos: la retroalimentación pedía
evidencia **auditable**, y una configuración sin su ejecución todavía no lo es.
