# Análisis estático y Quality Gate (SonarCloud)

> Responde a la observación repetida en la retroalimentación de las semanas 6 y
> 7: *«la evidencia de SonarCloud debe ser auditable: archivo de configuración,
> run del hash revisado y URL pública con el estado del Quality Gate»*.

Los tres elementos exigidos y dónde está cada uno:

| Elemento exigido | Dónde | Estado |
|---|---|---|
| **Archivo de configuración** | [`sonar-project.properties`](../sonar-project.properties) | ✅ En el repositorio |
| **Ejecución en el pipeline** | Job `calidad` de [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | ✅ Definido |
| **URL pública del Quality Gate** | Ver §3 | ⚠️ Requiere el alta descrita en §1 |

---

## 1. Alta del proyecto (una sola vez)

El análisis necesita un token que **no puede vivir en el repositorio**: quien lo
tenga puede publicar resultados en nombre del proyecto. Por eso viaja como
secreto de GitHub y no como archivo, y por eso este paso es manual.

1. Entrar en <https://sonarcloud.io> e iniciar sesión con la cuenta de GitHub.
2. **+ → Analyze new project** y elegir el repositorio del curso.
3. En **Set up → With GitHub Actions**, SonarCloud muestra el `SONAR_TOKEN`.
4. Copiar ese valor en el repositorio de GitHub:
   **Settings → Secrets and variables → Actions → New repository secret**,
   con el nombre exacto `SONAR_TOKEN`.
5. **Comprobar `projectKey` y `organization`.** SonarCloud los muestra en
   *Project Information*. Si no coinciden con los de
   [`sonar-project.properties`](../sonar-project.properties), hay que copiarlos
   ahí tal cual: es el error más frecuente y se manifiesta como
   `project not found`.
6. En **Administration → Analysis Method**, desactivar *Automatic Analysis*.
   Si queda activo, entra en conflicto con el análisis del pipeline y uno de
   los dos falla.

Hasta que exista el secreto, el job `calidad` **se omite sin poner el pipeline
en rojo**: registra un aviso y termina. Es deliberado — una configuración que
todavía no existe no es un defecto del código y no debe impedir que el resto de
la construcción sea evaluable.

## 2. Qué se analiza y por qué así

| Ajuste | Valor | Motivo |
|---|---|---|
| `sonar.sources` | `backend/app` | Solo el producto. `backend/scripts/` es instrumental de medición y comparación; mezclarlo confundiría su deuda con la del sistema. |
| `sonar.tests` | `backend/tests` | Declaradas como pruebas, no como fuente. Si fueran fuente, sus aserciones contarían como complejidad del producto y penalizarían al equipo por probar más. |
| `sonar.python.coverage.reportPaths` | `backend/coverage.xml` | Lo genera el pipeline con `pytest --cov`. La ruta es relativa a la raíz del repositorio, no a `backend/`. |
| `fetch-depth: 0` en el checkout | — | Sin historial completo, SonarCloud no puede atribuir cada línea a su commit y la métrica de *código nuevo* queda vacía, que es justo la que mira el Quality Gate. |

### Sobre `pytest-cov` y el lock

El job `pruebas` instala con `--require-hashes` desde `requirements-ci.txt`, y
esa propiedad no se toca. `pytest-cov` se instala **aparte, solo en el job
`calidad`**: es instrumental de ese job y no una dependencia del producto.
Meterlo en el lock obligaría al job de pruebas a instalar algo que no usa, y a
todo el que clone el repositorio también.

## 3. Evidencia para la revisión

Una vez completado el paso 1, la evidencia auditable son estas tres cosas
juntas —ninguna sirve sola—:

- **URL pública del proyecto:**
  `https://sonarcloud.io/summary/overall?id=<projectKey>`
- **Insignia del Quality Gate** en el README, que refleja el estado en vivo:
  ```markdown
  [![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=<projectKey>&metric=alert_status)](https://sonarcloud.io/summary/overall?id=<projectKey>)
  ```
- **Run del hash revisado:** el enlace al run de Actions correspondiente al
  commit exacto que se entrega. Un run de un commit anterior no demuestra el
  estado de lo entregado, que es la razón por la que la retroalimentación pide
  explícitamente «el hash revisado».

Los tres se registran en [`correcciones.md`](../correcciones.md) al cerrar la
entrega, con el hash concreto.

## 4. Cobertura medida en local

Referencia previa al primer análisis, para saber de qué punto se parte:

```
77 pruebas · 412 sentencias · 99 % de cobertura
```

Reproducible con:

```bash
cd backend
pip install "pytest-cov>=5,<7"
pytest --cov=app --cov-report=term-missing
```

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
