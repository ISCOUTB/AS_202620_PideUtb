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
| **Versión del contrato** | `info.version` (SemVer: `1.0.0`) | Comunica a los consumidores **qué cambió y si les afecta**. Cambia en cada modificación del archivo. |
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

## 6. Historial

| Versión | Ruta | Estado | Archivo congelado | Cambios |
|---|---|---|---|---|
| **1.0.0** | `/v1` | **Vigente** | [`historial/openapi-1.0.0.yaml`](historial/openapi-1.0.0.yaml) | Versión inicial: catálogo, pedidos y pagos. |

El contrato de eventos sigue la misma política y su propio historial:
[`historial/asyncapi-1.0.0.yaml`](historial/asyncapi-1.0.0.yaml).

### Por qué `1.0.0` y no `0.1.0`

`0.x` significa «sin promesa de compatibilidad», y en ese régimen ninguna de las
reglas de §3 sería exigible: cualquier rotura estaría permitida por definición y
el pipeline no tendría nada que hacer cumplir. La entrega consiste precisamente
en tener esa promesa, así que la versión empieza donde la promesa empieza.
