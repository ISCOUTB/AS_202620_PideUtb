# Línea base de rendimiento — `POST /pedidos`

Medición de referencia del corte vertical implementado: qué se mide, con qué
instrumento, con qué resultado, y cómo se protege de regresiones en CI.

> **Nota sobre el reto de la semana 5.** Este documento nació para sostener la
> cadena *restricción → diagnóstico → línea base → ADR → prueba → contraste*.
> El docente retiró esa restricción de las exigencias, así que las secciones que
> dependían de su enunciado se eliminaron. Lo que se conserva es la medición,
> que sigue siendo evidencia válida y viva: es la referencia contra la que se
> contrastó el reajuste de límites de contexto de
> [ADR-0002](adr/0002-propiedad-datos-establecimiento.md), y la protege una
> prueba de regresión en cada push.

## 1. Qué se mide y por qué

El corte vertical implementado es la creación de un pedido (`POST /pedidos`),
descrito en [arc42 §6.1](arc42/arc42.md#runtime-crear-pedido). Es el flujo que
**atraviesa las fronteras entre contextos delimitados**, y por tanto el único
punto donde hoy se puede medir el efecto real de las decisiones arquitectónicas
([ADR-0001](adr/0001-estilo-arquitectonico.md) y
[ADR-0002](adr/0002-propiedad-datos-establecimiento.md)):

```
Cliente → pedidos.router → pedidos.service ─┬→ menu.service.obtener_item()
                                            └→ usuarios.service.establecimiento_esta_activo()
```

Lo que la arquitectura controla aquí es el coste de cruzar esas fronteras. En el
monolito modular son llamadas en proceso; si un contexto se extrajera como
servicio, ese mismo salto pasaría a ser una llamada de red. La línea base es la
referencia contra la cual evaluar cualquier cambio estructural futuro —y el dato
que permite estimar qué costaría esa extracción.

**Lo que esta medición no es:** una prueba de carga. No hay concurrencia ni
usuarios simultáneos, así que **no verifica** el umbral de
[ESC-02](arc42/arc42.md#esc-02) (< 2 min en el 90 % de los intentos en hora
pico). Verificar ESC-02 exige clientes concurrentes, y queda pendiente.

## 2. Método e instrumento

Instrumento: [`backend/scripts/medir_linea_base.py`](../backend/scripts/medir_linea_base.py).
Método: 10 peticiones de calentamiento descartadas, luego 300 peticiones
`POST /pedidos` medidas con `time.perf_counter()`.

```bash
cd backend && python scripts/medir_linea_base.py 300
```

## 3. Resultado

```
Línea base POST /pedidos  (n=300 peticiones)
  min  : 2.36 ms
  p50  : 2.66 ms
  p95  : 3.02 ms
  max  : 21.18 ms
```

| Métrica | Valor |
|---|---|
| Muestras | 300 peticiones |
| Mínimo | 2,36 ms |
| **p50** | **2,66 ms** |
| **p95** | **3,02 ms** |
| Máximo | 21,18 ms |
| Fecha de la medición | 2026-09-13 |
| Entorno | Contenedor Linux, Python 3.12, FastAPI `TestClient` en proceso, repositorios en memoria |

### Evolución entre entregas

| Momento | Llamadas entre contextos | p50 | p95 |
|---|---|---|---|
| Corte 1 (antes de ADR-0002) | 1 (`menu`) | 2,85 ms | 3,32 ms |
| **Tras ADR-0002** | **2** (`menu` + `usuarios`) | **2,66 ms** | **3,02 ms** |

El dato relevante: al **duplicar** las llamadas entre contextos el p95 no subió,
bajó. El salto entre contextos sigue siendo en proceso y su coste es
indistinguible del ruido de medición. Esto respalda lo que afirma
[ADR-0002](adr/0002-propiedad-datos-establecimiento.md): dar un dueño único a
`Establecimiento` no costó rendimiento, y lo que sí costaría es extraer un
contexto como servicio, porque ese mismo salto pasaría a ser de red.

Los repositorios siguen siendo en memoria: cuando se conecte Supabase habrá que
volver a medir, porque el acceso a datos pasará a dominar el tiempo total
(ver [V-09](violaciones.md#v-09)).

## 4. Protección en CI

La línea base está protegida por una prueba de regresión que corre en cada push:

- Prueba: `backend/tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral`
- Umbral: **p95 < 50 ms** sobre 100 peticiones
- Pipeline: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

El umbral se fijó muy por encima del p95 medido en local, no en el valor
medido: los runners compartidos de GitHub Actions tienen una varianza mucho
mayor que la máquina de desarrollo, y un umbral ajustado produciría fallos
intermitentes. Con 50 ms la prueba sigue detectando una regresión de orden de
magnitud —que es lo que un cambio arquitectónico equivocado produciría— sin
volverse inestable.

## Trazabilidad

| Elemento | Referencia |
|---|---|
| Escenarios relacionados | [ESC-01](arc42/arc42.md#esc-01), [ESC-02](arc42/arc42.md#esc-02) |
| Decisiones que contrasta | [ADR-0001](adr/0001-estilo-arquitectonico.md), [ADR-0002](adr/0002-propiedad-datos-establecimiento.md) |
| Contextos que atraviesa | [`docs/ddd-contextos.md` §2](ddd-contextos.md) |
| Deuda que afecta a la medición | [V-09](violaciones.md#v-09) — estado en memoria |
| Índice de aspectos | [`docs/aspectos.md`](aspectos.md), fila ESC-02 |
