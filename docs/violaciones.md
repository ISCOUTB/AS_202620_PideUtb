# Violaciones detectadas en el código actual y plan de corrección

Evidencia S6. Detalle de la auditoría de modularidad resumida en
[`docs/ddd-contextos.md` §4](ddd-contextos.md), contrastando el código de
`backend/app/` contra la regla de comunicación de
[ADR-0001](adr/0001-estilo-arquitectonico.md) y la regla de propiedad de datos:
**cada dato tiene exactamente un módulo que lo escribe; los demás lo leen o lo
solicitan**.

**Auditoría realizada sobre el commit `bbefae8`.** Método: revisión de qué
módulo escribe qué dato, qué import cruza la frontera y qué tipos devuelven las
funciones públicas, más ejecución del código para reproducir cada hallazgo.
**No se registra ninguna violación que no se haya reproducido.** Las descartadas
por no reproducirse se documentan al final: el descarte también es resultado de
la auditoría.

## Resumen

| ID | Violación | Regla incumplida | Severidad | Estado |
|---|---|---|---|---|
| [V-01](#v-01) | El cliente decidía el establecimiento del pedido | Dueño único | 🔴 Alta | ✅ Corregida |
| [V-02](#v-02) | Se aceptaban pedidos a establecimientos que no operan | Dueño único | 🔴 Alta | ✅ Corregida |
| [V-03](#v-03) | `cantidad` admitía cero y negativos | Validación de dominio | 🔴 Alta | ✅ Corregida |
| [V-04](#v-04) | La regla de dependencia no se verificaba | Auditoría | 🟠 Media | ✅ Corregida |
| [V-05](#v-05) | El modelo de Catálogo se filtraba en Pedidos | Frontera de contexto | 🟠 Media | ✅ Corregida |
| [V-06](#v-06) | La instantánea del pedido era inauditable | Trazabilidad | 🟠 Media | ✅ Corregida |
| [V-07](#v-07) | El dinero se representa con `float` | Modelado | 🟠 Media | ✅ Corregida (S7) |
| [V-08](#v-08) | `estado` del pedido es texto libre | Modelado | 🟠 Media | ✅ Corregida (S7) |
| [V-09](#v-09) | El estado vive en memoria del proceso | Arquitectura | 🟡 Conocida | ⏳ Con plazo |

Seis se corrigieron en S6 y **dos más en S7** —V-07 y V-08—, cada una con su
prueba. Queda una, V-09, con plazo y motivo.

Las dos de S7 no se cerraron por iniciativa propia sino porque **el contrato de
API obligó a decidir**: escribir `openapi.yaml` antes que el código forzaba a
fijar el tipo del dinero y el conjunto de estados, y ninguna de las dos
decisiones se podía posponer sin publicar un contrato que habría que romper
después. Es el efecto práctico de trabajar API-first.

---

<a id="v-01"></a>

## V-01 · El cliente decidía a qué establecimiento iba el pedido

**Regla incumplida:** dueño único. Es la consecuencia concreta del hallazgo
[H-2](ddd-contextos.md) —`Establecimiento` sin dueño—: como nadie era la fuente
de verdad, `pedidos` escribía el valor que llegaba del cliente HTTP.

**Reproducción (antes).** El ítem 1 pertenece al establecimiento 1:

```bash
curl -X POST http://127.0.0.1:8000/pedidos -H "Content-Type: application/json" \
  -d '{"establecimiento_id": 99, "item_id": 1, "cantidad": 1}'
```

```json
201 {"id":1,"establecimiento_id":99,"item_id":1,"nombre_item":"Arepa de huevo", ...}
```

El pedido quedaba asignado al establecimiento 99, que no existe. El
establecimiento real nunca lo habría visto en su panel
([ESC-03](arc42/arc42.md#esc-03)).

**Corrección.** `establecimiento_id` se eliminó de `CrearPedidoRequest` y se
deriva de `item.establecimiento_id`, que llega del contexto Catálogo. Un campo
extra en la petición se ignora.

**Prueba:** `tests/test_propiedad_datos.py::test_establecimiento_se_deriva_del_item_y_no_del_cliente`

---

<a id="v-02"></a>

## V-02 · Se aceptaban pedidos a establecimientos que no operan

**Regla incumplida:** dueño único. Nadie podía responder si un establecimiento
existía o estaba abierto, porque la entidad no tenía dueño.

**Corrección.** El contexto Cuentas (`usuarios`) pasa a ser el **único
escritor** de `Establecimiento` y expone
`usuarios.service.establecimiento_esta_activo()`. `pedidos.service` la consulta
antes de crear el pedido y responde `409` si el punto no está recibiendo
pedidos. Decisión en
[ADR-0002](adr/0002-propiedad-datos-establecimiento.md).

**Prueba:** `tests/test_propiedad_datos.py::test_pedido_en_establecimiento_inactivo_se_rechaza`

---

<a id="v-03"></a>

## V-03 · `cantidad` admitía cero y valores negativos

**Regla incumplida:** validación de dominio en el contexto dueño.

**Reproducción (antes).**

| Petición | Respuesta |
|---|---|
| `{"item_id":1,"cantidad":0}` | `201`, `total: 0.0` |
| `{"item_id":1,"cantidad":-5}` | `201`, `total: -20000.0` |

Un pedido de importe negativo es un abono a favor del comprador.

**Corrección.** `cantidad: int = Field(default=1, ge=1, le=50)`. El límite
superior evita pedidos que ningún establecimiento puede atender. Pydantic
responde `422` sin lógica adicional.

**Prueba:** `tests/test_propiedad_datos.py::test_cantidad_fuera_de_rango_se_rechaza`

---

<a id="v-04"></a>

## V-04 · La regla de dependencia no se verificaba

**Regla incumplida:** la auditoría de modularidad. ADR-0001 prohíbe que un
módulo importe el `repository` o los `models` de otro, pero **nada lo
comprobaba**: escribir `from app.menu.repository import buscar_por_id` dentro de
`pedidos` dejaba el CI en verde. La regla que sostiene toda la decisión
arquitectónica dependía de que nadie se equivocara.

**Corrección.** `tests/test_modularidad.py` recorre el árbol de sintaxis de cada
archivo de `app/` y falla si un módulo importa de otro algo que no sea `service`
o `contracts`. Normaliza las dos formas de import, porque mirar solo
`from app.menu.service import x` y no `from app.menu import service` deja pasar
la mitad de los casos.

La prueba incluye su propio caso negativo
(`test_la_auditoria_detecta_una_violacion_introducida`), y se comprobó a mano
que detecta las tres formas de violación:

```
from app.menu.repository import buscar_por_id   -> detectada
from app.usuarios import models as m            -> detectada
import app.usuarios.repository                  -> detectada
```

**Es la corrección de mayor valor de la lista:** es la única que impide que las
demás reaparezcan.

---

<a id="v-05"></a>

## V-05 · El modelo de Catálogo se filtraba dentro de Pedidos

**Regla incumplida:** frontera de contexto. Este hallazgo **no aparece revisando
imports**: `menu.service.obtener_item()` devolvía la entidad interna `ItemMenu`,
así que `pedidos.service` manipulaba directamente un tipo del contexto vecino
sin importar nada ilegal. Si aparecen tipos del otro contexto dentro del tuyo,
no hay frontera: hay filtración. El efecto práctico es que cualquier campo
añadido a `ItemMenu` quedaba expuesto a Pedidos y a los clientes HTTP.

**Corrección.** Se separó el **lenguaje publicado** del modelo interno:
`menu/contracts.py` define `ItemDisponible` y `usuarios/contracts.py` define
`EstablecimientoPublico`. Son lo único que cruza la frontera; los `models` de
cada contexto vuelven a ser privados.

**No se construyó una anticorruption layer**, y es deliberado: una capa de
traducción completa cuesta mantenimiento y se justifica cuando el modelo ajeno
es hostil o inestable. Entre contextos internos escritos por el mismo equipo, el
contrato publicado da la misma protección a una fracción del coste. La
anticorruption layer queda reservada para Wompi
([`ddd-contextos.md` §2](ddd-contextos.md)).

**Prueba:** `tests/test_modularidad.py` (la superficie pública incluye
`contracts` y excluye `models`).

---

<a id="v-06"></a>

## V-06 · La instantánea del pedido era inauditable

**Regla incumplida:** trazabilidad de los datos copiados entre contextos. Es el
defecto real detrás del hallazgo [H-1](ddd-contextos.md).

El pedido guardaba `total` pero no el precio unitario. Con `total: 20000` y
`cantidad: 5` se podía dividir, pero en cuanto existan descuentos o impuestos la
división deja de ser válida y el pedido no se puede auditar. Además, la
intención de instantánea no estaba escrita, así que alguien podía «arreglarla»
leyendo el precio vigente de Catálogo y romper la inmutabilidad del importe.

**Corrección.** Se añadió `precio_unitario` al `Pedido` y se documentó la
instantánea en el docstring del modelo y en
[`ddd-contextos.md` §3](ddd-contextos.md).

**Prueba:** `tests/test_propiedad_datos.py::test_el_pedido_conserva_el_precio_aunque_cambie_el_catalogo`

---

<a id="v-07"></a>

## V-07 · El dinero se representa con `float`

**Estado:** ✅ corregida en S7. **Archivos:** `app/menu/models.py`, `app/menu/contracts.py`, `app/pedidos/models.py`, `app/pedidos/contracts.py`, `app/pagos/models.py`

`precio: float` y `total: float`. El tipo `float` no representa exactamente los
decimales (`0.1 + 0.2` da `0.30000000000000004`). Hoy no se nota porque los
precios semilla son enteros redondos, pero con impuestos o descuentos los
totales se desviarán por céntimos. Afecta a [ESC-04](arc42/arc42.md#esc-04): el
código de canje acredita un pago, y un importe que no cuadra con el de la
pasarela es una disputa.

**Corrección.** Todos los importes son **enteros en centavos**, y la unidad va
en el nombre del campo: `precio_centavos`, `precio_unitario_centavos`,
`total_centavos`, `monto_centavos`. Es la unidad que espera la pasarela, así que
el número que guarda el pedido y el que se manda a cobrar son el mismo, sin
conversión intermedia donde perder precisión.

**Por qué la unidad va en el nombre.** Un campo `precio` que pasa de pesos a
centavos es el único cambio incompatible que **ninguna herramienta puede
detectar**: mismo nombre, mismo tipo, significado distinto, y la factura se
multiplica por cien. Obligar a que cambiar la unidad implique cambiar el nombre
convierte un cambio invisible en uno que `oasdiff` y las pruebas de contrato sí
ven ([política de versionado §4](api/politica-versionado.md)).

**Se hizo ahora y no después** porque el contrato se publica en esta entrega:
cambiarlo una vez que existiera un consumidor habría exigido `/v2`.

**Pruebas:** `tests/test_menu.py::test_consultar_un_item_devuelve_el_precio_en_centavos`,
`tests/test_pedidos.py::test_crear_pedido_exitoso`,
`tests/test_contrato_api.py::test_la_aplicacion_cumple_el_contrato_publicado`

---

<a id="v-08"></a>

## V-08 · El estado del pedido es texto libre

**Estado:** ✅ corregida en S7. **Archivos:** `app/pedidos/contracts.py`, `app/pedidos/models.py`

`estado: str = "pendiente_pago"` acepta cualquier cadena, y no existe la lista
de estados válidos ni las transiciones permitidas. Nada impide pasar de
`entregado` a `pendiente_pago`. [ESC-03](arc42/arc42.md#esc-03) mide justamente
el cambio de estado.

**Corrección.** `EstadoPedido` es un `Enum` de seis valores declarado en
`pedidos.contracts` —no en `models.py`— porque **el conjunto de estados es parte
del lenguaje publicado**: mientras fue texto libre, ningún consumidor podía
saber qué valores debía estar preparado para recibir, que es tanto como no tener
contrato.

La transición la hace una única función, `pedidos.service.confirmar_pago`,
coherente con que Pedidos sea el único escritor del dato. Pagos la *solicita*;
no la ejecuta.

**Desviación respecto del plan original:** el valor previsto `listo` quedó como
`listo_para_recoger`. «Listo» es ambiguo —¿listo para preparar o listo para
recoger?— y es exactamente el tipo de ambigüedad que la auditoría de lenguaje
ubicuo de S6 encontró con «Usuario» y «Carrito».

**Lo que aún no está:** la máquina de transiciones permitidas. Hoy nada impide
pasar de `entregado` a `pendiente_pago` salvo que solo haya una función que
escriba el estado. Entra con el panel del establecimiento, que es el trabajo
que necesita esas transiciones.

**Pruebas:** `tests/test_contrato_api.py::test_los_enum_del_contrato_coinciden_con_los_del_codigo`,
`tests/test_expectativas_consumidor.py::test_el_consumidor_interpreta_todos_los_estados_posibles`

---

<a id="v-09"></a>

## V-09 · El estado vive en memoria del proceso

**Estado:** ⏳ conocida, con plazo. **Archivos:** `app/*/repository.py`

Los datos semilla y los pedidos son variables de módulo: cada proceso tiene su
propia copia.

**Reproducción.** Dos procesos distintos, equivalentes a dos *workers* de
uvicorn o a dos invocaciones serverless:

```
proceso 1 -> pedido id = 1
proceso 2 -> pedido id = 1
```

Dos pedidos distintos con el mismo identificador. Con el despliegue en Vercel
previsto en [arc42 §4.1](arc42/arc42.md#seccion-4), además, los pedidos
desaparecen entre invocaciones.

**Plan.** Conectar Supabase y delegar en la base de datos la generación de
identificadores. **Antes de cualquier despliegue**, aunque sea de demostración.
La interfaz de los repositorios ya está diseñada para que el cambio no toque
`service.py` ni `router.py`.

---

## Candidatas descartadas

El descarte también es resultado de la auditoría: estas se examinaron y **no**
se registran como violaciones.

| Candidata | Por qué se descartó |
|---|---|
| Condición de carrera en `pedidos.repository.siguiente_id()` por usar `global` sin bloqueo | Se ejecutó con 8 hilos y 16 000 llamadas: **cero colisiones**. El GIL de CPython serializa ese incremento. Registrarla habría sido un hallazgo teórico presentado como real. Lo que sí se reprodujo —el aislamiento entre procesos— está en [V-09](#v-09) |
| Que `Pedido` copie `nombre_item` y `total` de Catálogo ([H-1](ddd-contextos.md)) | No es escritura compartida: `menu` sigue siendo el único que escribe `ItemMenu.nombre`. Congelar el importe es correcto por diseño. El defecto real está en [V-06](#v-06) |
| Que `menu` y `pedidos` compartan `establecimiento_id` como shared kernel | Un shared kernel exige que ambos contextos **escriban** el mismo modelo. Aquí Cuentas es el único escritor y los otros dos guardan una referencia opaca: customer/supplier es el patrón correcto |
| Crear un quinto módulo `establecimientos` | ADR-0001 ya decidió no fragmentar más allá de lo necesario para el tamaño del proyecto. Un establecimiento es, en la práctica, un tipo de cuenta con permisos distintos, no un concepto con ciclo de vida propio. Ver las alternativas en [ADR-0002](adr/0002-propiedad-datos-establecimiento.md) |

## Plan de corrección de lo que queda

Orden por dependencia, no por severidad.

| Orden | Violación | Cuándo | Por qué en ese punto |
|---|---|---|---|
| 1 | [V-07](#v-07) | Con la integración de Pagos | Cambiar el tipo del importe toca el contrato de la API; hacerlo a la vez que se añade el pago evita romperlo dos veces |
| 2 | [V-08](#v-08) | Con el panel del establecimiento | Es el trabajo que necesita las transiciones de estado |
| 3 | [V-09](#v-09) | Antes de cualquier despliegue | Es la de mayor alcance y bloquea la puesta en producción |

Cada corrección entra con su prueba en el mismo cambio, y la fila
correspondiente de [`docs/aspectos.md`](aspectos.md) se completa cuando el
escenario asociado queda cubierto.
