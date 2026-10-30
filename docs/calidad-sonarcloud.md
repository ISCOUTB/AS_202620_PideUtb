# Análisis estático y Quality Gate (SonarCloud)

> Responde a la observación repetida en la retroalimentación de las semanas 6 y
> 7: *«la evidencia de SonarCloud debe ser auditable: archivo de configuración,
> run del hash revisado y URL pública con el estado del Quality Gate»*.

Los tres elementos exigidos y dónde está cada uno:

| Elemento exigido | Dónde | Estado |
|---|---|---|
| **Archivo de configuración** | [`sonar-project.properties`](../sonar-project.properties) | ✅ En el repositorio |
| **Ejecución en el pipeline** | Job `calidad` de [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | ✅ Definido |
| **URL pública del Quality Gate** | [Panel del proyecto](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb) | ✅ Público, sin cuenta, y en **OK** |
| **Run del hash revisado** | [Run #20](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35556118369) — commit `130c653` | ✅ |

Identificadores del proyecto, **verificados contra la API** y no supuestos:

| Dato | Valor |
|---|---|
| `projectKey` | `ISCOUTB_AS_202620_PideUtb` |
| `organization` | `isco-utb` |
| Visibilidad | `public` |

---

## 1. Método de análisis: por qué sigue siendo el automático

SonarCloud está conectado al repositorio y analizando mediante *Automatic
Analysis*: el modo en que la aplicación de GitHub lee el código por su cuenta,
sin pasar por el pipeline. Con él, los tres elementos que exige la
retroalimentación —configuración, run del hash y URL pública del Quality
Gate— **están cubiertos**.

**Decisión: se mantiene el análisis automático por ahora.** Cambiar el método
de análisis de un repositorio de la organización afecta a los tres integrantes
y al criterio de evaluación, así que se consulta antes de tocarlo. Lo que sigue
documenta qué se gana con el cambio y cómo hacerlo, no una tarea pendiente de
la entrega.

Lo que el análisis automático **no** puede hacer:

| | Automatic Analysis | Análisis desde el pipeline |
|---|---|---|
| Necesita configuración | No | Sí, un `SONAR_TOKEN` |
| Lee `sonar-project.properties` | Parcialmente | Sí |
| Puede ingerir la **cobertura** | **No** | Sí |
| Bloquea la construcción si el gate falla | No — es un check aparte | Sí, con el paso de Quality Gate |

Los dos modos **no pueden convivir**: si se activa el análisis desde CI sin
apagar el automático, uno de los dos falla con `You are running manual analysis
while Automatic Analysis is enabled`.

### Cuál de los dos está activo, y qué costó descubrirlo

**El automático.** El job `SonarCloud` del pipeline existe desde la semana 5 y
**nunca ha corrido**: comprueba si hay `SONAR_TOKEN` y, si no lo hay, se omite
sin fallar. El check sale **verde** porque omitirse cuenta como éxito.

La consecuencia, descubierta en la auditoría de la semana 9: durante tres
entregas la cobertura **no se midió ni una vez**, aunque la tabla de arriba ya
decía que el análisis automático no puede ingerirla. El conocimiento estaba
escrito; lo que faltaba era notar cuál de los dos modos estaba corriendo.

El README llegó a publicar una insignia de cobertura que renderizaba
literalmente **«Measure has not been found»**. Se retiró: una insignia que
anuncia una métrica inexistente afirma una verificación que no ocurre.

**Qué se hizo en su lugar**, sin tocar la configuración de SonarCloud: la
cobertura se mide ahora en el job `pruebas`, con `--cov-fail-under=85`. Es un
umbral **exigido**, no un dato informativo, y se mide en el único job que
ejecuta las pruebas contra PostgreSQL —sin base de datos, las ramas de los
`repository.py` quedan sin ejecutar y el porcentaje miente a la baja—.

Si algún día se activa el análisis desde CI, la cobertura volverá a aparecer en
SonarCloud y la insignia se puede reponer. Mientras tanto, el número vive donde
se puede exigir.

### Pasos, si se decide hacer el cambio

1. Entrar en el [panel del proyecto](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb)
   con la cuenta de GitHub.
2. **Administration → Analysis Method** y **desactivar** *Automatic Analysis*.
3. En **Administration → Analysis Method → With GitHub Actions**, SonarCloud
   muestra el `SONAR_TOKEN`.
4. Copiar ese valor en GitHub: **Settings → Secrets and variables → Actions →
   New repository secret**, con el nombre exacto `SONAR_TOKEN`.
5. Volver a lanzar el workflow (`Actions → CI → Re-run all jobs`).

Mientras no exista el secreto, el job `calidad` **se omite sin poner el
pipeline en rojo**: registra un aviso y termina. Es deliberado — una
configuración que todavía no existe no es un defecto del código y no debe
impedir que el resto de la construcción sea evaluable.

## 2. Qué se analiza y por qué así

| Ajuste | Valor | Motivo |
|---|---|---|
| `sonar.sources` | `backend/app` | Solo el producto. `backend/scripts/` es instrumental de medición y comparación; mezclarlo confundiría su deuda con la del sistema. |
| `sonar.tests` | `backend/tests` | Declaradas como pruebas, no como fuente. Si fueran fuente, sus aserciones contarían como complejidad del producto y penalizarían al equipo por probar más. |
| `sonar.python.coverage.reportPaths` | `backend/coverage.xml` | Lo genera el pipeline con `pytest --cov`. La ruta es relativa a la raíz del repositorio, no a `backend/`. |
| `fetch-depth: 0` en el checkout | — | Sin historial completo, SonarCloud no puede atribuir cada línea a su commit y la métrica de *código nuevo* queda vacía, que es justo la que mira el Quality Gate. |

### Sobre `pytest-cov` y el lock

El job `pruebas` instala con `--require-hashes` desde `requirements-ci.txt`, y
esa propiedad no se toca. `pytest-cov` vive en su propio lock,
[`backend/requirements-calidad.txt`](../backend/requirements-calidad.txt), con
el mismo régimen: versiones exactas, hashes y solo ruedas.

Están separados porque son cosas distintas: uno declara lo que el producto
necesita para funcionar, el otro lo que este job necesita para medir. Meter el
segundo en el primero obligaría al job de pruebas —y a cualquiera que clone el
repositorio— a instalar algo que no usa.

La primera versión instalaba `pytest-cov` con un rango de versiones y sin
hashes. SonarCloud lo marcó como dos incidencias de seguridad, y con razón:
cualquier versión nueva del paquete o de sus dependencias podía entrar en la
construcción sin que nadie lo hubiera decidido.

## 3. Evidencia para la revisión

Las tres cosas que la retroalimentación pedía, todas disponibles hoy —y
ninguna sirve sola—:

- **URL pública del proyecto:**
  `https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb`
- **Insignia del Quality Gate** en el README, que refleja el estado en vivo:
  ```markdown
  [![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=ISCOUTB_AS_202620_PideUtb&metric=alert_status)](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb)
  ```
- **Run del hash revisado:** el enlace al run de Actions correspondiente al
  commit exacto que se entrega. Un run de un commit anterior no demuestra el
  estado de lo entregado, que es la razón por la que la retroalimentación pide
  explícitamente «el hash revisado».

Los tres se registran en [`correcciones.md`](../correcciones.md) al cerrar la
entrega, con el hash concreto.

## 3 bis. Historial del Quality Gate, y por qué no hay una URL por commit

**Panel del proyecto:**
<https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb>

El análisis automático de SonarCloud **no analiza cada commit**: analiza cuando
detecta cambios, y agrupa varios en un mismo análisis. La consecuencia práctica
es que **no existe una URL de Quality Gate para un hash arbitrario**, y pedirla
por commit no siempre se puede responder. Lo señaló la revisión docente de la
semana 9 al no encontrarla para `a94bf4e`, y la respuesta honesta es esa: ese
commit no tuvo análisis propio.

Lo que sí hay es el historial, consultable con:

```bash
curl -s "https://sonarcloud.io/api/project_analyses/search?project=ISCOUTB_AS_202620_PideUtb&ps=12"
```

Los cambios de veredicto registrados:

| Fecha | Commit | Quality Gate |
|---|---|---|
| 2026-10-01 | `87bdf2ad` | **Green** (venía de Red) |
| 2026-09-30 | `0393eee5` | **Red** (venía de Green) |
| 2026-09-21 | `356369d1` | **Red** (venía de Green) |

Ese historial vale más que una captura en verde: **demuestra que el gate
bloquea de verdad**. El rojo del 30/09 fue una calificación de fiabilidad C por
seis promesas sin manejar en el frontend; el verde del 01/10 es el commit que
las corrigió. Un gate que nunca se ha puesto rojo no ha demostrado nada.

---

## 4. Cobertura

Desde la semana 9 se mide **en el pipeline** y se exige: el job `pruebas` corre
`pytest --cov=app --cov-fail-under=85` y la construcción falla si baja de ahí.

El umbral va por debajo del valor real a propósito. Puesto exactamente en él,
cualquier refactor normal rompería la construcción, y lo que el equipo
aprendería es a subir el umbral en vez de a mirarlo.

Medición local al fijarlo (sin PostgreSQL, así que es el **suelo**: en CI las
ramas de los `repository.py` sí se ejecutan y el valor sube):

```
171 pruebas · 724 sentencias · 88 % de cobertura
```

La cifra anterior de este documento —77 pruebas, 99 %— era de la semana 5 y
quedó obsoleta. Se conserva el dato de entonces solo en el historial de git:
un número viejo presentado como actual es peor que ninguno.

Reproducible con:

```bash
cd backend
pip install --require-hashes --only-binary=:all: -r requirements-calidad.txt
pytest --cov=app --cov-report=term-missing
```

Esta cifra **no aparece en el panel de SonarCloud** mientras el análisis sea el
automático: es la limitación que motiva el cambio descrito en §1.

Las seis sentencias sin cubrir son ramas de traducción de error en los routers
y en `pagos.service`. Están identificadas y no se cubren con una prueba
artificial solo para subir el número: una prueba que existe para mover una
métrica no detecta ningún fallo.

## 5. Qué hacer si el Quality Gate sale en rojo

El gate por defecto («Sonar way») evalúa **código nuevo**, no el histórico. Un
rojo señala algo introducido en el último cambio, y el orden de actuación es:

1. Abrir el enlace del run, que apunta a la incidencia concreta.
2. Si es un defecto real, corregirlo. Es lo que el gate existe para provocar.
3. Si es un falso positivo, marcarlo en SonarCloud como *Won't fix* **con
   justificación escrita**. Un falso positivo silenciado sin motivo es
   indistinguible de un defecto ignorado.
4. No bajar el umbral del gate para que pase. Un gate ajustado a lo que el
   código ya cumple deja de ser una puerta.

---

## 6. Lo que el gate señaló en la semana 10, y qué se hizo con cada cosa

El gate salió **en rojo una vez** y luego en verde con seis avisos no
bloqueantes. Queda aquí el detalle porque un aviso al que nadie respondió por
escrito se convierte en un aviso que el siguiente vuelve a discutir desde cero.

### El que tumbó el gate

| Regla | Dónde | Qué se hizo |
|---|---|---|
| `python:S5863` — aserción que compara la misma expresión consigo misma | `test_autenticacion.py` | **Retirada.** Pretendía comprobar que `hash_de_token` es determinista y no añadía nada: la línea anterior ya compara contra el hash que `nuevo_token` calculó por dentro, así que esa comparación ya son dos cómputos independientes. Se quitó en vez de reescribirla con variables intermedias, que habría silenciado la regla sin atender lo que señalaba |

### Los seis que no bloqueaban

Pasaron el gate igual. Tres se corrigieron porque eran defectos reales, y los
otros tres se dejan con motivo.

| Regla | Dónde | Decisión |
|---|---|---|
| `python:S3457` — f-string sin campos de reemplazo | `usuarios/repository.py` | **Corregido**, y es el que más importa de los seis. Era el único `f"SELECT ..."` del backend sin interpolar nada: un prefijo suelto. No era inocuo — un `f` delante de una cadena SQL invita a que el siguiente escriba `{algo}` dentro sin notar que acaba de abrir una inyección. Las demás consultas sí lo llevan, y sí interpolan `{_COLUMNAS}` |
| `javascript:S7744` — objeto vacío inútil | `panel.js` | **Corregido.** `...(opciones.headers \|\| {})`: esparcir `undefined` en un objeto literal ya no hace nada, así que el `\|\| {}` era código muerto con aspecto defensivo |
| `javascript:S6582` — preferir encadenamiento opcional | `panel.js` | **Corregido.** `guardada?.token && guardada?.usuario` |
| `python:S8409` — `response_model` duplica la anotación de retorno | `usuarios/router.py` | **Corregido después, en todo el backend.** Ver abajo |
| `python:S8410` — usar `Annotated` en las dependencias (×2) | `usuarios/router.py` | **Corregido después, en todo el backend.** Ver abajo |

### Los dos que se dejaron, y por qué se hicieron igual

La decisión inicial fue **no tocarlos**, con este argumento: los cuatro routers
usaban el estilo antiguo, así que cambiar solo `usuarios/router.py` lo volvería
el raro del conjunto, y la regla señalaría igualmente a los otros tres en cuanto
alguien los tocara.

Ese argumento era correcto en su premisa y equivocado en su conclusión. Si el
problema es que cambiar **uno** crea inconsistencia, la respuesta no es dejar el
aviso abierto: es cambiar **los cuatro**. Lo que lo justificaba de verdad era el
alcance —no meter un cambio de convención dentro de una entrega sobre
autenticación—, y eso se resuelve con una rama aparte, no renunciando al cambio.

Hecho así: `response_model` retirado de las **diez** operaciones donde duplicaba
la anotación de retorno, y `Annotated` en las **siete** declaraciones de
parámetro del backend (cuatro `Depends`, dos `Query`, un `Header`), más la
dependencia de `app/autenticacion.py` que Sonar no señalaba porque no está en un
router.

**Queda un `response_model`, y no es un olvido.** `GET /health` se anota
`-> EstadoServicio | JSONResponse`, porque el camino de fallo devuelve una
respuesta 503 ya construida. Ahí la anotación y el modelo publicado **no** son
lo mismo, así que retirarlo haría que FastAPI tomara la unión entera como
esquema. Lleva su comentario en el decorador.

**Lo que da confianza en que el refactor no cambió nada:**
`test_contrato_api.py` compara el OpenAPI que genera la aplicación contra
`docs/api/openapi.yaml`, campo a campo y en las dos direcciones. Si retirar
`response_model` hubiera alterado un solo esquema publicado, esa prueba lo
habría dicho. Pasó sin tocar el contrato, que es exactamente la prueba de que
los dos declaraban lo mismo.

**La regla que se sigue aquí:** un aviso se corrige cuando señala un defecto, y
se deja escrito cuando lo que señala es una convención del proyecto. Lo que no
se hace es marcarlo como *Won't fix* en SonarCloud sin que el motivo esté en el
repositorio: el panel de una herramienta externa no es donde se leen las
decisiones de arquitectura de este proyecto.

### Y lo que sigue sin resolverse: `0.0% Coverage on New Code`

El comentario del gate reporta **0 % de cobertura sobre código nuevo**, con la
suite midiendo **96,41 %** en local y en el job `pruebas`. No es una
contradicción: es exactamente la limitación de §1. Mientras el análisis sea el
**automático**, SonarCloud no ejecuta las pruebas y por tanto no puede ingerir
`coverage.xml`.

Esta semana **no se cambia**, y la decisión es deliberada: cambiar de modo exige
tocar la configuración del proyecto en SonarCloud, que es una acción fuera del
repositorio, y conviene hacerla a la vista y no de pasada dentro de una entrega
sobre otra cosa. Lo que sí se hace es no dejar que el 0 % se lea como un dato
sobre el código: la cobertura real está medida, el comando para reproducirla
está en §4, y el pipeline la exige con `--cov-fail-under=85`.

## 7. Lo que el gate señaló en la semana 16, y qué se hizo con cada cosa

El gate volvió a salir **en rojo**, esta vez con `new_security_rating` en **C**,
y lo señalado era del sitio: `sitio/app.js`. Conviene decir por qué eso es
posible, porque `sonar-project.properties` declara `sonar.sources=backend/app` y
la contradicción desconcierta: el análisis que publica el gate es el
**automático** (§1), que recorre el repositorio entero y no lee ese archivo. La
configuración de ahí gobierna el escaneo del job `SonarCloud`, que se omite sin
`SONAR_TOKEN`. Dicho de otro modo: **el sitio está analizado aunque la
configuración diga que no**, y eso es una suerte, porque los tres hallazgos de
abajo son reales.

### El que tumbó el gate, en dos intentos

| Regla | Dónde | Qué se hizo |
|---|---|---|
| `jssecurity:S7044` — travesía de API por entrada sin sanear, y `jssecurity:S8476` sobre la misma línea | `app.js`, el `fetch` de `api()` | **Corregido en dos pasos**, porque el primero solo tapó uno de los tres caminos. Ver abajo |

El defecto no se ve leyendo la línea. `api(\`/v1/pedidos/${id}\`)` parece pedir
un pedido; con un `id` de `1/../../../v1/sesiones` el navegador resuelve los
`..` antes de enviar y la petición sale hacia `/v1/sesiones`. La dirección que
sale no es la que el código aparenta pedir. Está comprobado y no supuesto: con
la validación quitada, la prueba de abajo ve la petición salir.

**El primer intento** atacó el origen. Guardar el pedido en `localStorage`
había abierto un camino que antes no existía —el `pedido_id` pasó a venir de un
sitio que cualquiera edita desde la consola del navegador—, así que
`leerElPedidoGuardado` lo convierte con `Number` y exige un entero positivo.

**No bastó, y el rastro del segundo análisis explicó por qué.** Quedaban dos
caminos más hacia el mismo `fetch`:

| Camino | Origen que declara Sonar | Por qué el primer arreglo no lo tocaba |
|---|---|---|
| `referencia_pago` → `/v1/pagos/intentos/${ref}` | El almacenamiento | Se validó el identificador y no la referencia, que sale del mismo sitio. Un descuido, no una decisión |
| `pedido_id` → `/v1/pedidos/${id}` en `consultarEstado` | La respuesta de la API | Ese valor nunca pasó por el almacenamiento: llega del servidor. Sonar lo cuenta igual, y tiene su razón —«de fiar» no es lo mismo que «verificado»— |

**El segundo intento** atacó el destino, que es donde la regla se puede
sostener: todo valor que se interpola en una ruta pasa por
`encodeURIComponent`. No sustituye a la validación del identificador, que hace
otra cosa —rechazar pronto lo que no es un pedido y tirar lo que está roto en
el almacenamiento—; la acompaña. Una dice *qué vale*, la otra impide que lo que
vale se convierta en estructura.

Conviene ser honesto sobre el orden: escapar al construir la ruta se descartó
primero, con el argumento de que deja el problema planteado como «qué
caracteres hay que filtrar». El argumento era bueno para el identificador, que
sí tiene un tipo —entero—, y no servía para la referencia de pago, que es texto
libre de hasta 64 caracteres. Para esa, codificar **es** la respuesta. La
referencia real es `pago-{id}-{seis hex}`, así que codificarla no cambia ni un
carácter de las que existen.

Lo cubren dos pruebas, y cada una ve algo distinto:

- `e2e/flujo-completo.spec.js` escribe un identificador manipulado en el
  almacenamiento y comprueba que no sale ninguna petición hacia él, y que lo
  guardado se descarta. Es la prueba del comportamiento.
- `test_todo_lo_que_se_mete_en_una_ruta_va_codificado` recorre `app.js` y
  `panel.js` y exige que toda interpolación dentro de una ruta pase por
  `encodeURIComponent`. Es la prueba de la regla, y se ganó el sitio en cuanto
  se escribió: encontró un cuarto punto que la revisión a ojo había dejado
  pasar, `/v1/menu/establecimientos/${CONFIG.ESTABLECIMIENTO_ID}/items`.

Ese cuarto punto no venía de ningún sitio hostil —sale de `config.js`, que es
nuestro— y se codificó igual. Una regla con una excepción razonable es una
regla que hay que discutir cada vez; sin excepciones se aplica sola. De paso se
corrigió el mismo patrón en `panel.js`, que nadie había señalado todavía.

### Los dos que no bloqueaban

| Regla | Dónde | Decisión |
|---|---|---|
| `javascript:S6582` — preferir encadenamiento opcional | `app.js`, `leerElPedidoGuardado` | **Corregido**, pero de paso: la comprobación de la que se quejaba desapareció al reescribir la función para validar el identificador |
| `javascript:S1135` — «completa la tarea de este `TODO`» | `app.js`, un comentario | **Falso positivo, y conviene saberlo.** No había ninguna tarea pendiente: el comentario decía «antes de **todo** esto». La regla busca líneas de comentario que *empiecen* por `TODO`, y este proyecto está escrito en español, donde «todo» es una palabra corriente. Se reescribió la frase |

Ese último deja una regla práctica para quien escriba aquí: **no empezar una
línea de comentario por la palabra «todo»**. Es más barato que desactivar la
regla, que seguiría haciendo falta el día que alguien deje un `TODO` de verdad.
