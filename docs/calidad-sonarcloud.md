# Análisis estático y Quality Gate (SonarCloud)

> Responde a la observación repetida en la retroalimentación de las semanas 6 y
> 7: *«la evidencia de SonarCloud debe ser auditable: archivo de configuración,
> run del hash revisado y URL pública con el estado del Quality Gate»*.

Los tres elementos exigidos y dónde está cada uno:

| Elemento exigido | Dónde | Estado |
|---|---|---|
| **Archivo de configuración** | [`sonar-project.properties`](../sonar-project.properties) | ✅ En el repositorio |
| **Ejecución en el pipeline** | Job `calidad` de [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | ✅ Definido |
| **URL pública del Quality Gate** | [Panel del proyecto](https://sonarcloud.io/summary/overall?id=ISCOUTB_AS_202620_PideUtb) | ✅ Público y accesible sin cuenta |

Identificadores del proyecto, **verificados contra la API** y no supuestos:

| Dato | Valor |
|---|---|
| `projectKey` | `ISCOUTB_AS_202620_PideUtb` |
| `organization` | `isco-utb` |
| Visibilidad | `public` |

---

## 1. El proyecto ya existe: lo que falta es cambiar de método de análisis

SonarCloud **ya está conectado** al repositorio y analizando, pero mediante
*Automatic Analysis*: el modo en que la aplicación de GitHub lee el código por
su cuenta, sin pasar por el pipeline. Funciona sin configurar nada, y por eso
es el que está activo.

El problema es lo que **no** puede hacer:

| | Automatic Analysis | Análisis desde el pipeline |
|---|---|---|
| Necesita configuración | No | Sí, un `SONAR_TOKEN` |
| Lee `sonar-project.properties` | Parcialmente | Sí |
| Puede ingerir la **cobertura** | **No** | Sí |
| Bloquea la construcción si el gate falla | No — es un check aparte | Sí, con el paso de Quality Gate |

Los dos modos **no pueden convivir**: si se activa el análisis desde CI sin
apagar el automático, uno de los dos falla con `You are running manual analysis
while Automatic Analysis is enabled`.

### Pasos

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

Una vez completado el paso 1, la evidencia auditable son estas tres cosas
juntas —ninguna sirve sola—:

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
