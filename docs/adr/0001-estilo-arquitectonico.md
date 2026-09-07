# ADR 0001: Estilo arquitectónico del backend de PideUTB

## Estado

Aceptada — 23/08/2026

## Contexto

PideUTB necesita una organización interna clara para el código del
backend antes de que el equipo empiece a implementar lógica de negocio
en la semana 4. El backend se construye en FastAPI (Python), persiste
datos en Supabase (PostgreSQL) y se integra con Wompi en ambiente
Sandbox para pagos. El equipo está compuesto por tres integrantes
full-stack generalistas, sin roles fijos ni experiencia previa
reportada en arquitectura hexagonal, con fecha límite del 22/11/2026 y
sin presupuesto para el proyecto.

Era necesario decidir un estilo arquitectónico para el backend que
permitiera:

-   Empezar a construir rápidamente, dado el equipo y el plazo
    disponibles.
-   Mantener una separación razonable entre la lógica de negocio y los
    detalles de infraestructura (Supabase, Wompi).
-   Facilitar el testing automatizado de la lógica de negocio.
-   Ser comprensible y aplicable de forma consistente por los tres
    integrantes del equipo.
-   No sobredimensionar la arquitectura para un sistema del tamaño de
    PideUTB (menú, pedidos, pago, código de redención).

## Alternativas consideradas

La comparación detallada con criterios y puntajes se encuentra en
[`docs/comparativa-arquitectura.md`](../comparativa-arquitectura.md).
Resumen:

### 1. Arquitectura por capas

Organización tradicional en capas técnicas horizontales (presentación,
lógica de negocio, acceso a datos).

-   **Pros**: es el estilo más simple y conocido por el equipo; permite
    arrancar de inmediato.
-   **Contras**: tiende a acoplar fuertemente la lógica de negocio con
    el acceso a datos concreto, dificultando el testing aislado y un
    eventual cambio de proveedor de persistencia o pagos.

### 2. Arquitectura hexagonal (puertos y adaptadores)

El dominio queda aislado de la infraestructura mediante puertos
(interfaces) y adaptadores concretos (Supabase, Wompi, HTTP).

-   **Pros**: mejor desacoplamiento posible entre dominio e
    infraestructura; facilita testing puro del dominio y el reemplazo
    de proveedores externos.
-   **Contras**: introduce conceptos nuevos (puertos, adaptadores,
    inversión de dependencias) que ningún integrante ha aplicado antes;
    la curva de aprendizaje y la ceremonia adicional no se justifican
    para el tamaño y plazo del proyecto.

### 3. Monolito modular

Un único desplegable organizado internamente en módulos de dominio
(pedidos, menú, pagos, usuarios), cada uno con su propia separación
interna de responsabilidades, sin la ceremonia completa de hexagonal.

-   **Pros**: buen balance entre simplicidad y organización; separa
    dominios sin sobreingeniería; cercano a la forma en que el equipo
    ya piensa el proyecto (por funcionalidades); despliegue simple en
    Vercel al no introducir capas adicionales de indirección.
-   **Contras**: el desacoplamiento entre dominio e infraestructura es
    más débil que en hexagonal; requiere disciplina del equipo para no
    degenerar en acoplamiento entre módulos con el tiempo.

## Decisión

Se adopta **monolito modular** como estilo arquitectónico para el
backend de PideUTB.

El backend se organiza en un único desplegable, dividido en paquetes de
dominio (por ejemplo: `pedidos`, `menu`, `pagos`, `usuarios`). Cada
módulo mantiene internamente su propia separación de responsabilidades
(rutas/API, lógica de aplicación, acceso a datos) y expone una interfaz
explícita hacia los demás módulos, evitando el acceso directo al detalle
interno de otro módulo.

## Consecuencias

-   El código se organiza por **dominio**, no por tipo técnico: no
    existirá una carpeta única `models/` o `controllers/` para todo el
    sistema, sino paquetes como `pedidos/`, `menu/`, `pagos/` y
    `usuarios/`, cada uno con su propia estructura interna.
-   La comunicación entre módulos debe hacerse a través de funciones o
    clases de servicio expuestas explícitamente, no accediendo
    directamente a las tablas o al almacenamiento interno de otro
    módulo.
-   El testing automatizado deberá apoyarse en mocks o fixtures simples
    para aislar la lógica de cada módulo, sin la garantía estructural
    que ofrecería hexagonal.
-   Esta decisión es revisable: si en una entrega posterior algún
    módulo (por ejemplo, la integración con Wompi) necesita mayor
    desacoplamiento, podrá evolucionar puntualmente hacia un estilo tipo
    puerto/adaptador sin necesidad de reescribir todo el sistema. Ese
    cambio debería documentarse en un nuevo ADR.
-   El esqueleto ejecutable del repositorio (paquetes vacíos, prueba
    automatizada base y comando único de arranque documentado en el
    README) refleja ya esta organización, de modo que la semana 4 pueda
    iniciar directamente con lógica de negocio dentro de esta
    estructura.

## Trazabilidad

Qué escenario motiva esta decisión, dónde se ve, qué commit la implementa y
qué prueba la verifica.

| Elemento | Referencia |
|---|---|
| **Escenario que la motiva** | [ESC-01 — Primer pedido de un usuario nuevo](../arc42/arc42.md#esc-01) (prioridad A/M): el umbral de < 3 min sin errores de navegación exige un estilo que el equipo pueda construir dentro del plazo y que permita mensajes de error específicos por módulo |
| **Escenarios adicionales afectados** | [ESC-02](../arc42/arc42.md#esc-02) (favorecido: sin salto de red entre módulos; costo aceptado: sin escalado independiente), [ESC-03](../arc42/arc42.md#esc-03) (favorecido: dueño único del estado del pedido) |
| **Estrategia de solución (arc42)** | [§4.2 estilo elegido](../arc42/arc42.md#seccion-4) · [§4.3 motivación por escenario](../arc42/arc42.md#seccion-4) · [§4.4 tácticas por escenario](../arc42/arc42.md#tacticas-por-escenario) |
| **Análisis que la sustenta** | [Matriz comparativa](../comparativa-arquitectura.md), incluida la [matriz por escenario](../comparativa-arquitectura.md) |
| **Diagrama C4 que la refleja** | [Nivel 3 — módulos internos de la API](../c4/nivel3-modulos.md): los cuatro paquetes de dominio y la regla de comunicación por función pública de servicio |
| **Commit que la implementa (esqueleto)** | `b5f0310` — *Entrega 3: arc42 sección 4, matriz comparativa, ADR 0001 y esqueleto ejecutable (monolito modular)*: crea `backend/app/{pedidos,menu,pagos,usuarios}/` |
| **Commit que la ejercita (corte vertical)** | `2e165bb` — *Refactor FastAPI app and add routers*: `pedidos` llama a `menu` únicamente a través de `menu.service.obtener_item()` |
| **Código que materializa la regla** | `backend/app/pedidos/service.py` (llama a la función pública de `menu`, nunca a `menu/repository.py`) · `backend/app/menu/service.py` (interfaz pública del módulo) · `backend/app/pedidos/router.py` (`POST /pedidos`) |
| **Pruebas que la verifican** | `backend/tests/test_pedidos.py::test_crear_pedido_exitoso` (el flujo cruza el límite entre módulos y responde `201`) · `::test_crear_pedido_item_no_encontrado` (`404`) · `::test_crear_pedido_item_no_disponible` (`409`) — los dos últimos comprueban que la validación vive en `menu` y no se filtra como error genérico |
| **Verificación automática** | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) ejecuta `pytest` en cada push y pull request |
| **Índice de trazabilidad** | Fila ESC-01 de [`docs/aspectos.md`](../aspectos.md) |
