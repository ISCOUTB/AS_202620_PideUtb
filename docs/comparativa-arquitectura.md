# Matriz comparativa de estilos arquitectónicos

Este documento compara tres estilos arquitectónicos posibles para
organizar internamente el backend de PideUTB: **arquitectura por
capas**, **arquitectura hexagonal (puertos y adaptadores)** y
**monolito modular**. El resultado de esta comparación sustenta la
decisión registrada en
[`docs/adr/0001-estilo-arquitectonico.md`](adr/0001-estilo-arquitectonico.md)
y se referencia desde la sección 4 de [`arc42.md`](arc42/arc42.md#seccion-4).

## Criterios de evaluación

Los criterios fueron elegidos considerando el contexto real del
proyecto: equipo de tres integrantes generalistas sin roles fijos,
fecha límite del 22/11/2026, sin presupuesto, backend en FastAPI con
persistencia en Supabase, pagos vía Wompi Sandbox, y despliegue previsto
en Vercel.

-   **Complejidad de implementación**: qué tan rápido puede el equipo
    empezar a construir con el estilo, dado que ninguno tiene
    experiencia previa reportada en hexagonal.
-   **Facilidad de testing**: qué tan fácil es aislar y probar la
    lógica de negocio sin depender de la base de datos o de servicios
    externos.
-   **Acoplamiento con frameworks**: qué tan fácil sería cambiar de
    proveedor (por ejemplo, reemplazar Supabase o Wompi) sin reescribir
    la lógica de negocio.
-   **Curva de aprendizaje**: qué tan fácil es para los tres
    integrantes entender y aplicar el estilo de manera consistente.
-   **Alineación con el tamaño del proyecto**: qué tan apropiado es el
    estilo para el alcance real de PideUTB (menú, pedidos, pago,
    código de redención), sin sobreingeniería ni subestructura.
-   **Facilidad de despliegue en Vercel**: qué tan simple resulta
    empaquetar y desplegar el backend con este estilo.

Escala utilizada: **1** (deficiente) a **5** (excelente), en el
contexto específico de este proyecto.

## Matriz por criterios técnicos

| Criterio | Por capas | Hexagonal (puertos y adaptadores) | Monolito modular |
|---|---|---|---|
| Complejidad de implementación | 5 | 2 | 4 |
| Facilidad de testing | 2 | 5 | 4 |
| Acoplamiento con frameworks | 1 | 5 | 3 |
| Curva de aprendizaje | 5 | 2 | 4 |
| Alineación con el tamaño del proyecto | 3 | 2 | 5 |
| Facilidad de despliegue en Vercel | 4 | 3 | 4 |
| **Total** | **20 / 30** | **19 / 30** | **24 / 30** |

## Matriz por escenario del árbol de utilidad

La matriz anterior compara los estilos por criterios técnicos generales. Esta
segunda matriz es la que sustenta la decisión: evalúa, **escenario por
escenario del [árbol de utilidad](arc42/arc42.md#arbol-utilidad)**, qué mejora
y qué empeora con cada estilo. `+` = el estilo favorece el escenario;
`=` = indiferente; `−` = lo perjudica.

| Escenario (prioridad) | Umbral | Por capas | Hexagonal | Monolito modular |
|---|---|---|---|---|
| [**ESC-01**](arc42/arc42.md#esc-01) — Primer pedido de usuario nuevo (A/M) | < 3 min sin errores | `+` Rápido de construir, pero los errores de datos tienden a subir como `500` genéricos | `−` La ceremonia de puertos/adaptadores consume el tiempo que hace falta para pulir el flujo | `+` Rápido de construir **y** con errores específicos por módulo (`404`/`409`) |
| [**ESC-02**](arc42/arc42.md#esc-02) — Pedido en hora pico (A/M) | < 2 min en el 90 % | `=` Un desplegable, sin salto de red, pero sin frontera para optimizar el menú por separado | `=` Igual latencia; los adaptadores facilitarían meter caché después | `+` Sin salto de red y con `repository.py` como frontera para añadir caché de menú. `−` No escala `pedidos` de forma independiente |
| [**ESC-03**](arc42/arc42.md#esc-03) — Gestión de estado por el establecimiento (A/B) | ≤ 10 s, ≤ 3 interacciones | `−` Sin dueño claro del estado: cualquier capa puede escribir la tabla de pedidos | `+` El dominio es dueño del estado por diseño | `+` `pedidos` es dueño único del estado; transición en un solo punto |
| [**ESC-04**](arc42/arc42.md#esc-04) — Verificación del código de recogida (A/M) | < 2 s, 100 % de rechazo de reúso | `−` La validación se dispersa entre controlador y acceso a datos | `+` Un puerto de pagos aísla y hace trivial probar la regla de un solo uso | `=` La regla vive en `pagos.service`; testeable con fixtures, sin puerto formal |
| [**ESC-05**](arc42/arc42.md#esc-05) — Error en el proceso de pago (M/B) | < 3 s, carrito conservado 100 % | `−` El acoplamiento con el SDK de Wompi dificulta simular un rechazo | `+` El adaptador de Wompi se sustituye por un doble de prueba | `=` Se puede aislar Wompi detrás de una función de servicio, sin puerto formal |
| **Balance** | — | Mejora ESC-01 a costa de ESC-03, ESC-04 y ESC-05 | Mejora ESC-03, ESC-04 y ESC-05 a costa de ESC-01, el escenario prioritario | **Mejora ESC-01, ESC-02 y ESC-03 (los tres de prioridad más alta) y queda neutral en ESC-04 y ESC-05** |

**Lectura de la matriz:** hexagonal gana en los escenarios de menor prioridad
(ESC-04 y ESC-05, ambos dependientes de `pagos`, aún no implementado) y pierde
en ESC-01, que es el escenario prioritario. El monolito modular es el único
estilo que no empeora ninguno de los tres escenarios de prioridad alta. El
costo aceptado y explícito es ESC-02: si la medición de carga muestra que el
umbral de hora pico no se cumple, la salida es extraer `pedidos` como servicio
independiente, lo cual el estilo permite sin reescribir el sistema.

## Análisis por estilo

### Arquitectura por capas

Es el estilo más simple de arrancar y el más familiar para el equipo,
pero tiende a acoplar fuertemente la lógica de negocio con el acceso a
datos (Supabase), lo que complica el testing aislado y dificulta un
eventual cambio de proveedor de persistencia o pagos.

### Arquitectura hexagonal

Ofrece el mejor desacoplamiento entre dominio e infraestructura, y por
eso obtiene los puntajes más altos en testing y acoplamiento con
frameworks. Sin embargo, introduce conceptos (puertos, adaptadores,
inversión de dependencias) que ningún integrante del equipo ha aplicado
antes, y esa ceremonia adicional no se justifica para el tamaño y plazo
de PideUTB.

### Monolito modular

Obtiene el puntaje total más alto. Organiza el backend por dominios
(pedidos, menú, pagos, usuarios) sin la sobrecarga de hexagonal,
mantiene una testabilidad razonable si cada módulo separa su lógica
interna, y es más cercano a la forma en que el equipo ya piensa el
proyecto (por funcionalidades). Es también el estilo con mejor balance
general entre las restricciones de tiempo, equipo y tamaño del sistema.

## Resultado

Se selecciona **monolito modular** como estilo arquitectónico para el
backend de PideUTB. La decisión formal, con contexto, alternativas
consideradas y consecuencias, se documenta en el ADR
[`0001-estilo-arquitectonico.md`](adr/0001-estilo-arquitectonico.md).
