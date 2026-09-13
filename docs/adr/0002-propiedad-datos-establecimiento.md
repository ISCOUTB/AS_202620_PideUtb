# ADR 0002: Propiedad de los datos de Establecimiento y lenguaje publicado entre contextos

## Estado

Aceptada — 13/09/2026

*(El equipo revisó y aceptó la decisión al implementarla. Si prefieren dejarla
en discusión, basta cambiar esta línea a «Propuesta» y revertir el commit que
implementa el módulo `usuarios`.)*

## Contexto

La auditoría de modularidad de la semana 6
([`docs/ddd-contextos.md`](../ddd-contextos.md)) encontró dos problemas que la
estructura de carpetas no dejaba ver.

**1. `Establecimiento` no tenía dueño.** `establecimiento_id` se referencia como
un entero simple en `backend/app/menu/models.py` (`ItemMenu.establecimiento_id`)
y en `backend/app/pedidos/models.py` (`Pedido.establecimiento_id`), pero ningún
módulo era dueño de los datos reales del establecimiento (nombre, ubicación,
horario). No era una violación de «un solo escritor por dato» —porque nadie los
escribía—, pero es el mismo riesgo en su forma inversa: **un dato sin dueño
tiende a terminar con dos dueños** en cuanto dos módulos necesitan mostrarlo.

El riesgo dejó de ser hipotético: la ausencia de dueño tenía ya una consecuencia
reproducible. `pedidos` aceptaba `establecimiento_id` del cliente HTTP y lo
escribía sin contrastarlo, de modo que un pedido podía quedar asignado a un
establecimiento que no vende ese producto o que no existe
([V-01](../violaciones.md#v-01), [V-02](../violaciones.md#v-02)).

Y se agrava en la próxima entrega: tanto `pagos` (que deberá mostrar en qué
establecimiento se recoge el pedido) como `usuarios` (que deberá autenticar al
personal de un establecimiento) van a necesitar esos datos. Sin una decisión
explícita, lo probable es que cada uno guarde su propia copia.

**2. El modelo interno de un contexto se filtraba en otro.**
`menu.service.obtener_item()` devolvía la entidad `ItemMenu`, así que
`pedidos.service` manipulaba un tipo del contexto vecino. La regla de
[ADR-0001](0001-estilo-arquitectonico.md) prohíbe importar los `models` de otro
módulo, pero no impedía recibir sus instancias como valor de retorno: la
frontera existía en el import y no en el tipo
([V-05](../violaciones.md#v-05)).

## Alternativas consideradas

### Para la propiedad de `Establecimiento`

**1. Crear un quinto módulo `establecimientos`.**

- **Pros:** separa con máxima claridad «quién soy» (cuenta y autenticación) de
  «qué vendo» (catálogo); evita que `usuarios` crezca demasiado.
- **Contras:** el equipo ya evaluó en [ADR-0001](0001-estilo-arquitectonico.md)
  que la fragmentación excesiva no se justifica para el tamaño de PideUTB. Un
  establecimiento **es**, en la práctica, un tipo de cuenta con permisos
  distintos a los de un usuario común, no un concepto de negocio separado con
  ciclo de vida propio.

**2. Asignar la propiedad a `menu`.**

- **Pros:** el catálogo ya cuelga del establecimiento, y `menu` está
  implementado, así que la corrección sería inmediata.
- **Contras:** **contradice lo que el equipo ya había escrito.**
  [arc42 §5.3](../arc42/arc42.md#responsabilidad-modulos) asigna al módulo
  `usuarios` la responsabilidad *«Autenticación y roles (usuario: estudiante o
  profesor / establecimiento / admin)»*. Crear un dueño distinto en el código
  dejaría dos respuestas contradictorias a la misma pregunta dentro de la propia
  documentación.

**3. Dejar `establecimiento_id` sin dueño (statu quo).**

- **Pros:** ningún cambio inmediato.
- **Contras:** es exactamente el riesgo que la auditoría detectó, y ya se está
  materializando en V-01.

**4. Modelar `Establecimiento` dentro de `usuarios` — elegida.**

- **Pros:** no agrega un módulo nuevo; reutiliza la responsabilidad que arc42
  §5.3 ya le asignaba; mantiene los cuatro módulos de ADR-0001; un solo
  `service.py` resuelve tanto la autenticación de cuentas como los datos de
  establecimientos, que comparten ciclo de vida (una cuenta) y mecanismo de
  acceso (login).
- **Contras:** `usuarios` concentra dos responsabilidades relacionadas pero
  distintas: identidad de personas y datos de negocios. Se acepta el coste por
  la misma razón de tamaño de equipo y plazo que sustentó ADR-0001.

### Para la frontera entre contextos

**5. Anticorruption layer completa** entre Catálogo, Pedidos y Cuentas, con
traductores en ambos sentidos. **Descartada:** una capa de traducción cuesta
mantenimiento y se justifica cuando el modelo ajeno es hostil o inestable. Aquí
los tres lados los escribe el mismo equipo y cambian a la vez; ponerla «por
precaución» es el error frecuente contra el que advierte el propio patrón.

**6. Lenguaje publicado — elegida.** Un módulo `contracts.py` por contexto cuyos
tipos son lo único que cruza la frontera, separado del modelo interno. Da la
misma protección frente a la filtración a una fracción del coste, y deja el
modelo interno libre para evolucionar.

## Decisión

1. **El módulo `usuarios` (contexto Cuentas) es el único escritor de la entidad
   `Establecimiento`** (`id`, `nombre`, `ubicación`, `horario`, `activo`),
   modelada como un tercer tipo de cuenta junto a usuario (estudiante o
   profesor) y admin.
2. **`menu` y `pedidos` almacenan únicamente `establecimiento_id` como
   referencia** —no duplican nombre, ubicación ni horario— y lo resuelven a
   través de `usuarios.service.obtener_establecimiento(id)` y
   `usuarios.service.establecimiento_esta_activo(id)`.
3. **`establecimiento_id` deja de aceptarse en la petición de creación de
   pedido.** Se deriva del ítem.
4. **Cada contexto publica sus tipos de frontera en `contracts.py`.** Las
   funciones públicas responden con esos tipos, nunca con entidades internas.
5. **La superficie pública de un contexto queda definida como `service` y
   `contracts`.** Cualquier otro import entre módulos es una violación.
6. **La anticorruption layer se reserva para Wompi**, único modelo ajeno e
   inestable del sistema.

A diferencia de lo previsto inicialmente, la decisión **no queda solo
documentada**: se implementó el módulo `usuarios` con esa responsabilidad, para
que la propiedad exista en el código y no únicamente en este ADR.

## Consecuencias

**Positivas.**

- Ningún dato del sistema tiene dos escritores, que es la propiedad que
  determina si un servicio se podrá extraer más adelante.
- La regla de la decisión 5 es verificable: `backend/tests/test_modularidad.py`
  analiza el árbol de sintaxis de cada archivo y falla si alguien la rompe.
- `menu.ItemMenu` y `pedidos.Pedido` **no cambian su relación con el
  establecimiento**: siguen guardando solo la referencia, sin datos duplicados.
- El error de «pedido al establecimiento equivocado» pasa a ser imposible por
  construcción, no por validación añadida.
- `menu` (Catálogo) se convierte en el contexto más barato de extraer como
  servicio: no lo escribe nadie desde fuera y su lenguaje publicado ya tiene la
  forma de una respuesta HTTP.

**Negativas y costes aceptados.**

- **Cambia el contrato de la API.** `POST /pedidos` ya no acepta
  `establecimiento_id`. Como todavía no hay frontend consumiendo el endpoint, el
  coste es cero hoy y habría sido alto más adelante.
- **Hay un tipo más que mantener por contexto.** `ItemDisponible` y
  `EstablecimientoPublico` duplican campos de las entidades internas. Es el
  precio del desacoplamiento: cuando dejen de ser iguales será porque el modelo
  interno evolucionó sin romper a nadie.
- **`usuarios` concentra identidad y datos de negocio.** Si en una entrega
  posterior el establecimiento necesita su propio ciclo de vida independiente de
  las cuentas (sucursales, convenios comerciales), podrá extraerse a un módulo
  propio **sin reescribir `menu` ni `pedidos`**, que ya lo tratan como una
  referencia opaca. Ese cambio requeriría un ADR nuevo.
- **Coste en rendimiento: nulo.** La línea base de `POST /pedidos` pasó de
  p95 3,32 ms a **p95 3,02 ms** pese a añadir una segunda llamada entre
  contextos, porque sigue siendo una llamada en proceso. El dato importa porque
  muestra lo que costaría extraer un contexto como servicio: ese mismo salto
  pasaría a ser de red.

## Trazabilidad

| Elemento | Referencia |
|---|---|
| **Auditoría que la motiva** | [`docs/ddd-contextos.md` §4](../ddd-contextos.md), hallazgo H-2 |
| **Violaciones que corrige** | [V-01](../violaciones.md#v-01), [V-02](../violaciones.md#v-02), [V-05](../violaciones.md#v-05) |
| **Decisión relacionada** | [ADR-0001](0001-estilo-arquitectonico.md) — no se modifica; esta la complementa |
| **Responsabilidad de módulo ya prevista en** | [arc42 §5.3](../arc42/arc42.md#responsabilidad-modulos) |
| **Escenarios afectados** | [ESC-01](../arc42/arc42.md#esc-01), [ESC-03](../arc42/arc42.md#esc-03) |
| **Conceptos transversales** | [arc42 §8](../arc42/arc42.md#seccion-8) |
| **C4 afectado** | [Nivel 3 — módulos](../c4/nivel3-modulos.md) |
| **Código** | `backend/app/usuarios/` (`models.py`, `contracts.py`, `repository.py`, `service.py`), `backend/app/menu/contracts.py`, `backend/app/pedidos/models.py`, `backend/app/pedidos/service.py` |
| **Pruebas** | `tests/test_propiedad_datos.py` (6 pruebas) · `tests/test_modularidad.py` (regla de dependencia + caso negativo) |
| **Verificación automática** | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) |
| **Índice de trazabilidad** | [`docs/aspectos.md`](../aspectos.md) |
