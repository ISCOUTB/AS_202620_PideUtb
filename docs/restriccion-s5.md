# Restricción del reto (S5) — diagnóstico, línea base y verificación

Este documento sigue la cadena que exige la entrega: **restricción → diagnóstico
→ línea base medida → decisión (ADR) → implementación → prueba en CI →
contraste contra el umbral**.

> ⚠️ **Estado:** la línea base ya está medida y automatizada (secciones 2 a 4).
> La sección 1 (restricción asignada) requiere el enunciado que asigna el
> docente; el equipo debe transcribirlo aquí antes de la sustentación. Las
> secciones 5 y 6 se completan una vez definida esa restricción.

## 1. Restricción asignada

**Pendiente de transcribir.** Debe registrarse aquí, textualmente, la
restricción entregada por el docente, junto con:

- El **umbral** cuantitativo que impone.
- El **escenario del árbol de utilidad** al que afecta
  ([ESC-01](arc42/arc42.md#esc-01) … [ESC-05](arc42/arc42.md#esc-05)).
- La **fecha** en que se asignó.

No se documenta una restricción supuesta: hacerlo produciría un diagnóstico no
verificable.

## 2. Diagnóstico del punto de medición

El corte vertical implementado es la creación de un pedido
(`POST /pedidos`), descrito en
[arc42 §6.1](arc42/arc42.md#runtime-crear-pedido). Es el único flujo que
atraviesa un límite entre módulos de dominio, y por tanto el único punto donde
hoy se puede medir el efecto real de la decisión arquitectónica
([ADR-0001](adr/0001-estilo-arquitectonico.md)):

```
Cliente → pedidos.router → pedidos.service → menu.service.obtener_item() → menu.repository
```

Lo que la arquitectura controla en este flujo es el costo de cruzar ese límite.
En el monolito modular es una llamada en proceso; si el módulo se extrajera
como servicio, ese mismo cruce pasaría a ser una llamada de red. La línea base
es, por tanto, la referencia contra la cual se evaluará cualquier cambio
estructural futuro.

**Lo que esta medición no es:** una prueba de carga. No hay concurrencia ni
usuarios simultáneos, así que **no verifica** el umbral de
[ESC-02](arc42/arc42.md#esc-02) (< 2 min en el 90 % de los intentos en hora
pico). Verificar ESC-02 requiere una prueba de carga con clientes concurrentes,
prevista para S6.

## 3. Línea base medida

Instrumento: [`backend/scripts/medir_linea_base.py`](../backend/scripts/medir_linea_base.py).
Método: 10 peticiones de calentamiento descartadas, luego 300 peticiones
`POST /pedidos` medidas con `time.perf_counter()`.

```
$ cd backend && python scripts/medir_linea_base.py 300

Línea base POST /pedidos  (n=300 peticiones)
  min  : 2.26 ms
  p50  : 2.85 ms
  p95  : 3.32 ms
  max  : 7.84 ms
```

| Métrica | Valor |
|---|---|
| Muestras | 300 peticiones |
| Mínimo | 2,26 ms |
| **p50** | **2,85 ms** |
| **p95** | **3,32 ms** |
| Máximo | 7,84 ms |
| Fecha de la medición | 2026-09-07 |
| Entorno | Contenedor Linux, Python 3.11, FastAPI `TestClient` en proceso, sin base de datos externa (repositorio en memoria) |

El repositorio todavía es en memoria: cuando se conecte Supabase esta línea
base debe volver a medirse, porque el acceso a datos pasará a dominar el
tiempo total.

## 4. Verificación automática

La línea base está protegida por una prueba de regresión que corre en CI:

- Prueba: `backend/tests/test_linea_base.py::test_p95_de_crear_pedido_bajo_umbral`
- Umbral: **p95 < 50 ms** sobre 100 peticiones
- Pipeline: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

El umbral se fijó ~15× por encima del p95 medido en local, no en el valor
medido: los runners compartidos de GitHub Actions tienen una varianza mucho
mayor que la máquina de desarrollo, y un umbral ajustado produciría fallos
intermitentes. Con 50 ms la prueba sigue detectando una regresión de orden de
magnitud —que es lo que un cambio arquitectónico equivocado produciría— sin
volverse inestable.

## 5. Cambio implementado en respuesta a la restricción

**Pendiente** — depende de la sección 1.

## 6. Contraste del resultado contra el umbral

**Pendiente** — depende de las secciones 1 y 5. La tabla a completar es:

| Métrica | Línea base (S5) | Después del cambio | Umbral de la restricción | ¿Cumple? |
|---|---|---|---|---|
| p95 de `POST /pedidos` | 3,32 ms | — | — | — |

## Trazabilidad

| Elemento | Referencia |
|---|---|
| Escenarios relacionados | [ESC-01](arc42/arc42.md#esc-01), [ESC-02](arc42/arc42.md#esc-02) |
| Decisión vigente | [ADR-0001](adr/0001-estilo-arquitectonico.md) |
| ADR del reto | Pendiente — será `docs/adr/0002-*.md` |
| Índice de aspectos | [`docs/aspectos.md`](aspectos.md) |
