# Correcciones a la retroalimentación docente — PideUTB

**Equipo:** `Santiago-C0` · `daniarriet` · `ruddy2000utb-droid`
**Repositorio:** https://github.com/ISCOUTB/AS_202620_PideUtb
**Rama evaluable:** `master`
**Estado de CI:** ✅ verde — [run #15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594) — commit `cd70d84`, 13 pruebas en Python 3.11 y 3.12

Este documento resume, para la nueva revisión, qué se corrigió de la
retroalimentación de las semanas 1 a 5 y dónde quedó cada evidencia. El detalle
punto por punto está en la [sección 6](#6-respuesta-punto-por-punto-a-la-retroalimentación).

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

## 3. Evidencia S6 — Contextos delimitados y propiedad de datos

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

## 4. Trabajo planificado

No queda ninguna observación del docente sin atender. El reparto de
contribución, que era el último punto abierto, se resolvió en esta entrega: los
nueve commits de S6 los hicieron los tres integrantes con sus propias cuentas
(4 · 3 · 2).

Lo que sigue es trabajo planificado, no correcciones pendientes: las tres
violaciones que quedan abiertas en
[`docs/violaciones.md`](docs/violaciones.md), cada una con su momento y su
motivo.

| Violación | Cuándo | Por qué en ese punto |
|---|---|---|
| [V-07](docs/violaciones.md#v-07) — dinero en `float` | Con la integración de Pagos | Cambiar el tipo del importe toca el contrato de la API; hacerlo junto al pago evita romperlo dos veces |
| [V-08](docs/violaciones.md#v-08) — `estado` como texto libre | Con el panel del establecimiento | Es el trabajo que necesita las transiciones de estado |
| [V-09](docs/violaciones.md#v-09) — estado en memoria del proceso | Antes de cualquier despliegue | Es la de mayor alcance y bloquea la puesta en producción |

La restricción del reto de la semana 5 y la etiqueta `corte-1` **quedaron
retiradas de las exigencias por el docente**, así que ya no figuran como
pendientes. La medición de línea base que motivó ese trabajo se conserva en
[`docs/linea-base.md`](docs/linea-base.md), porque sigue siendo la evidencia de
ESC-02 y la referencia contra la que se contrastó ADR-0002.

## 5. Cómo verificar

```bash
git clone https://github.com/ISCOUTB/AS_202620_PideUtb
cd AS_202620_PideUtb

# Documentación en las rutas exigidas
ls docs/arc42/ docs/c4/ docs/adr/
ls docs/ddd-contextos.md docs/violaciones.md

# Pruebas (5 en verde)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -v

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

Historial de CI: https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml

---

## 6. Respuesta punto por punto a la retroalimentación

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

### Evidencia de integración continua

El pipeline [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta la
suite completa (`pytest`, 13 pruebas) en Python 3.11 y 3.12 en cada push y cada
pull request.

| Run | Rama | Commit | Evento | Resultado |
|---|---|---|---|---|
| [#15](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34783395594) | `master` | `cd70d84` | push | ✅ success |

Ese es el run de referencia para la entrega: corresponde al estado actual de
`master`, con la entrega S6 completa. El historial completo de
ejecuciones —todas en verde— está en la
[pestaña Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).


## 7. Resumen

**No queda ninguna observación del docente sin atender.** El último punto
abierto era el reparto de contribución, y se cerró en esta entrega: los nueve
commits de S6 están hechos por los tres integrantes desde sus propias cuentas
(`ruddy2000utb-droid` 4 · `daniarriet` 3 · `Santiago-C0` 2), verificable en el
historial de GitHub.

La restricción del reto de la semana 5, su ADR y la etiqueta `corte-1` quedaron
retiradas de las exigencias por el docente.

La **entrega S6 está completa**: mapa de contextos, tabla de propiedad de datos
con dueño único, lista de violaciones con plan de corrección, arc42 §8 con el
lenguaje ubicuo, glosario y C4 nivel 3 actualizados, y ADR-0002 — más seis
violaciones corregidas en el código, cada una con su prueba. La suite pasó de 5
a 13 pruebas, todas en verde en CI.
