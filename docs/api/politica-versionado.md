# Política de versionado y evolución del contrato

> Reglas que el pipeline aplica automáticamente sobre
> [`openapi.yaml`](openapi.yaml) y [`asyncapi.yaml`](asyncapi.yaml).
> Quién las verifica y cómo: [`README.md`](README.md) de esta carpeta.

Este documento existe para que «¿este cambio rompe a alguien?» deje de ser una
opinión. Cada regla de aquí está implementada en
[`backend/scripts/comparar_contratos.py`](../../backend/scripts/comparar_contratos.py)
y ejercitada con su caso negativo en
[`backend/tests/test_compatibilidad_contrato.py`](../../backend/tests/test_compatibilidad_contrato.py).

---

## 1. Dos versiones distintas, que se mueven a distinto ritmo

Es la confusión más fácil de cometer, así que se separan explícitamente.

| Qué | Dónde vive | Para qué sirve |
|---|---|---|
| **Versión del contrato** | `info.version` (SemVer; hoy `1.1.0`) | Comunica a los consumidores **qué cambió y si les afecta**. Cambia en cada modificación del archivo. |
| **Versión de la ruta** | El prefijo `/v1` en cada path | Permite que **dos versiones incompatibles convivan** desplegadas. Solo cambia cuando hay una rotura. |

Un contrato puede pasar de `1.0.0` a `1.4.0` sin que la ruta deje de ser `/v1`:
son cuatro entregas de cambios compatibles. La ruta pasa a `/v2` únicamente
cuando `info.version` llega a `2.0.0`.

`GET /health` queda **fuera** de `/v1` a propósito. Es una sonda operativa para
la plataforma de despliegue, no parte de la superficie de negocio, y no arrastra
la promesa de compatibilidad.

## 2. Qué versión subir

| Cambio | Bump | Ruta |
|---|---|---|
| Se añade un endpoint | MINOR | `/v1` |
| Se añade un campo **opcional** a una petición | MINOR | `/v1` |
| Se añade un campo a una respuesta | MINOR | `/v1` |
| Se relaja una restricción de petición (`maximum` mayor, `minLength` menor) | MINOR | `/v1` |
| Solo cambian descripciones o ejemplos | PATCH | `/v1` |
| **Cualquier cambio de la tabla incompatible (§3)** | **MAJOR** | **`/v2`** |

## 3. Qué es un cambio incompatible

La definición operativa: **un cliente escrito contra la versión anterior, sin
tocarlo, deja de funcionar.**

| # | Cambio | Por qué rompe |
|---|---|---|
| I-1 | Quitar un endpoint | El cliente recibe `404` donde antes había respuesta. |
| I-2 | Quitar un campo **requerido** de una respuesta | El cliente lo lee y encuentra la clave ausente. |
| I-3 | Hacer **requerido** un campo de petición que era opcional | Las peticiones que ya funcionaban pasan a `422`. |
| I-4 | Añadir un campo **requerido** a una petición | Idéntico a I-3: el cliente no lo envía y es rechazado. |
| I-5 | Cambiar el **tipo** de un campo | `4000.0` y `400000` no se leen igual aunque el nombre no cambie. |
| I-6 | Cambiar el **significado** de un campo sin cambiar su nombre ni su tipo | El peor: ninguna herramienta lo detecta. Ver §4. |
| I-7 | Quitar un valor de un `enum` de **petición** | Un valor que el cliente enviaba pasa a ser inválido. |
| I-8 | Añadir un valor a un `enum` de **respuesta** | El cliente recibe un valor que su `switch` no contempla. Ver §3.1. |
| I-9 | Estrechar una restricción de petición (`maximum` menor, `minLength` mayor, `pattern` más estricto) | Peticiones antes válidas pasan a rechazarse. |
| I-10 | Quitar un código de respuesta documentado, o cambiar qué significa | El cliente tiene ramas de manejo de error que dejan de dispararse. |
| I-11 | Cambiar el `content-type` de una respuesta | El cliente no sabe deserializarla. |
| I-12 | **Exigir una cabecera o una credencial que antes no se pedía** | Peticiones que funcionaban pasan a `401`. Es I-4 aplicado a las cabeceras, y la lista no lo contemplaba hasta la semana 10. Ver §3.2. |

### 3.1 Los `enum` no son simétricos

Es la regla que más se equivoca, porque la intuición «añadir siempre es
compatible» falla justo aquí. Depende de **hacia dónde viaja el dato**:

| | Añadir un valor | Quitar un valor |
|---|---|---|
| **Enum de petición** (el cliente envía) | Compatible — nadie lo enviaba todavía | **Incompatible** — alguien lo enviaba |
| **Enum de respuesta** (el cliente recibe) | **Incompatible** — nadie sabe tratarlo | Compatible — nadie volverá a recibirlo |

`EstadoPedido` aparece en respuestas. Añadirle un estado nuevo obliga a `/v2`,
salvo que se demuestre que ningún consumidor discrimina por estado — y esa
demostración es justamente lo que hace
[`contracts/consumidor-web.yaml`](../../contracts/consumidor-web.yaml), donde
cada consumidor declara qué valores interpreta.

### 3.2 Por qué I-12 se añadió tarde, y qué más apareció al añadirla

La lista original hablaba de **campos** de petición y respuesta, y las cabeceras
no son campos. Esa distinción es técnica y no le importa a nadie: a un cliente
que empieza a recibir `401` le da igual si lo que falta viaja en el cuerpo o en
una cabecera.

El hueco apareció al añadir autenticación al panel del mostrador en la semana
10, y lo encontró leer la lista preguntándose si cubría el caso que teníamos
delante. Lo que vino después es más interesante que el hueco:

**Escribir la regla no la hace cierta.** Con I-12 ya en esta tabla, se midió el
contrato 2.0.0 contra la 1.2.0 congelada con nuestro propio comparador. Resultado:
**cero** cambios incompatibles, para el cambio más grande que este contrato ha
tenido. `comparar_contratos.py` revisaba rutas, esquemas, campos requeridos,
tipos, `enum` y códigos de respuesta, y no miraba `security` en absoluto. La
regla existía en este documento y en ningún otro sitio.

**Y había un segundo portón abierto detrás.**
`test_el_contrato_vigente_no_rompe_la_linea_base` comparaba siempre contra
`openapi-1.0.0.yaml` y se **omitía** cuando la MAYOR subía. Los dos defectos
juntos tienen una consecuencia peor que cada uno por separado: el salto a 2.0.0
habría apagado la comparación de compatibilidad para el resto del proyecto, y la
prueba habría seguido saliendo como «omitida», que en un resumen de pytest se lee
casi igual que «pasó».

Las dos cosas quedaron cerradas en la misma semana:

- I-12 está implementada en `backend/scripts/comparar_contratos.py`
  (`_comparar_credenciales`), con dos casos negativos y uno positivo en
  `test_compatibilidad_contrato.py`. El positivo importa tanto como los
  negativos: dejar de exigir una credencial es compatible, y una regla que
  marcara cualquier cambio de `security` como rotura bloquearía la única
  dirección inofensiva.
- La línea base la resuelve ahora `info.version` del propio contrato, así que un
  salto de MAYOR no apaga la comparación: la **reapunta** a la nueva base y
  obliga a congelarla en el mismo commit, tanto en la prueba como en el job de
  `oasdiff`.
- Y se añadió la simetría que faltaba:
  `test_el_salto_de_mayor_esta_justificado_por_una_rotura_real` exige que un
  2.0.0 pueda **señalar** la rotura que lo justifica. Avisar sin romper no es
  inofensivo: anuncia trabajo que no existe, y gasta la credibilidad del
  siguiente aviso.

Sobre `oasdiff` no afirmamos nada aquí: no se midió contra este caso, y una
herramienta externa no es evidencia hasta que uno la corre. Lo que sí se midió
es lo propio, y lo propio estaba en cero.

Es el mismo tipo de hallazgo que la semana 9, una vez más: una verificación que
no cubre todo el terreno da una seguridad que no tiene. La diferencia es que esta
vez el terreno descubierto era la verificación misma.

---

## 4. El cambio que ninguna herramienta detecta

`spectral` valida la forma. `oasdiff` compara estructuras. Ninguno de los dos
puede ver I-6: **el campo se llama igual, tiene el mismo tipo, y significa otra
cosa**.

El caso real de este proyecto: si `precio_unitario` hubiera quedado como número
decimal en pesos y después se cambiara a entero en centavos, `4000 → 400000`
pasa todas las validaciones automáticas y multiplica la factura por cien.

La defensa no es técnica sino de nomenclatura: **la unidad va en el nombre del
campo** (`precio_unitario_centavos`), de modo que cambiar la unidad obligue a
cambiar el nombre, y cambiar el nombre sí es un cambio que las herramientas
detectan. Es la misma disciplina de lenguaje ubicuo que resolvió las
ambigüedades de «Usuario» y «Carrito» en [arc42 §8.1](../arc42/arc42.md#lenguaje-ubicuo).

## 5. Cómo se avisa a los consumidores

Cuando toca `/v2`, el aviso no es un mensaje: es comportamiento observable en la
propia API.

1. **`/v1` y `/v2` conviven.** `/v1` no se apaga el día que `/v2` se publica.
2. **`/v1` empieza a anunciarse obsoleto en cada respuesta**, con cabeceras
   estándar que un cliente puede leer sin intervención humana:

   ```http
   Deprecation: true
   Sunset: Sat, 20 Dec 2026 00:00:00 GMT
   Link: <https://github.com/ISCOUTB/AS_202620_PideUtb/blob/master/docs/api/openapi.yaml>; rel="successor-version"
   ```

3. **La operación queda marcada `deprecated: true`** en el contrato, de modo que
   los clientes regenerados a partir del archivo emiten aviso al compilar.
4. **Plazo mínimo de 90 días** entre `Deprecation` y `Sunset`.
5. **La versión anterior se congela** en `historial/` y nunca se edita: es la
   referencia contra la que se comprueba que la promesa se cumplió.

El orden importa: primero se publica `/v2`, luego se marca `/v1` como obsoleto.
Al revés se avisa de una migración hacia un destino que todavía no existe.

## 5 bis. La excepción: cuando el comportamiento viejo **es** el defecto

El procedimiento de §5 asume una evolución benigna: `/v1` sigue funcionando
mientras los consumidores migran, y eso es correcto cuando lo viejo es
simplemente anterior.

**No lo es cuando lo viejo es una vulnerabilidad.** Mantener `/v1` vivo 90 días
mientras `/v2` exige autenticación significa dejar abierta durante tres meses la
misma puerta que se está cerrando. El plazo que protege a los consumidores
protegería también a quien quiera entrar.

Así que para un cambio incompatible **cuyo motivo es cerrar un defecto de
seguridad** rige esto:

1. **No hay convivencia.** El comportamiento inseguro deja de existir el día del
   despliegue, no noventa días después.
2. **El prefijo de ruta no cambia.** `/v1` frente a `/v2` existe *para permitir
   que dos versiones convivan*; sin convivencia, el prefijo no tiene trabajo que
   hacer. `info.version` sí sube a MAYOR, porque la rotura es real y hay que
   anunciarla.
3. **Se declara aquí, no en el commit.** La excepción tiene que ser legible
   antes de usarse, o se convierte en la coartada de cualquier rotura.
4. **Solo aplica mientras los consumidores estén coordinados**, es decir
   mientras `contracts/` declare consumidores que viven en este repositorio y se
   despliegan con la API. En cuanto exista uno externo, vuelve a regir §5 sin
   excepciones, porque ya no se le puede actualizar a la vez.

El riesgo de esta excepción es evidente: justifica saltarse el aviso, y casi
cualquier cambio se puede presentar como «de seguridad». El punto 4 es lo que la
acota, y es comprobable: basta mirar cuántos consumidores declara `contracts/`.

---

## 6. Historial

| Versión | Ruta | Estado | Archivo congelado | Cambios |
|---|---|---|---|---|
| **1.0.0** | `/v1` | Soportada | [`historial/openapi-1.0.0.yaml`](historial/openapi-1.0.0.yaml) | Versión inicial: catálogo, pedidos y pagos. |
| **1.1.0** | `/v1` | **Vigente** | [`historial/openapi-1.1.0.yaml`](historial/openapi-1.1.0.yaml) | `/health` sondea dependencias; nuevo `503`; nueva operación `/metricas`. |

### El caso 1.1.0, como ejemplo de esta política aplicada

Es el primer cambio que se midió contra estas reglas, y el diseño cambió por lo
que dijeron.

Hacer real el chequeo de salud pedía, en la versión intuitiva, que `status`
pudiera valer `ok` **o** `no_disponible`. Eso es exactamente la regla **I-8**:
un valor nuevo en un `enum` de respuesta. Un cliente cuyo `if (status === "ok")`
funcionaba habría empezado a caer en la rama equivocada sin que nadie tocara su
código, y habría obligado a `/v2`.

La forma compatible fue separar por código de respuesta: el `200` conserva su
`enum` de un solo valor y **añade** el campo `dependencias`, y el estado
degradado vive en un esquema propio, `ServicioNoDisponible`, bajo un `503`
nuevo. Añadir un campo a una respuesta y añadir un código no están en la lista
de §3, así que el salto es **MINOR**: 1.0.0 → 1.1.0, la ruta sigue en `/v1` y
ningún consumidor tuvo que cambiar.

Quedó un rastro que conviene notar: el `503` obligó a declararlo en
`contracts/consumidor-web.yaml`, porque `test_expectativas_consumidor.py` exige
que el consumidor sepa manejar todo código que puede recibir. Un cambio
compatible tampoco se cuela sin que alguien lo mire.

El contrato de eventos sigue la misma política y su propio historial:
[`historial/asyncapi-1.0.0.yaml`](historial/asyncapi-1.0.0.yaml).

### Por qué `1.0.0` y no `0.1.0`

`0.x` significa «sin promesa de compatibilidad», y en ese régimen ninguna de las
reglas de §3 sería exigible: cualquier rotura estaría permitida por definición y
el pipeline no tendría nada que hacer cumplir. La entrega consiste precisamente
en tener esa promesa, así que la versión empieza donde la promesa empieza.
