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
| [V-09](#v-09) | El estado vive en memoria del proceso | Arquitectura | 🟡 Conocida | ✅ Corregida (S8) |
| [V-10](#v-10) | El panel del mostrador no está autenticado | Autenticación | 🔴 Alta | ✅ Corregida (S10) |
| [V-11](#v-11) | El secreto del webhook estaba escrito en el código | Secretos | 🔴 Alta | ✅ Corregida (S9) |
| [V-12](#v-12) | El token de sesión vive en `sessionStorage` | Autenticación | 🟡 Conocida | ⏳ Aceptada, con condición |
| [V-13](#v-13) | Los códigos de canje se podían cosechar enumerando pedidos | Exposición de datos | 🔴 Alta | ✅ Corregida (S14) |

Seis se corrigieron en S6 y **dos más en S7** —V-07 y V-08—, cada una con su
prueba. **V-09 se cerró en S8** con la migración a PostgreSQL, **V-11 en S9** y
**V-10 en S10** con sesiones y roles propios
([ADR-0007](adr/0007-autenticacion-del-panel.md)).

Cerrar V-10 abrió V-12, y eso no es un fracaso: es lo que pasa cuando una
protección se construye de verdad en vez de dejarla anotada. Mientras el panel
no tenía sesión no había token que robar. Ahora hay uno, vive en el navegador y
hay que decir dónde y qué lo expondría. Una violación nueva que nace **descrita
y acotada** vale más que una ausencia de la que nadie habla.

**V-13 se encontró mirando el código de al lado.** Apareció preparando otra cosa
—publicar el estado del cobro para que un rechazo dejara de parecer un pago que
no ha llegado— y el paso previo era saber qué expone ya la consulta pública de
un pedido. Expone el código de canje, y los identificadores son secuenciales.

Es la misma lección que V-11 con una causa distinta: V-11 llevaba tres entregas
activa y la encontró una auditoría; V-13 llevaba desde la primera entrega y la
encontró **la pregunta previa a añadir una lectura más**. Ninguna de las dos la
encontró una prueba, porque ninguna prueba comprobaba lo que *no* debería poder
hacerse.

V-11 merece una línea aparte porque no se descubrió construyendo sino
**auditando**: estuvo activa en producción tres entregas, con el pipeline en
verde todo ese tiempo.

V-10 tampoco se descubrió tarde. Fue consecuencia de una decisión tomada con los
ojos abiertos, y durante las tres entregas que estuvo abierta el sistema la
declaró por su cuenta: el panel avisaba en pantalla de que no estaba protegido,
en vez de dejarlo solo en este documento.

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

**Estado:** ✅ corregida en S8. **Archivos:** `app/*/repository.py`,
`app/base_de_datos.py`, `migraciones/`

Los datos semilla y los pedidos eran variables de módulo: cada proceso tenía su
propia copia.

**Reproducción.** Dos procesos distintos, equivalentes a dos *workers* de
uvicorn o a dos invocaciones serverless:

```
proceso 1 -> pedido id = 1
proceso 2 -> pedido id = 1
```

Dos pedidos distintos con el mismo identificador.

El despliegue real ([ADR-0004](adr/0004-plataforma-de-despliegue.md)) usa un
contenedor con proceso persistente, así que los pedidos **sí** sobreviven entre
peticiones — pero no entre despliegues, y Render redespliega en cada push a
`master`. El chequeo de salud lo declara en voz alta: responde
`tipo: "memoria"`.

**Corrección.** Los cuatro repositorios consultan PostgreSQL cuando
`PIDEUTB_DATABASE_URL` está configurada, y **la base de datos genera los
identificadores**: `siguiente_id()` ya no existe. El esquema está en
`migraciones/001_esquema_inicial.sql` y lo aplica `scripts/migrar.py`.

Se conserva la implementación en memoria para que la suite corra sin PostgreSQL
instalado. El riesgo de que las dos se separen se controla ejecutando **las
mismas pruebas contra ambas** (`tests/test_repositorios.py`), y el CI levanta un
PostgreSQL efímero para que la parte que importa no se omita en silencio.

La migración cerró además un modo de fallo que el almacenamiento en memoria
ocultaba: confirmar un pago pasó de leer-decidir-escribir a un
`UPDATE ... WHERE estado = 'pendiente_pago'` en una sola instrucción. Con dos
trabajadores y dos entregas simultáneas del mismo webhook, la versión anterior
habría generado **dos códigos de canje** para un solo pedido.
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

---

<a id="v-10"></a>

## V-10 · El panel del mostrador no está autenticado

**Estado:** ✅ corregida en S10. **Archivos:** `sitio/panel.html`,
`sitio/panel.js`, `app/pedidos/router.py`, `app/autenticacion.py`,
`app/usuarios/`

Cualquiera que conociera la URL del panel podía listar los pedidos de cualquier
establecimiento y avanzar su estado. No había sesión, ni rol, ni comprobación de
que quien pedía el cambio trabajara en ese establecimiento.

**Reproducción (hasta S10).** Sin ninguna credencial, contra el entorno
desplegado:

```bash
curl -s "https://pideutb-api.onrender.com/v1/pedidos?establecimiento_id=1"
curl -s -X POST https://pideutb-api.onrender.com/v1/pedidos/1/estado \
  -H "Content-Type: application/json" -d '{"estado":"entregado"}'
```

**Por qué se desplegó igual.** La autenticación es trabajo de la entrega
siguiente, y dejar [ESC-03](arc42/arc42.md#esc-03) sin implementar por esperarla
habría dejado al establecimiento sin ninguna forma de gestionar sus pedidos.

**Por qué no se puso un secreto compartido.** Fue la primera idea y se
descartó: un sitio estático no puede guardar un secreto. Cualquier clave en
`panel.js` se lee con F12, así que sería teatro — y peor que admitir que está
abierto, porque *parece* protegido y nadie volvería a mirarlo.

**Lo que sí se hizo, porque sí se podía.** El daño está acotado por diseño, no
por confianza:

| Contención | Cómo |
|---|---|
| **El panel no puede marcar un pedido como pagado** | `pagado` no está en `EstadoSolicitable`, así que el esquema lo rechaza con `422`. Esa transición solo la dispara el webhook firmado de la pasarela ([ADR-0003](adr/0003-estrategia-integracion.md)) |
| **No se puede revertir un pago** | `pendiente_pago` tampoco es solicitable |
| **No se pueden saltar estados** | `TRANSICIONES_DEL_MOSTRADOR` solo admite el recorrido legítimo |
| **Los estados finales son finales** | Desde `entregado` o `cancelado` no se sale |
| **La cola exigía un establecimiento** | `establecimiento_id` era obligatorio: sin él la ruta habría devuelto los pedidos de todo el campus. En S10 dejó de ser obligatorio **y de ser una contención**, porque el establecimiento pasó a salir de la sesión |
| **Se avisa en la propia pantalla** | El panel dice que no está protegido, en vez de dejarlo solo en este documento |

Sin la primera, cualquiera con un navegador podría marcar su propio pedido como
pagado y retirar comida sin pagarla. Es la contención que importa, y está
cubierta por
`tests/test_panel_mostrador.py::test_el_mostrador_no_puede_marcar_un_pedido_como_pagado`.

**Corrección (S10): el establecimiento sale de la sesión, no del parámetro.**

El plan decía «sesión para el personal y comprobación de que el pedido
pertenece a su establecimiento». Es lo que se hizo, con una diferencia que
conviene subrayar: el `establecimiento_id` no se *valida*, se **ignora** como
fuente de autoridad. Validarlo habría dejado la decisión en manos de quien
pregunta; ahora la respuesta se construye desde la sesión y el parámetro solo
existe para que un administrador elija.

| Qué | Dónde | Prueba |
|---|---|---|
| Sin sesión no se puede ni mirar la cola | `app/autenticacion.py::usuario_actual` → `401` + `WWW-Authenticate: Bearer` | `test_sin_sesion_no_se_puede_ni_mirar` |
| El establecimiento lo fija la sesión | `establecimiento_que_puede_ver` | `test_el_establecimiento_sale_de_la_sesion_y_no_del_parametro` |
| Pedir el de otro no se ignora en silencio: da `403` | idem | `test_pedir_el_establecimiento_de_otro_da_403` |
| Un pedido de otro establecimiento responde `404`, no `403` | `pedidos.service.avanzar_estado` | `test_avanzar_el_pedido_de_otro_establecimiento_da_404` |
| Entregar exige el código de canje | idem, transición a `entregado` | `test_entregar_sin_el_codigo_no_se_puede` |

**Por qué `404` y no `403` para un pedido ajeno.** Un `403` confirma que el
pedido existe. Con eso se enumeran los pedidos del campus probando
identificadores, que es una fuga distinta y más silenciosa que la que se estaba
cerrando. En cambio, pedir el **establecimiento** de otro sí responde `403`:
ahí no hay nada que enumerar, porque los establecimientos son públicos y están
en el menú.

**Lo que esto costó.** El contrato subió a **2.0.0**: exigir una credencial que
antes no se pedía rompe a todo cliente existente (regla **I-12** de
[`politica-versionado.md`](api/politica-versionado.md)). El prefijo de ruta no
cambió a `/v2`, y eso es deliberado: §5 bis de la política lo prohíbe cuando lo
viejo **es** el defecto. Mantener `/v1` abierto noventa días mientras `/v2`
exige sesión sería dejar esta misma puerta abierta tres meses más, y el plazo
que protege a los consumidores protegería también a quien quiera entrar.

**Lo que esto abrió.** [V-12](#v-12): ahora hay un token, y vive en el
navegador.

---

<a id="v-11"></a>

## V-11 · El secreto del webhook estaba escrito en el código

**Estado:** ✅ corregida en S9. **Archivos:** `app/pagos/service.py`,
`tests/conftest.py`, `tests/test_secreto_pasarela.py`

`app/pagos/service.py` traía un valor por defecto para el secreto que verifica
la firma de los avisos de la pasarela:

```python
_SECRETO_PASARELA = os.getenv("PIDEUTB_SECRETO_PASARELA", "<cadena fija en el código>")
```

El valor que ocupaba ese lugar no se reproduce. Está en el historial de git y de
ahí no se puede quitar, pero mantenerlo escrito en los archivos vigentes lo deja
al alcance de un `grep` y no aporta nada: lo que hay que entender de V-11 es que
**había** un valor por defecto, no cuál era. Fue rotado al corregirla, y la
acreditación de esa rotación está más abajo.

La intención era buena: que el repositorio fuera ejecutable sin credenciales.
**Esa comodidad es justamente lo que lo volvió peligroso**, porque nadie lo
trató como un secreto — no lo parecía.

**Reproducción.** El despliegue nunca definió la variable real. Consultando la
API de Render, el servicio tenía solo `PIDEUTB_DATABASE_URL` y
`PIDEUTB_ORIGENES_PERMITIDOS`. Así que la API en producción verificaba las
firmas contra una cadena **publicada en un repositorio público**, y cualquiera
que lo leyera podía firmar un aviso de pago válido y obtener un código de canje
sin pagar.

No se explotó contra producción: el código lee el valor por defecto y la
variable no existía, así que la deducción es concluyente sin hacerlo.

**Por qué no lo detectó nada.** No era una credencial *olvidada* —esas las
encuentra cualquier escáner de secretos— sino un valor por defecto
**deliberado**, escrito como tal y con un comentario explicándolo. Ninguna
herramienta lo marca, porque desde fuera parece una decisión.

**Corrección: fallar en cerrado.** Se quitó el valor por defecto. Sin
`PIDEUTB_SECRETO_PASARELA`, `firma_valida` rechaza **todo** evento.

Un sistema sin su secreto deja de aceptar confirmaciones de pago: molesto y
visible. Con un secreto público aceptaba pagos falsos: peor y silencioso.

Siete pruebas lo cubren, y tres merecen mención:

- `test_una_firma_hecha_con_otro_secreto_no_sirve` **reproduce el ataque**: un
  evento firmado con una cadena que no es la configurada devuelve `401`.
- `test_el_secreto_no_aparece_en_el_codigo_fuente` comprueba que ningún archivo
  de `app/` vuelva a traer uno escrito. Es la prueba que lo habría evitado desde
  el principio: no verifica un comportamiento, verifica la ausencia de la causa.
- `test_ningun_secreto_vuelve_a_tener_valor_por_defecto` persigue **la forma**
  del defecto, no su valor: cualquier `os.getenv` de una variable con pinta de
  credencial que lleve un valor por defecto no vacío. Buscar el valor histórico
  solo habría protegido contra repetir aquel error exacto; buscar la forma
  protege contra el error. Viene con su propio caso negativo —
  `test_el_guardia_de_secretos_detecta_lo_que_dice_detectar`— porque un
  detector al que solo se le dan archivos correctos pasa igual si funciona y si
  está roto.

### Acreditación: rotado y desplegado

Corregir el código no cierra esta violación. El secreto siguió publicado en el
historial de git después del commit que lo quitó, así que mientras no se rotara
y el despliegue no corriera la versión que falla en cerrado, la puerta seguía
abierta. Lo comprobado, el **2026-10-12**:

| Qué | Cómo se comprobó | Resultado |
|---|---|---|
| La variable existe en producción | API de Render, `GET /v1/services/srv-dasroip7lnhs73ahd4c0/env-vars` | `PIDEUTB_SECRETO_PASARELA` presente, **43 caracteres** |
| Es un valor rotado, no el histórico | Longitud frente a la del valor que estuvo publicado | Distinta. 43 caracteres es lo que devuelve `secrets.token_urlsafe(32)`: entropía generada, no una palabra |
| El despliegue vivo incluye la corrección | `git merge-base --is-ancestor ad0b9b1 7e973faf` | Cierto. `ad0b9b1` es el commit que quita el valor por defecto |
| Qué commit está sirviendo | API de Render, `GET .../deploys` | `7e973faf`, estado `live`, terminado el 2026-10-04T17:48:39Z |
| Los servicios responden | `GET /health` y `GET /panel.html` | `200` los dos |

El valor del secreto **no se leyó**, solo su longitud. Es deliberado: una
acreditación que para demostrar la rotación tuviera que mirar el secreto deja
el secreto en el historial de la sesión que la escribió, y entonces la
acreditación es la nueva fuga. La longitud basta para distinguir una cadena
generada de una palabra escrita a mano, que es exactamente la pregunta.

Tampoco se explotó contra producción, ni antes ni ahora: el código leía el
valor por defecto y la variable no existía, de modo que la deducción es
concluyente sin hacerlo, y hacerlo habría sido emitir un pago falso contra un
servicio en marcha.

**Lo que dejó para la próxima vez.** Las pruebas declaran ahora el secreto
explícitamente en `conftest.py`. Que haya que declararlo es el punto, no una
molestia: un secreto que se puede omitir termina omitido, y la omisión no se
nota porque todo sigue funcionando.

Y la lección que se generaliza: **corregir el código es la mitad del trabajo.**
La otra mitad es rotar lo que estuvo expuesto y comprobar que lo desplegado es
lo corregido. Un repositorio puede estar impecable mientras producción sigue
sirviendo la versión vulnerable, y el repositorio no tiene forma de saberlo. Por
eso esta acreditación nombra el commit que está vivo y no solo el que arregla.

---

<a id="v-12"></a>

## V-12 · El token de sesión vive en `sessionStorage`

**Estado:** ⏳ aceptada, con condición explícita. **Archivos:** `sitio/panel.js`,
`app/autenticacion.py`

El panel guarda el token de sesión en `sessionStorage`. Un fallo de XSS en el
sitio permitiría leerlo con una línea de JavaScript y operar el mostrador
durante las ocho horas que dura la sesión.

**Por qué no es una cookie `HttpOnly`,** que es la respuesta de manual. El sitio
es estático y vive en un origen distinto del de la API
([`pideutb-sitio.onrender.com`](https://pideutb-sitio.onrender.com) frente a
`pideutb-api.onrender.com`). Una cookie que cruce esos dos orígenes necesita
`SameSite=None`, `Secure`, CORS con credenciales y, a partir de ahí,
**protección contra CSRF**, porque el navegador la enviaría sola desde cualquier
sitio.

El intercambio, dicho entero:

| | Token en `sessionStorage` | Cookie `HttpOnly` entre orígenes |
|---|---|---|
| Expuesto a XSS | **Sí** | No |
| Expuesto a CSRF | No: nada se envía solo | **Sí**, salvo que se añada defensa explícita |
| Piezas nuevas que hay que mantener correctas | Ninguna | `SameSite=None`, CORS con credenciales, tokens anti-CSRF |

No se eligió la opción «segura» sino la que **deja menos cosas que mantener
correctas**. Un CSRF mal defendido no avisa; y cada pieza de la columna derecha
es una que puede configurarse mal en silencio, que es exactamente la forma en
que apareció [V-11](#v-11).

**Qué acota el riesgo hoy.** El panel no renderiza HTML de nadie: todo el texto
que viene de la API se inserta con `textContent`, nunca con `innerHTML`. Eso es
lo que hace que el XSS no sea un camino abierto, y **es una propiedad del código
del sitio, no una garantía del mecanismo**: un solo `innerHTML` futuro la
elimina.

**Condición para reconsiderarlo.** Esta aceptación deja de valer si ocurre
cualquiera de estas tres:

1. El sitio pasa a renderizar contenido que escribe un usuario —nombres de
   ítems editables, notas de pedido, cualquier cosa que llegue de un formulario.
2. El sitio y la API pasan a compartir origen, con lo que la cookie deja de
   necesitar `SameSite=None` y el intercambio cambia de signo.
3. La sesión pasa a dar acceso a algo con dinero de verdad, y no solo a la cola
   de un mostrador.

**Lo que no se hizo y se nota.** No hay Content-Security-Policy. Sería la
defensa en profundidad que corresponde aquí: con una CSP estricta, un XSS
inyectado tendría mucho más difícil ejecutarse. Está sin hacer, y se dice en vez
de omitirlo.

---

<a id="v-13"></a>

## V-13 · Los códigos de canje se podían cosechar enumerando pedidos

**Estado:** ✅ corregida en S14. **Archivos:** `app/pedidos/router.py`,
`app/pedidos/service.py`, `app/pedidos/models.py`,
`migraciones/007_token_de_consulta.sql`, `sitio/app.js`

`GET /v1/pedidos/{pedido_id}` era **público y no pedía nada**, y devolvía
`codigo_canje`. Los identificadores son secuenciales, así que cualquiera podía
recorrerlos y quedarse con los códigos de los pedidos pagados. El código de
canje es lo que se presenta en el mostrador para llevarse la comida: con él se
recoge el pedido de otra persona.

**Reproducción (hasta S14).** Sin ninguna credencial:

```bash
for id in 1 2 3 4 5; do curl -s "http://127.0.0.1:8000/v1/pedidos/$id"; done
```

```
estado=pendiente_pago   total=   8000  codigo_canje=None
estado=pagado           total=  60000  codigo_canje=VR8M19
estado=pagado           total=  36500  codigo_canje=CR1IGP
estado=pagado           total=  26000  codigo_canje=4PD2EJ
estado=pendiente_pago   total=   4500  codigo_canje=None
```

**No estaba en el modelo de amenazas.** arc42 §8.7 tenía I-1 —enumerar los
pedidos *de otro establecimiento*— y lo cerró exigiendo sesión en la cola del
mostrador. Esta puerta era otra, iba por identificador y no exigía nada. Lo
cubre ahora **I-8**.

**Por qué estuvo abierta tanto tiempo.** La consulta nació para que el cliente
pudiera seguir su pago, y un cliente sin cuenta no tiene con qué autenticarse:
la ausencia de cuentas es una decisión deliberada (arc42 §8.8), y de ella se
siguió, sin decirlo, que esa consulta no podía pedir nada. El salto que faltaba
es que **identificar un pedido no es identificar a una persona**.

**La corrección.** El pedido lleva un `token_consulta`: 192 bits de
`secrets.token_urlsafe(24)`, entregado **una sola vez** en la respuesta de
`crearPedido` y exigido en la cabecera `X-Token-Pedido`. Sin él, con uno
equivocado o con un pedido que no existe la respuesta es la misma, `404` —un
`403` confirmaría cuáles existen, que es el criterio que I-1 ya había fijado—.
La comparación es en tiempo constante, por lo mismo que la firma de la pasarela.

**Es un cambio incompatible, y se aplicó sin periodo de convivencia.** Lo
permite §5 bis de `api/politica-versionado.md`, escrita antes de necesitarla:
cuando lo viejo **es** el defecto, los noventa días que protegen a los
consumidores protegerían también a quien quiera entrar. Contrato 4.0.0, prefijo
`/v1` sin cambiar, único consumidor actualizado en el mismo commit.

**Lo que destapó de paso.** El comparador de contratos daba el cambio por
**compatible**: miraba `security` y el cuerpo de las peticiones, pero no los
`parameters`, así que exigir una cabecera nueva no encendía nada. La regla I-12
ya existía y decía exactamente eso desde la S10; lo que faltaba era que el
comparador la aplicara. Es el mismo hueco que la S10 encontró en `security`, un
nivel más abajo, y ahora tiene sus dos casos negativos.

**Lo que quedaba, y se cerró en la S16.** El token vivía en memoria del
navegador, así que recargar la página perdía el pedido igual que antes de este
cambio. Eso se escribió aquí como una limitación aceptada, y resultó ser un
defecto con consecuencia: quien ya había pagado y recargaba —o volvía desde la
pasarela, que abre otra pestaña, o pulsaba «Hacer otro pedido»— se quedaba sin
el código con el que recoge. El dinero se había movido y la prueba de que se
había movido, no.

Ahora el pedido y su token se guardan en `localStorage`, y el sitio los retoma
al abrir. Lo que eso **añade** a la superficie de ataque es poco y conviene
decirlo con precisión:

| | Antes | Ahora |
|---|---|---|
| Qué puede leer un XSS en el sitio | El token, de la variable | El token, del almacenamiento |
| Qué sobrevive a cerrar la pestaña | Nada | El pedido propio, seis horas |
| Qué ve la siguiente persona en un aparato compartido | Nada | Nada: se borra al entregarse o cancelarse el pedido, y caduca |

El primer renglón es el que importa, y no cambia: un XSS que pueda leer
`localStorage` ya podía leer la variable. Los otros dos son los que sí añaden
exposición, y los dos están acotados a propósito —seis horas es más que una
comida y menos que un día—.

Lo que **sigue sin existir** es «buscar mi pedido»: se recupera lo que este
navegador guardó, no una cuenta. Desde otro aparato no hay nada que encontrar, y
añadirlo volvería a abrir la pregunta de qué identifica a quien pregunta.

**Y estuvo abierto en un despliegue que se daba por apagado.**
`pideutb-api.onrender.com` —el anterior a
[ADR-0008](adr/0008-despliegue-en-el-servidor-del-laboratorio.md)— seguía vivo,
anunciando la versión 2.0.0 del contrato y respondiendo a
`GET /v1/pedidos/{id}` con el `codigo_canje` dentro. `infra/README.md` lo daba
por inexistente; se comprobó pidiéndoselo y respondió `200`.

Que no llegara a filtrar nada fue casualidad: sus tres pedidos estaban en
`pendiente_pago` y un pedido sin pagar no tiene código. Cualquiera que se
hubiera pagado ahí lo habría expuesto.

**Cerrado el 29 de octubre de 2026**, apagando el servicio desde el panel de
Render. Comprobado como se comprobó que estaba abierto, pidiéndoselo:

```
$ curl -i https://pideutb-api.onrender.com/health
HTTP/1.1 404 Not Found
x-render-routing: no-server
```

`no-server` es el borde de Render diciendo que detrás de ese nombre no hay
ningún servicio. Las tres rutas que antes respondían —`/`, `/health` y
`/v1/pedidos/{id}`— dan lo mismo.

**La lección se queda escrita aunque el caso esté cerrado:** corregir el código
no cierra una vulnerabilidad si el código viejo sigue atendiendo. Entre la
corrección (S14) y el apagado pasaron dos semanas en las que esta violación
estaba corregida *en el despliegue vigente* y abierta en otro que nadie
miraba.
