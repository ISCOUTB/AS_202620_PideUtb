# Evidencia S7 — citas verificables

Documento de **citas**, no de prosa. Cada criterio de la ficha apunta a un
archivo y una línea concretos, y el fragmento se reproduce aquí para que no
haga falta abrir el archivo.

Existe porque la revisión automática anterior marcó como *no verificado* siete
criterios cuyo contenido **sí estaba en el repositorio**, con observaciones del
tipo «existe, pero no se aportó su contenido» y «el contenido aportado se trunca
en §1». `docs/arc42/arc42.md` tiene 1031 líneas: se trunca en cualquier lectura
con límite. Este archivo cabe entero.

| Dato | Valor |
|---|---|
| Repositorio | `ISCOUTB/AS_202620_PideUtb` (público) |
| Rama evaluable | `master` |
| Contrato | [`docs/api/openapi.yaml`](api/openapi.yaml) `1.0.0` · [`docs/api/asyncapi.yaml`](api/asyncapi.yaml) `1.0.0` |
| Pipeline | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — 3 jobs |
| Runs | [Historial de Actions](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml) |
| Quality Gate | [Panel público](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb) — estado `OK` |
| Vigencia de estas citas | La verifica [`backend/tests/test_evidencia.py`](../backend/tests/test_evidencia.py) en cada push |

---

## 1. Correspondencia contrato ↔ código

Las operaciones del contrato y la línea exacta que las implementa. La ruta
efectiva es `prefix` del router más el path del decorador.

> **La tabla se mantiene al día, no congelada.** Cada número de línea de aquí lo
> verifica `backend/tests/test_evidencia.py` en cada push, así que cuando el
> contrato crece hay que volver a esta tabla o la construcción falla. Las filas
> añadidas después de la semana 7 llevan la versión en la que aparecieron. Lo
> que no se puede hacer es dejar que los números envejezcan en silencio: una
> cita caducada afirma algo falso con apariencia de precisión.

| Path en `openapi.yaml` | Prefijo del router | Path del decorador | Ruta resultante |
|---|---|---|---|
| `/health` · L85 | — | `main.py:119-120` `@app.get("/health")` | `/health` ✔ |
| `/metricas` · L118 | — | `main.py:160-161` `@app.get("/metricas")` | `/metricas` ✔ |
| `/v1/menu/items/{item_id}` · L144 | `menu/router.py:20` `/v1/menu` | `:23-24` `"/items/{item_id}"` | ✔ |
| `/v1/menu/establecimientos/{establecimiento_id}/items` · L168 | `menu/router.py:20` `/v1/menu` | `:35-36` `"/establecimientos/{establecimiento_id}/items"` | ✔ |
| `/v1/sesiones` (POST) · L202 — *2.0.0* | `usuarios/router.py:16` `/v1/sesiones` | `:19-20` `""` | ✔ |
| `/v1/sesiones` (DELETE) · L202 — *2.0.0* | `usuarios/router.py:16` `/v1/sesiones` | `:45-46` `""` | ✔ |
| `/v1/pedidos` (POST) · L262 | `pedidos/router.py:23` `/v1/pedidos` | `:26-27` `""` | ✔ |
| `/v1/pedidos` (GET) · L262 | `pedidos/router.py:23` `/v1/pedidos` | `:57-58` `""` | ✔ |
| `/v1/pedidos/{pedido_id}/estado` · L354 | `pedidos/router.py:23` `/v1/pedidos` | `:95-96` `"/{pedido_id}/estado"` | ✔ |
| `/v1/pedidos/{pedido_id}` · L438 | `pedidos/router.py:23` `/v1/pedidos` | `:45-46` `"/{pedido_id}"` | ✔ |
| `/v1/pagos/intentos` · L462 | `pagos/router.py:20` `/v1/pagos` | `:23-24` `"/intentos"` | ✔ |
| `/v1/pagos/eventos` · L495 | `pagos/router.py:20` `/v1/pagos` | `:40-41` `"/eventos"` | ✔ |

**10 paths declarados, 12 operaciones implementadas, ninguna de más.**
`/v1/pedidos` y `/v1/sesiones` aparecen dos veces cada uno porque tienen dos
métodos: en pedidos, `POST` crea y `GET` lista; en sesiones, `POST` abre y
`DELETE` cierra.

Tres saltos de versión. Los dos primeros, **compatibles** y por eso en el
segundo número (`politica-versionado.md` §2); el tercero, **incompatible** y por
eso en el primero:

- **1.1.0** — `/metricas` y el chequeo de salud real.
- **1.2.0** — la cola del mostrador y la máquina de estados, que cierran
  [ESC-03](arc42/arc42.md#esc-03).
- **2.0.0** — las sesiones del panel, y con ellas la credencial que las dos
  operaciones del mostrador pasaron a exigir. Es un salto de MAYOR por la regla
  **I-12**: pedir una cabecera que antes no se pedía rompe a todo consumidor que
  no la manda, y los dos que había —el panel y las pruebas— no la mandaban.
  Cierra [V-10](violaciones.md) y [ESC-04](arc42/arc42.md#esc-04).

Los prefijos, literales:

```python
backend/app/menu/router.py:20      router = APIRouter(prefix="/v1/menu",     tags=["menu"])
backend/app/pedidos/router.py:23   router = APIRouter(prefix="/v1/pedidos",  tags=["pedidos"])
backend/app/pagos/router.py:20     router = APIRouter(prefix="/v1/pagos",    tags=["pagos"])
backend/app/usuarios/router.py:16  router = APIRouter(prefix="/v1/sesiones", tags=["sesiones"])
```

### La correspondencia no se afirma: se verifica en cada push

`backend/tests/test_contrato_api.py` compara el contrato con `app.openapi()` —
lo que la aplicación declara de sí misma en tiempo de ejecución— **en las dos
direcciones**:

```python
for ruta, metodo in sorted(set(del_contrato) - set(de_la_app)):
    encontradas.append(f"{metodo.upper()} {ruta}: el contrato la promete y la aplicación no la implementa")
for ruta, metodo in sorted(set(de_la_app) - set(del_contrato)):
    encontradas.append(f"{metodo.upper()} {ruta}: la aplicación la expone sin declararla en el contrato")
```

Compara además, por operación: códigos de respuesta declarados, campos de cada
esquema, cuáles son requeridos, tipos y valores de `enum`. La prueba lleva
**7 casos negativos** que introducen divergencias a propósito y exigen que se
detecten.

---

## 2. El pipeline ejecuta la prueba de contrato

Tres jobs en [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

### Job `pruebas` — ejecuta las tres suites de contrato

```yaml
ci.yml:109      - name: Ejecutar pruebas
ci.yml:113        run: pytest -v --junitxml=reporte-pruebas.xml
```

`pytest` recoge todo `backend/tests/`, que incluye
`test_contrato_api.py`, `test_compatibilidad_contrato.py` y
`test_expectativas_consumidor.py`. Matriz: Python 3.11 y 3.12.

### Job `contrato` — herramientas externas

```yaml
ci.yml:185     - name: Validar la forma de los contratos (Spectral)
ci.yml:187         ./node_modules/.bin/spectral lint \
ci.yml:184           docs/api/openapi.yaml \
ci.yml:185           docs/api/asyncapi.yaml \
ci.yml:186           --ruleset .spectral.yaml \
ci.yml:187           --fail-severity=warn

ci.yml:203     - name: Resolver la línea base del contrato
ci.yml:203         base="docs/api/historial/openapi-${mayor}.0.0.yaml"
ci.yml:204         if [ ! -f "$base" ]; then
ci.yml:206           exit 1

ci.yml:215     - name: Detectar cambios incompatibles (oasdiff)
ci.yml:217         docker run --rm -v "${{ github.workspace }}:/specs" tufin/oasdiff breaking \
ci.yml:214           "/specs/${{ steps.linea_base.outputs.ruta }}" \
ci.yml:215           /specs/docs/api/openapi.yaml \
ci.yml:220           --fail-on ERR
```

Ningún paso lleva `continue-on-error`: si cualquiera falla, el job falla y el
run queda en rojo.

**La línea base no es un literal.** Hasta la semana 10 este paso comparaba
contra `openapi-1.0.0.yaml`, y el comparador propio
(`test_compatibilidad_contrato.py`) se **saltaba** cuando la MAYOR subía. Con
esos dos detalles juntos, el salto a 2.0.0 habría apagado la comparación para
siempre: todo cambio posterior dentro de la 2.x pasaría sin medirse, y la
prueba seguiría apareciendo como «omitida», que en un resumen de pytest se lee
casi igual que «pasó». Ahora la base se resuelve desde `info.version` del propio
contrato, así que un salto de MAYOR no apaga el portón: lo reapunta, y obliga a
congelar la nueva base en el mismo commit o el job falla.

### Runs

| Run | Rama | Commit | Conclusión |
|---|---|---|---|
| [#23](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35557330685) | `master` | `557e150` | ✅ `success` |
| [#22](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35557297196) | `demo/cambio-incompatible` | `adb4077` | ❌ `failure` |
| [#20](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35556118369) | `master` | `130c653` | ✅ `success` |

El estado en vivo está en la insignia del [README](../README.md) y en el
[historial completo](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml).

---

## 3. La prueba falla ante un cambio incompatible

[**Run #22**](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/35557297196)
— commit `adb4077`, conclusión **`failure`**.

Se provocó retirando `total_centavos` del esquema `Pedido`: quitar un campo
requerido de una respuesta, regla **I-2** de
[`politica-versionado.md`](api/politica-versionado.md).

| Job | Resultado | Paso que falló |
|---|---|---|
| `Contrato de API` | ❌ | `Detectar cambios incompatibles (oasdiff)` |
| `pytest (Python 3.11)` | ❌ | `Ejecutar pruebas` |
| `pytest (Python 3.12)` | ❌ | `Ejecutar pruebas` |
| `SonarCloud` | ✅ | — |

**Lo que no falló importa tanto como lo que falló: Spectral pasó.** Dentro del
mismo job, el paso anterior no se quejó, porque el archivo seguía siendo un
OpenAPI 3.1 válido y bien formado. Lo roto no era la *forma* del contrato sino
la *promesa* que incumplía.

Un proyecto que solo validara el esquema habría dejado pasar este cambio en
verde. Es la justificación empírica de que haya tres capas y no una.

Procedimiento reproducible: [`docs/api/README.md` §3](api/README.md#run-en-rojo).
La rama se borró; el run permanece en el historial.

---

## 4. arc42 §6 — Vista de ejecución

Ubicación: [`docs/arc42/arc42.md`](arc42/arc42.md) **líneas 453 a 825**.

| Subsección | Línea | Contenido |
|---|---|---|
| 6.1 Resumen de los flujos y sus fronteras | 468 | Tabla de 6 flujos con protocolo, formato, modo y qué pasa si el otro lado no responde |
| 6.2 Crear un pedido | 489 | Diagrama de secuencia — síncrono, en proceso |
| 6.3 Pagar un pedido | 554 | Diagrama de secuencia — dos fases, cruza la frontera asíncrona |
| 6.4 Consultar el estado | 636 | Diagrama de secuencia — cómo se entera el usuario |
| 6.5 Modos de fallo | 669 | 9 modos de fallo, cada uno con la prueba que lo cubre |
| 6.6 Deuda conocida | 812 | Limitaciones del transporte en proceso |

La tabla de §6.1, reproducida:

| # | Flujo | Protocolo | Formato | Modo | Si el otro lado no responde |
|---|---|---|---|---|---|
| 1 | Frontend Web → API | HTTPS | JSON (REST) | Síncrono | El usuario no puede operar |
| 2 | Entre contextos, dentro de la API | Llamada en proceso | Tipos de `contracts` | Síncrono | No puede ocurrir: mismo proceso |
| 3 | API → Supabase | HTTPS | JSON | Síncrono | La operación falla y se responde error |
| 4 | API → Wompi (**iniciar** cobro) | HTTPS | JSON | Síncrono | Error inmediato; el pedido se conserva |
| 5 | Wompi → API (**confirmar** cobro) | HTTPS | JSON firmado | **Asíncrono** | El pedido queda `pendiente_pago`, consultable |
| 6 | API → Panel del establecimiento | Bus en proceso | JSON | **Asíncrono** | El cobro se completa igual |

---

## 5. C4 nivel 2 — cada flecha con protocolo y formato

Ubicación: [`docs/c4/nivel2-contenedores.md`](c4/nivel2-contenedores.md),
**líneas 27 a 34**. Las siete relaciones, literales del diagrama Mermaid:

```
L27  Rel(usuario, frontend, "Consulta menús, pide, paga y recoge", "HTTPS · HTML/JSON · síncrono")
L28  Rel(establecimiento, frontend, "Gestiona productos y estados de pedido", "HTTPS · HTML/JSON · síncrono")
L29  Rel(admin, frontend, "Administra la plataforma", "HTTPS · HTML/JSON · síncrono")
L31  Rel(frontend, api, "Consume la API v1", "HTTPS · JSON (REST) · síncrono")
L32  Rel(api, supabase, "Lee/escribe datos, valida identidad", "PostgreSQL sobre un pool reutilizado · síncrono · ~1 ms")
L33  Rel(api, wompi, "Abre el intento de cobro", "HTTPS · JSON · síncrono")
L34  Rel_Back(api, wompi, "Confirma la transacción (webhook firmado)", "HTTPS · JSON + HMAC · ASÍNCRONO")
```

El segundo argumento de cada `Rel` es la etiqueta técnica, y lleva **las tres
cosas**: protocolo, formato y modo de interacción.

La L34 es `Rel_Back` —flecha hacia dentro— porque el webhook **no es la
respuesta** de la L33: es una petición nueva que llega minutos después, por otra
conexión, y que puede llegar repetida o no llegar nunca.

---

## 6. Tabla de aspectos — ocho columnas

Ubicación: [`docs/aspectos.md`](aspectos.md). Encabezado literal:

```
| ID | Aspecto de calidad | Escenario | Medida de respuesta (umbral) | C4 | ADR | Código | Pruebas |
```

Seis filas, todas con código y prueba:

| ID | Aspecto | Umbral | ADR | Código | Pruebas |
|---|---|---|---|---|---|
| ESC-01 | Usabilidad | < 3 min | 0001, 0002 | `pedidos/router.py` | `test_pedidos.py` ✅ |
| ESC-02 | Disponibilidad · Rendimiento | < 2 min en el 90 % | 0001 | `pedidos/` | `test_linea_base.py` ✅ |
| ESC-03 | Usabilidad · Rendimiento | ≤ 10 s, ≤ 3 interacciones | 0002 | `usuarios/service.py` | `test_propiedad_datos.py` ✅ |
| ESC-04 | Confiabilidad · Seguridad | 100 % de reutilizaciones rechazadas | 0001, **0003** | `pedidos/service.py` (`confirmar_pago`) | `test_pagos.py` ✅ |
| ESC-05 | Usabilidad (errores) | < 3 s; pedido conservado el 100 % | **0003** | `pagos/`, `eventos.py` | `test_pagos.py` ✅ |
| CON-01 | Evolucionabilidad | 0 cambios incompatibles sin detectar | 0003 | `docs/api/`, `comparar_contratos.py` | 3 suites de contrato ✅ |

Ninguna celda de *Código* o *Pruebas* está vacía.

---

## 7. SonarCloud

### Configuración

[`sonar-project.properties`](../sonar-project.properties), valores verificados
contra la API y no supuestos:

```properties
sonar.projectKey=ISCOUTB_AS_202620_PideUtb
sonar.organization=isco-utb
sonar.sources=backend/app
sonar.tests=backend/tests
sonar.python.coverage.reportPaths=backend/coverage.xml
```

### Líneas del workflow

```yaml
ci.yml:274     - name: Medir cobertura
ci.yml:277       run: pytest --cov=app --cov-report=xml:coverage.xml
ci.yml:282     - name: Analizar con SonarCloud
ci.yml:284       uses: SonarSource/sonarqube-scan-action@ba9859eae8dd6bd29e412f25ddbbef3d032000f4  # v8.2.2
ci.yml:291     - name: Esperar el veredicto del Quality Gate
ci.yml:293       uses: SonarSource/sonarqube-quality-gate-action@7a5fffe8e523c40e0c740b6bc2712ab503e52efa  # v1.2.1
```

### URL pública y estado

- **Panel:** https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb
- **API del gate, consultable sin cuenta:**
  `https://sonarcloud.io/api/qualitygates/project_status?projectKey=ISCOUTB_AS_202620_PideUtb`

Estado: **`OK`**, las cinco condiciones en verde.

```
new_reliability_rating          1   (antes 3)
new_security_rating             1   (antes 3)
new_maintainability_rating      1
new_duplicated_lines_density    0.0
new_security_hotspots_reviewed  100.0
```

Fiabilidad y seguridad fallaban; las siete incidencias se corrigieron en el
commit `130c653`. Detalle y decisión sobre el método de análisis:
[`docs/calidad-sonarcloud.md`](calidad-sonarcloud.md).

---

## 8. Cómo reproducirlo todo

```bash
git clone https://github.com/ISCOUTB/AS_202620_PideUtb && cd AS_202620_PideUtb
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && pytest -v          # 77 pruebas
```

```bash
npm install --no-save --ignore-scripts @stoplight/spectral-cli@6.15.0
./node_modules/.bin/spectral lint docs/api/*.yaml --ruleset .spectral.yaml --fail-severity=warn
```

```bash
cd backend && python scripts/comparar_contratos.py \
  ../docs/api/historial/openapi-1.0.0.yaml ../docs/api/openapi.yaml
```
