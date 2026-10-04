# ADR 0006: No incorporar un componente generativo, y dejar escrito qué lo cambiaría

## Estado

Aceptada — 04/10/2026

## Contexto

La semana 9 pide evaluar la incorporación de un componente generativo al sistema
**por riesgo, costo y latencia**, o justificar su no incorporación. Este ADR
hace lo segundo, pero haciendo antes lo primero: un «no» sin números no es una
evaluación, es una preferencia.

### Los candidatos que el sistema tiene de verdad

Se revisó el sistema entero buscando dónde un modelo haría algo que el código
determinista no hace mejor:

| Candidato | Veredicto |
|---|---|
| **Descripciones automáticas de los ítems** | **Rechazado por seguridad.** Generar «contiene gluten» —o peor, omitirlo— es un riesgo de salud. Un modelo que alucina un alérgeno manda a alguien al hospital. Es el candidato que *parece* más obvio y el que hay que rechazar más rápido |
| **Resumen de la cola para el mostrador** | Una lista ordenada por antigüedad lo hace mejor, siempre igual y gratis |
| **Asistente «¿dónde está mi pedido?»** | La pantalla ya lo dice. Un modelo para repetirlo es ceremonia |
| **«Lo de siempre»** | Es una consulta sobre el historial, no generación |
| **Búsqueda en lenguaje natural de la carta** | **El único defendible.** Es el que se evalúa abajo |

## La alternativa evaluada

**Búsqueda en lenguaje natural sobre la carta.** El usuario escribe «algo barato
y sin carne» y el sistema devuelve los ítems que encajan.

Es plausible: la gente sí busca comida así. Y tiene las tres magnitudes que hay
que medir.

### Proveedor y tarifa

**Claude Haiku 4.5**, el modelo más barato de su familia, por ser la tarea más
simple posible. Tarifa publicada en <https://claude.com/pricing>, consultada el
**04/10/2026**:

| | Precio |
|---|---|
| Entrada | **1 USD por millón de tokens** |
| Salida | **5 USD por millón de tokens** |

### Costo por operación

Supuestos declarados, con su origen:

| Supuesto | Valor | De dónde sale |
|---|---|---|
| Ítems en la carta | 4 | Semilla actual (`migraciones/002_datos_semilla.sql`) |
| Tokens por ítem en el prompt | ~25 | Nombre, precio y disponibilidad |
| Instrucción del sistema | ~150 tokens | Estimación |
| Consulta del usuario | ~15 tokens | «algo barato y sin carne» |
| Respuesta | ~30 tokens | Una lista de identificadores |
| Búsquedas por pedido | 1 | Estimación conservadora: la mayoría no buscaría |
| Pedidos/día | 200 | Mismo supuesto que [`comparacion-despliegue.md`](../comparacion-despliegue.md) §6 |

```
Entrada por búsqueda:  150 + (4 × 25) + 15 = 265 tokens
Salida por búsqueda:                          30 tokens

Costo por búsqueda = (265 / 1e6 × 1) + (30 / 1e6 × 5)
                   = 0,000265 + 0,00015
                   = 0,000415 USD

Al mes: 0,000415 × 200 × 30 = 2,49 USD/mes
```

**≈ 2,50 USD/mes** con el volumen estimado.

### Lo que ese número significa aquí

El sistema entero cuesta hoy **0 USD/mes**, y la primera restricción de
[arc42 §2.1](../arc42/arc42.md) no es «bajo coste»: es **cero y sin tarjeta de
crédito**. El equipo no tiene medio de pago con el que registrarse en ningún
proveedor.

Así que el costo relevante no es 2,50 USD. Es **que no hay forma de pagarlo**, y
eso solo descarta por sí mismo. Pero seguir el análisis vale la pena, porque el
presupuesto puede cambiar y las otras dos magnitudes no.

### Latencia

La búsqueda ocurre **dentro** del recorrido que mide
[ESC-02](../arc42/arc42.md#esc-02): *menos de 2 minutos para el proceso completo
en el 90 % de los intentos*.

| | Medido / estimado |
|---|---|
| p95 del servidor hoy, `POST /v1/pedidos` | **1,58 ms** (`GET /metricas`, entorno desplegado) |
| p95 estimado de una llamada a Haiku | 1–3 s para una respuesta de ~30 tokens |

Una llamada de **2 s** consume el **1,7 %** del presupuesto de 120 s. Por sí
sola no rompe ESC-02.

Pero el contexto importa: el arranque en frío de la plataforma ya se come
**42,4 s medidos** (ver `comparacion-despliegue.md` §10) en la primera petición
de cada pico. Sumar 2 s por búsqueda a un presupuesto del que ya desapareció un
tercio es gastar margen que no sobra.

### Riesgo

| Riesgo | Consecuencia |
|---|---|
| **El proveedor se cae** | La búsqueda deja de funcionar. Aceptable **solo** si hay camino alternativo; sin él, el usuario no puede pedir |
| **El proveedor se degrada** | Respuestas lentas que arrastran el recorrido entero, sin fallar del todo — el modo de fallo más difícil de detectar |
| **Alucina un ítem que no existe** | El usuario pide algo que el establecimiento no vende |
| **Inyección por la entrada** | La consulta del usuario llega al prompt. Se modela en la semana 13 con OWASP; aquí solo se constata que la superficie existiría |
| **Dependencia de una clave de API** | Un secreto más que custodiar, en un proyecto que acaba de descubrir uno publicado ([V-11](../violaciones.md)) |

## Decisión

**No se incorpora un componente generativo.**

Tres motivos, en orden de peso:

**1. Existe la alternativa determinista, y es mejor.** Con 4 ítems en la carta,
un filtro por precio y etiquetas da el mismo resultado en **milisegundos**,
gratis, sin alucinar y sin caerse. No es que el modelo sea caro: es que no
aporta nada que el filtro no haga ya.

**2. El presupuesto es cero y sin tarjeta.** 2,50 USD/mes es poco dinero y es,
aun así, infinitamente más de lo que el equipo puede pagar.

**3. Añadiría un modo de fallo externo a un camino crítico.** El sistema tiene
hoy una sola dependencia que no controla —la pasarela— y está deliberadamente
fuera del camino síncrono ([ADR-0003](0003-estrategia-integracion.md)). Meter
una segunda, y dentro del flujo de búsqueda, contradice esa decisión.

## Qué cambiaría esta decisión

Se declara para que el «no» sea revisable y no una postura:

| Si ocurre | Por qué cambia el cálculo |
|---|---|
| **La carta pasa de 4 a ~200 ítems**, con varios establecimientos | El filtro por etiquetas deja de servir: nadie etiqueta 200 platos de forma consistente. El costo por búsqueda sube con el tamaño del prompt y habría que recalcularlo |
| **Aparece presupuesto y medio de pago** | Desaparece el motivo 2, pero no el 1 ni el 3 |
| **Llegan consultas en texto libre que el filtro no cubre** | Por ejemplo reclamaciones escritas. Sería clasificación, no búsqueda, y fuera del camino crítico: mejor candidato que este |

## Si algún día se incorpora

Lo que este ADR deja preparado, para no improvisarlo entonces:

**Conjunto de evaluación con umbrales.** Un fichero de consultas reales con el
resultado esperado:

| Consulta | Debe devolver |
|---|---|
| «algo barato» | Los ítems por debajo de la mediana de precio |
| «sin carne» | Ningún ítem con carne |
| «algo que no existe en la carta» | Lista vacía, **no una invención** |
| «'; DROP TABLE pedidos; --» | Lista vacía, y nada ejecutado |

Umbrales propuestos: **100 % en el caso de la lista vacía** —alucinar un ítem es
el fallo que más daña la confianza— y **≥ 90 %** en los de filtrado.

**Comportamiento ante fallo o degradación del proveedor**, que es lo que el
enunciado exige declarar: el sistema **cae al filtro determinista**, no muestra
un error. La búsqueda inteligente sería una mejora sobre un camino que ya
funciona, nunca el único camino. Con un tiempo límite de **2 s**: pasado eso se
responde con el filtro, porque una búsqueda lenta es peor que una búsqueda
simple.

**C4 nivel 2**: aparecería como contenedor externo, con protocolo
`HTTPS · JSON · síncrono` y su costo anotado, igual que la pasarela.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Restricción de presupuesto | [arc42 §2.1](../arc42/arc42.md) |
| Escenario afectado por la latencia | [ESC-02](../arc42/arc42.md#esc-02) |
| Tarifa citada | <https://claude.com/pricing>, consultada el 04/10/2026 |
| p95 actual del servidor | `GET /metricas` del entorno desplegado |
| Arranque en frío medido | [`comparacion-despliegue.md`](../comparacion-despliegue.md) §10 |
| Decisión que esta respeta | [ADR-0003](0003-estrategia-integracion.md) — una sola dependencia externa, fuera del camino síncrono |
| Uso de IA en el desarrollo (distinto de esto) | [`docs/ia.md`](../ia.md) |
