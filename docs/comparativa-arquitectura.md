# Matriz comparativa de estilos arquitectónicos

Este documento compara tres estilos arquitectónicos posibles para
organizar internamente el backend de PideUTB: **arquitectura por
capas**, **arquitectura hexagonal (puertos y adaptadores)** y
**monolito modular**. El resultado de esta comparación sustenta la
decisión registrada en
[`docs/adr/0001-estilo-arquitectonico.md`](adr/0001-estilo-arquitectonico.md)
y se referencia desde la sección 4 de [`arc42.md`](../arc42.md).

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

## Matriz

| Criterio | Por capas | Hexagonal (puertos y adaptadores) | Monolito modular |
|---|---|---|---|
| Complejidad de implementación | 5 | 2 | 4 |
| Facilidad de testing | 2 | 5 | 4 |
| Acoplamiento con frameworks | 1 | 5 | 3 |
| Curva de aprendizaje | 5 | 2 | 4 |
| Alineación con el tamaño del proyecto | 3 | 2 | 5 |
| Facilidad de despliegue en Vercel | 4 | 3 | 4 |
| **Total** | **20 / 30** | **19 / 30** | **24 / 30** |

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
