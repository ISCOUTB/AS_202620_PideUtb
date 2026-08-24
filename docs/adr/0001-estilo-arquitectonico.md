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
