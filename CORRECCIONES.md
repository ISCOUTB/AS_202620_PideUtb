# Correcciones a la retroalimentación docente — PideUTB

**Equipo:** `Santiago-C0` · `daniarriet` · `ruddy2000utb-droid`
**Repositorio:** https://github.com/ISCOUTB/AS_202620_PideUtb
**Rama evaluable:** `master`
**Estado de CI:** ✅ verde — [run #3](https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534) (commit `ae52cca`, 5 pruebas en Python 3.11 y 3.12)

Este documento resume, para la nueva revisión, qué se corrigió de la
retroalimentación de las semanas 1 a 5 y dónde quedó cada evidencia. El detalle
punto por punto está en [`docs/correcciones.md`](docs/correcciones.md).

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
| Restricción del reto y línea base | [`docs/restriccion-s5.md`](docs/restriccion-s5.md) | no existía |

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
- **Run en verde:** https://github.com/ISCOUTB/AS_202620_PideUtb/actions/runs/34160302534
- Se añadió `backend/scripts/medir_linea_base.py` y la prueba de regresión
  `backend/tests/test_linea_base.py`. **Línea base medida** sobre 300 peticiones
  a `POST /pedidos`: p50 **2,85 ms**, p95 **3,32 ms**
  ([detalle y método](docs/restriccion-s5.md)).

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

## 3. Qué sigue pendiente y por qué

Declaramos estos puntos abiertamente en lugar de darlos por cerrados:

| Pendiente | Motivo |
|---|---|
| **Restricción asignada de S5** ([`docs/restriccion-s5.md`](docs/restriccion-s5.md) §1) | El enunciado lo asigna el docente y no lo tenemos registrado. Preferimos dejar la sección marcada como pendiente antes que documentar una restricción supuesta, que produciría un diagnóstico no verificable. El punto de medición sí está diagnosticado (§2) y la línea base medida (§3) |
| **ADR del reto (`0002`)** y contraste contra el umbral | Dependen del punto anterior. La tabla de contraste ya está preparada en §6 |
| **Etiqueta `corte-1`** | El docente indicó crearla sobre el commit de la próxima entrega. No la creamos sobre trabajo posterior al cierre porque equivaldría a presentar como entrega del corte algo que llegó tarde |
| **Reparto de contribución** | Depende del equipo, no del repositorio. El historial muestra 3 cuentas, con participación desigual |

## 4. Cómo verificar

```bash
git clone https://github.com/ISCOUTB/AS_202620_PideUtb
cd AS_202620_PideUtb

# Documentación en las rutas exigidas
ls docs/arc42/ docs/c4/ docs/adr/

# Pruebas (5 en verde)
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -v

# Línea base de rendimiento
python scripts/medir_linea_base.py 300
```

Historial de CI: https://github.com/ISCOUTB/AS_202620_PideUtb/actions/workflows/ci.yml
