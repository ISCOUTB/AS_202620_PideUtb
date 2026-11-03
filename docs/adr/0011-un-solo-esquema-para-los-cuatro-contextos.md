# ADR 0011: Guardar los cuatro contextos en un solo esquema con integridad referencial cruzada, que es la decisión de datos más cara de deshacer

## Estado

Aceptada — 03/11/2026. **Documenta una decisión que ya estaba tomada** desde
`001_esquema_inicial.sql` y que nunca se había escrito como tal.

## Contexto

Las decisiones de este proyecto están documentadas por lo que **aportan**:
[ADR-0001](0001-estilo-arquitectonico.md) eligió un monolito modular,
[ADR-0002](0002-propiedad-datos-establecimiento.md) repartió la propiedad de los
datos, [ADR-0009](0009-no-extraer-un-servicio.md) decidió no extraer ningún
servicio. Ninguna responde la pregunta que este ADR responde:

> De todo lo que decidimos sobre los datos, **¿qué sería lo más caro de
> deshacer, y cuánto cuesta exactamente?**

La pregunta no es retórica ni académica. El peso real de una decisión de
arquitectura no es lo que te da hoy: es **qué tan atrapado quedás si estuvo
mal**. Y las decisiones sobre datos son la categoría peor, por un motivo que no
aplica al código: un módulo se reescribe en una tarde y nadie se entera; las
filas que ya están escritas hay que migrarlas, y mientras migrás el sistema está
atendiendo gente.

Lo señaló la auditoría de la semana 12, que encontró que ningún ADR del
repositorio seleccionaba esa decisión ni ponía número a su reversión.

### La decisión, enunciada

Los cuatro contextos —`menu`, `pedidos`, `usuarios`, `pagos`— **escriben en un
solo esquema de PostgreSQL**, y la integridad entre ellos la impone el motor con
claves foráneas que **cruzan las fronteras de contexto**:

| Clave foránea | Dónde | Cruza de | a |
|---|---|---|---|
| `pagos_intentos.pedido_id` → `pedidos(id)` | `001:132` | **pagos** | **pedidos** |
| `pedidos.item_id` → `menu_items(id)` | `001:88` | pedidos | menu |
| `pedido_lineas.item_id` → `menu_items(id)` | `004:49` | pedidos | menu |
| `pedidos.establecimiento_id` → `establecimientos(id)` | `001:87` | pedidos | cuentas |
| `menu_items.establecimiento_id` → `establecimientos(id)` | `001:66` | menu | cuentas |
| `usuarios.establecimiento_id` → `establecimientos(id)` | `003:34` | usuarios | cuentas |

*(`sesiones.usuario_id` y `pedido_lineas.pedido_id` no entran: viven dentro de un
solo contexto y no atan a nadie con nadie.)*

Hoy eso es una ventaja y se cobra gratis. No puede existir un intento de pago
huérfano, ni una línea de pedido que apunte a un producto borrado, y no hace
falta ni una línea de código para garantizarlo: lo garantiza el motor, en cada
`INSERT`, sin que nadie lo recuerde.

## Por qué esta y no otra

Se consideraron las tres decisiones de datos candidatas.

### El esquema compartido — **la elegida**

Es la única cuya reversión **no se puede hacer con el sistema parado un rato**.
Las otras dos se deshacen con una ventana de mantenimiento; esta exige convivir
con los dos mundos mientras dura.

Y tiene un detonante concreto, no hipotético.
[ADR-0009](0009-no-extraer-un-servicio.md) nombra a `pagos` como **«el candidato
real»** a salir a su propio servicio el día que algo cambie. La primera fila de
la tabla de arriba, `pagos_intentos.pedido_id → pedidos(id)`, es exactamente la
cuerda que habría que cortar para sacarlo. La decisión que más barata parece hoy
es la que encarece calladamente la única extracción que el equipo ya dejó
escrito que algún día querrá.

### La propiedad de `Establecimiento` ([ADR-0002](0002-propiedad-datos-establecimiento.md))

Es una decisión de datos de verdad, y revertirla cuesta: habría que reasignar el
escritor y reescribir las lecturas que hoy pasan por lenguaje publicado. Pero
**se puede hacer de una vez**, sin convivencia: ninguna fila cambia de sitio,
solo cambia quién tiene permitido escribirla. Es cara en código y barata en
datos.

### PostgreSQL como motor

Revertirlo es una migración completa. Pero es costoso **en cualquier proyecto
del mundo**, y por eso no dice nada sobre este: un criterio que contesta igual
para todos no distingue nada. Además es la reversión mejor estudiada que existe,
con herramienta para cada par de motores.

## Decisión

**Se mantiene el esquema único con integridad referencial cruzada**, y se deja
escrito que es la decisión de datos más cara de deshacer de este sistema, con su
costo detallado abajo.

No se añade una capa de indirección para abaratarla por adelantado. Pagar hoy la
complejidad de no tener claves foráneas, para no pagar mañana una migración que
quizá nunca haga falta, es la clase de precaución que cuesta seguro y ahorra con
suerte. La apuesta de ADR-0001 sigue en pie.

## El costo de la reversión, en orden

Suponiendo el caso que ADR-0009 ya contempla —sacar `pagos` a su propio
desplegable, con su propia base—, esto es lo que hay que hacer, y en este orden:

1. **Sustituir la garantía del motor por conciliación en código.** La clave
   foránea desaparece, y con ella la imposibilidad estructural de un intento de
   pago huérfano. Esta parte **ya existe a medias**: la conciliación de
   [arc42 §6.7](../arc42/arc42.md#fallos-parciales) está implementada y probada
   en `backend/tests/test_fallos_parciales.py:71-174`, que inyecta un fallo
   entre dos escrituras y verifica que se detecta y se reintenta sin emitir un
   segundo código. Hoy cubre una ventana local; ahí cubriría dos bases.
2. **Partir el esquema.** `pagos_intentos` se va; `pedidos`, `menu_items`,
   `establecimientos` y `usuarios` se quedan. La columna `pedido_id` sobrevive
   como un identificador sin respaldo del motor.
3. **Escribir en los dos lados durante el corte.** Es el paso que impide hacer
   esto en una ventana de mantenimiento: mientras la base nueva se llena, la
   vieja sigue siendo la verdad, y toda escritura va a las dos. Cualquier error
   aquí se descubre tarde y en producción.
4. **Rellenar hacia atrás.** Copiar el histórico de `pagos_intentos` a la base
   nueva, con el sistema arriba, sin bloquear la tabla que atiende los cobros
   en curso.
5. **Retirar la escritura doble** y, solo entonces, borrar la tabla vieja.

Lo que convierte esto en «lo más caro» no son los cinco pasos: es que **el tres
y el cuatro ocurren con usuarios dentro**. Los otros dos candidatos no tienen un
paso equivalente.

## Qué señal dispararía pagarlo

Las mismas que [ADR-0009 §«Qué cambiaría esta decisión»](0009-no-extraer-un-servicio.md),
porque es la misma apuesta vista desde los datos. En particular:

- **Que `pagos` necesite escalar distinto del resto**, visible en `GET /metricas`
  si el p95 de `POST /v1/pagos/intentos` se despegara del de `POST /v1/pedidos`.
- **Que aparezca un segundo consumidor** del canal de eventos que no sea este
  sistema.
- **Que el presupuesto de memoria deje de ser 512 MB**, que es lo que hoy lo
  hace imposible aunque se quisiera.

Mientras ninguna ocurra, la clave foránea es una garantía gratis y no una deuda.

## Consecuencias

**Positivas.** Integridad referencial sin código que la sostenga, y sin pruebas
que la verifiquen: es el motor quien no deja. Las consultas que cruzan contextos
—la cola del mostrador con sus líneas y sus nombres de producto— son un `JOIN` y
no dos viajes con un ensamblado en memoria.

**Negativas y costes aceptados.** La extracción de `pagos` nace cara, y este
documento es el precio puesto por escrito. La regla de dependencia de
`test_modularidad.py` impide que los *módulos* se enreden, pero **no impide que
se enreden las tablas**: nada en CI falla hoy si alguien añade una sexta clave
foránea que cruce contextos. Esa guardia no existe, y no se añade en este ADR
porque prohibir claves foráneas en un sistema que las usa bien sería optimizar
contra un futuro que ADR-0009 decidió no tener todavía.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Estilo que esta decisión sostiene | [ADR-0001](0001-estilo-arquitectonico.md) |
| Propiedad de datos entre contextos | [ADR-0002](0002-propiedad-datos-establecimiento.md) |
| La extracción que esta decisión encarece | [ADR-0009](0009-no-extraer-un-servicio.md) |
| Las claves foráneas | [`001_esquema_inicial.sql`](../../backend/migraciones/001_esquema_inicial.sql) · [`003_autenticacion.sql`](../../backend/migraciones/003_autenticacion.sql) · [`004_carrito_y_catalogo.sql`](../../backend/migraciones/004_carrito_y_catalogo.sql) |
| Conciliación que sustituiría la garantía | [arc42 §6.7](../arc42/arc42.md#fallos-parciales) · `backend/tests/test_fallos_parciales.py` |
| Presupuesto de memoria | [ADR-0008](0008-despliegue-en-el-servidor-del-laboratorio.md) |
| Auditoría que pidió este documento | [`correcciones.md`](../../correcciones.md) |
