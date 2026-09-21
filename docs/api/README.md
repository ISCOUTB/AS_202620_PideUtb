# Contratos de API de PideUTB

Esta carpeta contiene la **fuente única de verdad** de las interfaces del
sistema. El contrato se escribe antes que el código y el pipeline falla si el
código deja de cumplirlo.

| Archivo | Qué describe | Versión |
|---|---|---|
| [`openapi.yaml`](openapi.yaml) | Superficie **síncrona**: menú, pedidos e inicio del cobro | `1.0.0` |
| [`asyncapi.yaml`](asyncapi.yaml) | Canales **asíncronos**: confirmación de pago y evento interno | `1.0.0` |
| [`politica-versionado.md`](politica-versionado.md) | Qué cambios son compatibles, cuáles no, y cómo se avisa | — |
| [`historial/`](historial/) | Versiones congeladas. Referencia contra la que se mide la compatibilidad | — |

El porqué de que haya dos archivos y no uno está en
[ADR-0003](../adr/0003-estrategia-integracion.md): el sistema tiene dos tipos de
integración con modos de fallo distintos, y describirlos con el mismo formato
ocultaría justamente la diferencia que importa.

---

## 1. Las tres capas de validación

Ninguna de las tres detecta lo que detectan las otras dos. Por eso están las
tres y no solo la más vistosa.

| Capa | Herramienta | Pregunta que responde | Dónde corre |
|---|---|---|---|
| **Forma** | Spectral | ¿Es un OpenAPI 3.1 / AsyncAPI 3.0 válido y bien formado? | Job `contrato` |
| **Compatibilidad** | oasdiff + [`comparar_contratos.py`](../../backend/scripts/comparar_contratos.py) | ¿Rompe a un cliente escrito contra la versión anterior? | Job `contrato` + `pytest` |
| **Conformidad** | `pytest` | ¿Lo cumple el código? ¿Y sigue emitiendo lo que el consumidor declaró que lee? | Job `pruebas` |

Una herramienta genérica no puede responder la tercera: no sabe qué campos usa
de verdad nuestro frontend. Y nuestras pruebas no pueden responder la primera:
asumen que el archivo está bien formado para poder compararlo.

### Las pruebas de contrato

| Archivo | Qué comprueba | Casos negativos |
|---|---|---|
| [`test_compatibilidad_contrato.py`](../../backend/tests/test_compatibilidad_contrato.py) | El contrato vigente no rompe la versión congelada | 10 roturas introducidas a propósito, una por regla de la política |
| [`test_contrato_api.py`](../../backend/tests/test_contrato_api.py) | La aplicación implementa exactamente lo declarado, en ambas direcciones | 7 derivas introducidas a propósito |
| [`test_expectativas_consumidor.py`](../../backend/tests/test_expectativas_consumidor.py) | Sigue emitiéndose lo que [`contracts/consumidor-web.yaml`](../../contracts/consumidor-web.yaml) declara leer | 3 retiradas introducidas a propósito |

Los casos negativos no son adorno: **una prueba de contrato que no puede
ponerse en rojo no demuestra nada.** Si alguna de esas veinte mutaciones dejara
de ser detectada, la prueba que la acompaña estaría comprobando el vacío, y las
propias pruebas lo delatarían.

---

## 2. Comprobar el contrato en local

```bash
# Capa 1 — forma
npx --yes @stoplight/spectral-cli@6.15.0 lint \
  docs/api/openapi.yaml docs/api/asyncapi.yaml \
  --ruleset .spectral.yaml --fail-severity=warn

# Capas 2 y 3 — compatibilidad y conformidad
cd backend && pytest tests/test_contrato_api.py \
                     tests/test_compatibilidad_contrato.py \
                     tests/test_expectativas_consumidor.py -v
```

Comparar dos versiones a mano, con el diagnóstico regla a regla:

```bash
cd backend
python scripts/comparar_contratos.py \
  ../docs/api/historial/openapi-1.0.0.yaml \
  ../docs/api/openapi.yaml
```

Termina con código `1` si encuentra algún cambio incompatible, así que sirve
igual en un `pre-commit` que en la terminal.

---

<a id="run-en-rojo"></a>

## 3. Demostrar que la validación puede fallar

> Responde a la observación de la semana 7: *«conservar la evidencia de un run
> en rojo provocado por un cambio incompatible: sin una prueba que pueda fallar,
> la validación no demuestra nada»*.

El procedimiento deja el run rojo **registrado en el historial de Actions** sin
ensuciar `master`, porque se hace en una rama desechable.

### Paso 1 — Rama con un cambio incompatible

```bash
git checkout -b demo/cambio-incompatible
```

Introducir **una sola** rotura en `docs/api/openapi.yaml`. La más clara de
explicar es quitar un campo requerido de una respuesta (regla I-2), porque rompe
a un consumidor que hoy lo lee:

```yaml
# En components.schemas.Pedido, borrar estas dos líneas de `properties`:
#     total_centavos:
#       type: integer
# y borrar `total_centavos` de la lista `required`.
```

### Paso 2 — Comprobar en local que falla antes de subirlo

```bash
cd backend && pytest tests/test_compatibilidad_contrato.py \
                     tests/test_expectativas_consumidor.py
```

La salida es exactamente esta —**3 fallos y 3 omisiones**— y conviene saber
leerla antes de mirarla:

```
FAILED tests/test_compatibilidad_contrato.py::test_el_contrato_vigente_no_rompe_la_linea_base
FAILED tests/test_contrato_api.py::test_la_aplicacion_cumple_el_contrato_publicado
FAILED tests/test_expectativas_consumidor.py::test_todo_campo_que_el_consumidor_lee_sigue_emitiendose
3 failed, 71 passed, 3 skipped
```

**Los tres fallos son las tres capas detectando la misma rotura por caminos
independientes**, que es la demostración de que no se solapan:

| Prueba que falla | Qué detectó |
|---|---|
| `test_el_contrato_vigente_no_rompe_la_linea_base` | I-2 respecto de la versión congelada `1.0.0` |
| `test_la_aplicacion_cumple_el_contrato_publicado` | El código sigue emitiendo el campo que el contrato ya no declara |
| `test_todo_campo_que_el_consumidor_lee_sigue_emitiendose` | `crearPedido → total_centavos` figura en `consumidor-web.yaml` |

**Las tres omisiones son las pruebas de caso negativo que se quedan sin trabajo**:
su mutación consistía precisamente en quitar `total_centavos`, y ya no está.
No fallan, se omiten con el motivo escrito:

```
SKIPPED `_quitar_campo_de_respuesta` ya no aplica sobre el contrato actual
        (KeyError: 'total_centavos'). El contrato base probablemente ya
        contiene ese cambio.
```

Esa distinción entre *fallar* y *omitir* la implementa
[`tests/conftest.py`](../../backend/tests/conftest.py) y existe por este
procedimiento: sin ella, las seis pruebas reventarían con un `KeyError` y el
ruido taparía justo lo que se quiere enseñar. Que una mutación ya no aplique no
significa que el detector esté roto, significa que no hay nada que detectar.

### Paso 3 — Empujar y conservar el enlace

```bash
git commit -am "demo: cambio incompatible para evidenciar la validacion de contrato"
git push -u origin demo/cambio-incompatible
```

El workflow corre sobre la rama (`branches: ["**"]`). Cuando termine en rojo, se
copia la URL del run y se registra en [`../../correcciones.md`](../../correcciones.md).

### Evidencia conservada

[**Run #22**](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35557297196) — commit `adb4077`, conclusión `failure`. Lo que produjo:

| Job | Resultado | Paso que falló |
|---|---|---|
| `Contrato de API` | ❌ | `Detectar cambios incompatibles (oasdiff)` |
| `pytest (Python 3.11)` | ❌ | `Ejecutar pruebas` |
| `pytest (Python 3.12)` | ❌ | `Ejecutar pruebas` |

**Spectral pasó.** Dentro del mismo job, el paso anterior no se quejó: el
archivo seguía siendo un OpenAPI 3.1 válido y bien formado. Lo roto no era la
forma sino la promesa, y esa distinción es exactamente la razón de que haya
tres capas y no una.

### Paso 4 — Limpiar

```bash
git checkout master
git branch -D demo/cambio-incompatible
git push origin --delete demo/cambio-incompatible
```

La rama se borra; **el run queda en el historial de Actions** y sigue siendo
consultable por su URL. Esa URL es la evidencia.

### Por qué en una rama y no en `master`

Un run rojo en `master` deja la rama evaluable en rojo y confunde la evidencia
de que el sistema funciona con la evidencia de que la validación funciona. Son
dos afirmaciones distintas y conviene poder enseñar las dos a la vez: `master`
en verde, y un run rojo reproducible que demuestra que el verde significa algo.

---

## 4. Generar un cliente a partir del contrato

El contrato es ejecutable, así que el cliente no se escribe a mano:

```bash
npx --yes @openapitools/openapi-generator-cli generate \
  -i docs/api/openapi.yaml \
  -g typescript-fetch \
  -o frontend/src/api-generado
```

El generador necesita `operationId` en cada operación —de ahí que
[`.spectral.yaml`](../../.spectral.yaml) lo exija como error— y produce un
método por operación con los tipos de cada esquema.

**Lo generado no se edita a mano ni se versiona con cambios propios.** Si hace
falta tocarlo, lo que hay que cambiar es el contrato y volver a generar: en
cuanto alguien parchea el cliente, el contrato deja de ser la fuente única de
verdad y vuelve a ser documentación.

Para un stub de servidor contra el que probar sin levantar el backend:

```bash
npx --yes @stoplight/prism-cli mock docs/api/openapi.yaml
```

Prism responde con los `examples` declarados en el contrato, que es la razón por
la que [`.spectral.yaml`](../../.spectral.yaml) exige que cada ejemplo valide
contra su propio esquema: un ejemplo incorrecto produciría un stub que enseña al
frontend a esperar algo que la API real nunca enviará.
