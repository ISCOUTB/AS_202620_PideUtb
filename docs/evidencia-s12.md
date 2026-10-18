# Evidencia S12 — Datos y eventos: medir antes de añadir

Fecha: **18/10/2026**.

Los entregables de la semana, y dónde está cada uno:

| Lo que se pide | Dónde |
|---|---|
| Garantías de consistencia por operación | [arc42 §8.6](arc42/arc42.md#consistencia) |
| Estrategia de caché e invalidación | [arc42 §8.6](arc42/arc42.md#consistencia) |
| Mensajería: contrato, garantías de entrega, deduplicación, reintentos y manejo de fallos | [`asyncapi.yaml`](api/asyncapi.yaml) · [arc42 §8.5](arc42/arc42.md#idempotencia) · [§6.7](arc42/arc42.md#fallos-parciales) |
| ADR comparando la solución con una alternativa síncrona | [ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md) |

Este documento explica **cómo se llegó a cada uno**, que es la parte que no cabe
en una tabla, y da cuenta de lo que se encontró por el camino.

---

## 1. La consistencia de este sistema se explica en una línea, y conviene decir por qué

Hay **una sola base de datos y ninguna réplica de lectura**. Todas las
escrituras y todas las lecturas van al mismo PostgreSQL por el mismo pool. De
ahí se sigue que las **diez operaciones de dominio son fuertemente
consistentes**: una lectura posterior a una escritura confirmada ve esa
escritura, siempre.

No es una virtud del diseño. Es una consecuencia del tamaño, y la tabla de
§8.6 existe sobre todo para dejar escrito **qué dejaría de ser cierto** si el
tamaño cambiara: una réplica, una caché o un contexto extraído convierten esa
línea en una tabla por operación.

### El hallazgo conceptual: lo que el usuario ve desfasado no son los datos

El panel refresca cada 8 segundos (`panel.js`) y la pantalla del cliente consulta
cada 3 (`config.js`). Así que lo que una persona ve puede estar hasta 8 segundos
desactualizado.

Llamar a eso «consistencia eventual» sería **falso**, y la distinción no es
académica:

| | Dónde vive | Cómo se reduce |
|---|---|---|
| Desfase de sondeo | Una constante en un archivo del sitio | Bajar el intervalo |
| Consistencia eventual | El almacenamiento | No se puede bajar: se diseña alrededor |

Confundirlos llevaría a resolver con arquitectura —réplicas, relojes, versiones—
un problema que es un número en un archivo de configuración. Este sistema tiene
lo primero y **no tiene** lo segundo.

### Y una operación que no tiene garantía ninguna

De las doce del contrato, `GET /metricas` es la única cuya respuesta **no sale de
la base de datos**: los percentiles los acumula una ventana en la memoria del
proceso. Se pierden al reiniciar y no son agregables entre procesos.

Importa porque es el endpoint con el que se miden las decisiones de esta misma
semana. Hoy hay un solo proceso y por eso sirve; el día que haya dos, es **lo
primero que miente, y lo haría en silencio**.

---

## 2. La caché: la decisión es «ninguna», y el motivo es un número

La pregunta no es si una caché ayudaría —casi siempre ayuda algo— sino **cuánto**
comparado con lo que cuesta. Medido contra el despliegue, sobre
`GET /v1/menu/establecimientos/1/items`:

| | |
|---|---|
| Ida y vuelta completa, desde fuera | **328 ms** (p50, n=12; mín. 281, máx. 775) |
| De eso, tiempo de servidor | **1,79 ms** (p50, n=26, vía `/metricas`) |
| Proporción | **0,55 %** |

Una caché de aplicación optimiza el tiempo de servidor. Aunque fuera perfecta
llevaría la experiencia de 328 ms a 326, que **no se distingue del ruido**: la
propia medición varía entre 281 y 775 ms.

Y el costo sí es real: **invalidación**. Una carta cacheada que no se invalida al
cambiar un precio muestra precios viejos, y un pedido creado contra un precio
viejo es una discrepancia con dinero de por medio. Se cambiaría un problema que
no existe por uno que sí.

La operación más lenta del sistema es `POST /v1/sesiones`, con **37,15 ms** de
p50, y es lenta **por diseño**: es scrypt derivando la contraseña. Es el único
sitio donde tardar es la función, no el costo. Cachearla sería desarmar la
defensa.

**Qué cambiaría la decisión**, comprobable sin discutirlo: que el tiempo de
servidor deje de ser el 0,55 %. `/metricas` lo publica, así que basta compararlo
con la ida y vuelta medida desde fuera.

---

## 3. El ADR: lo que el contrato promete y lo que de verdad corre

[ADR-0003](adr/0003-estrategia-integracion.md) ya comparó síncrono contra
asíncrono en septiembre, y acertó. Repetir esa comparación habría sido rellenar
un formulario. Lo que es nuevo es la **evidencia**:

| Lo que el contrato describe | Lo que corre |
|---|---|
| Un canal que publica `pedido.pagado` a quien se suscriba | `publicar()` se invoca y **no hay ningún suscriptor** |
| El panel se enteraría por ese evento | El panel **pregunta cada 8 segundos** |

`publicar()` es hoy, literalmente, una operación nula que devuelve `0`. Así que
la pregunta honesta no era «asíncrono o síncrono» sino: **el mecanismo que de
verdad notifica al panel es un sondeo que nadie documentó como decisión; se
queda, se sustituye por el empuje que el contrato promete, o se borra el canal
que no se usa.**

[ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md) evalúa las tres. Lo que
decide la segunda no es esfuerzo sino una limitación concreta:

> **Un bus en proceso no puede servir empuje correctamente.** Con un proceso
> funciona; con dos, un pago que procesa el proceso A no llega a un panel
> conectado al B, y el panel no se enteraría de que no se está enterando.

Un empuje correcto necesita un broker desplegado, y ahí entra la aritmética ya
escrita en [ADR-0009](adr/0009-no-extraer-un-servicio.md): caben 4 contenedores
y 512 MB, se usan 3 y 416. El broker entra en los 96 MB libres, pero gastaría el
**último contenedor disponible** en mejorar una frescura que ESC-03 no exige.

La tercera alternativa —borrar el canal— es la que exigió más honestidad, porque
su argumento es bueno: *un mecanismo sin usuarios es código que miente*. Se
descarta porque el contrato y la costura son lo que sostiene la reversibilidad
de ADR-0009, pero **se acepta su crítica**: la trampa se desactiva nombrándola y
con una prueba que falla el día que aparezca un suscriptor.

---

## 4. El hallazgo de la semana: un margen agotado que nadie había escrito

Es lo que más vale de la S12, y salió de cruzar dos documentos que nunca se
habían leído juntos.

[ESC-03](arc42/arc42.md#esc-03) concede **10 segundos** desde que un pedido se
paga hasta que el encargado lo ha visualizado y cambiado de estado. El estímulo
del escenario es *recibir un pedido pagado* y la respuesta incluye
*visualizarlo*, así que el tiempo que la cola tarda en mostrarlo **cuenta
dentro**.

El sondeo está fijado en **8000 ms**.

```
8 s de sondeo  +  2 s para que una persona vea y pulse  =  10 s exactos
```

**El margen es cero**, y no estaba escrito en ninguna parte. La constante que lo
consume citaba ESC-03, pero por las «3 interacciones», no por los 10 segundos.
Subirla a 12 000 «para aliviar carga» habría sido un cambio de una línea, sin
error visible y sin nada que se quejara, que incumple un escenario de calidad.

### Ahora se queja

`backend/tests/test_escenarios_de_calidad.py` ata la constante al umbral. **Y se
comprobó que falla**, que es la parte que una prueba nueva debe demostrar antes
de contar como mitigación:

| Defecto inyectado | Resultado |
|---|---|
| `MS_ENTRE_REFRESCOS` a 12 000 | **2 pruebas fallan** |
| Texto de Render devuelto a `index.html` | **falla** |
| Mención a la plataforma vieja sin su corrección al lado | **falla** |

Hay una segunda prueba que parece redundante y no lo es: comprueba que el margen
sigue agotado. Si alguien baja el intervalo y crea margen, **falla**, y obliga a
venir a retirar el riesgo de la documentación. Un riesgo resuelto que nadie borra
es la otra mitad del mismo problema.

### Lo que no se hizo, y por qué

Bajar el intervalo era lo tentador: dos segundos de margen por un carácter. No
se hizo porque **cambia el comportamiento en producción** —multiplica las
peticiones de cada panel abierto— y eso es una decisión de producto, no una
corrección de documentación. Queda medido, protegido y anotado como riesgo en
[arc42 §11](arc42/arc42.md#riesgos) para decidirlo con el número delante.

---

## 5. Seis defectos más del patrón de la S11

La semana 11 cerró con una conclusión: *la frontera más frágil no es ninguna
integración de red, es la configuración que une las piezas, y sus fallos no
producen un error sino un sistema que parece sano*
([§7.6](arc42/arc42.md#despliegue-deuda)).

Buscando los intervalos de sondeo aparecieron seis instancias más del mismo
patrón, en dos clases:

### Clase A — una premisa muerta que seguía explicando el sistema (4 archivos)

El sistema se desplegaba en el plan gratuito de Render, que dormía el servicio
tras 15 minutos. ADR-0008 lo movió al servidor del laboratorio el 13/10/2026, y
ADR-0004 quedó reemplazada **diciendo expresamente** que la plataforma nueva «no
tiene arranque en frío». El código no se enteró:

| Archivo | Qué decía | Gravedad |
|---|---|---|
| `sitio/index.html` | *«El servicio estaba dormido y se está despertando… es el arranque en frío del plan gratuito»* | **Alta: lo leía el usuario** |
| `sitio/config.js` | La constante se llamaba `MS_ANTES_DE_AVISAR_ARRANQUE_EN_FRIO` y el comentario justificaba su valor con Render | Media: el nombre se lee más que el comentario |
| `sitio/app.js` | El comentario de la pantalla 0 | Baja |
| `sitio/panel.js` | Justificaba pausar el sondeo con *«la cuota del plan gratuito»* | Baja |

El primero es el que importa y no es un comentario viejo: es **una causa falsa
delante de una persona**. Alguien que leía eso creía que el servicio despertaba y
esperaba un minuto que no iba a servirle de nada.

Corregido: el aviso se conserva —sigue habiendo motivos para que `/health`
tarde— pero **ya no afirma la causa**, porque desde el navegador no se puede
saber si es un reinicio o una red lenta. La constante pasó a
`MS_ANTES_DE_AVISAR_LENTITUD`.

### Clase B — un título que afirmaba una decisión que no se tomó (2 sitios)

ADR-0008 se titulaba *«…y bajo un solo origen»*. Pero el origen único **se
revirtió**: la plataforma no admite dos dominios con el mismo Host, y una tabla
**dentro del propio ADR** dice «Host aparte (lo que se hizo)».

Es peor que un título vago, porque arc42 §9 declara la regla que lo juzga: *el
título de cada ADR enuncia la decisión tomada, no el tema tratado*. Un título que
enuncia una decisión **no tomada** hace que el índice sea leíble y falso a la
vez. El índice de §9 repetía el error.

Corregido en los dos sitios, y el índice declara ahora qué ADR revisan a otras.

---

## 6. Lo que esta semana deliberadamente no añadió

| Patrón | Por qué no |
|---|---|
| **Caché** | El servidor es el 0,55 % de lo que ve el usuario. Medido (§2) |
| **Broker de mensajes** | Entra en los 96 MB libres, pero gasta el último contenedor para mejorar algo que ESC-03 no pide |
| **SSE o WebSocket** | Requiere el broker: un bus en proceso falla en silencio con dos procesos (§3) |
| **Réplica de lectura** | Crearía la consistencia eventual que hoy el sistema no tiene, para repartir una carga de 1,79 ms |
| **Outbox** | Heredado de la S11: un mecanismo para no perder mensajes que nadie recibe |

Las cinco están atadas a una condición comprobable, no a una preferencia. Y la
regla que las ordena es la misma que gobierna la caché: **medir la proporción
antes de optimizar el término.**

---

## 7. Verificación

```
289 passed, 1 skipped — 96,52 % de cobertura (con PostgreSQL)
228 passed, 62 skipped — sin PostgreSQL
```

De las nuevas: **7 en `test_escenarios_de_calidad.py`**, con los tres defectos
inyectados y comprobados (§4).

La cobertura **no se mueve** —914 de 947 sentencias, igual que en la S11— y es
lo correcto: esta semana no se añadió código de aplicación. Las correcciones
fueron a textos y comentarios del sitio, y lo nuevo es documentación y pruebas.
Una semana de arquitectura que no toca el dominio no debería mejorar la
cobertura, y si lo hiciera habría que preguntarse qué se colgó de paso.

| Elemento | Dónde |
|---|---|
| Consistencia por operación, caché e invalidación | [arc42 §8.6](arc42/arc42.md#consistencia) |
| Idempotencia y deduplicación | [arc42 §8.5](arc42/arc42.md#idempotencia) |
| Garantías de entrega del canal | [`docs/api/asyncapi.yaml`](api/asyncapi.yaml) |
| Reintentos y manejo de fallos | [arc42 §6.7](arc42/arc42.md#fallos-parciales) |
| ADR contra la alternativa síncrona | [ADR-0010](adr/0010-notificar-al-panel-por-sondeo.md) |
| Umbral de ESC-03, protegido | `backend/tests/test_escenarios_de_calidad.py` |
| Trazabilidad de ESC-03 actualizada | [`docs/aspectos.md`](aspectos.md) |
