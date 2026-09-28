# Evidencia de despliegue — Semana 8

Todo lo que aparece aquí se obtuvo **del entorno desplegado**, no de la máquina
de desarrollo. Cada bloque se puede reproducir con el comando que lo acompaña.

Fecha de captura: **27/09/2026**.

---

## 1. URLs públicas

| Pieza | URL | Verificación |
|---|---|---|
| **Sitio** | https://pideutb-sitio.onrender.com | `HTTP 200`, sirve `<title>PideUTB — pedidos en el campus</title>` |
| **API** | https://pideutb-api.onrender.com | `HTTP 200` en `/health` |
| **Base de datos** | Proyecto `yrjkdtzunngjasembvlv`, región `us-east-1` | Creada por Terraform |

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://pideutb-sitio.onrender.com/
curl -s https://pideutb-api.onrender.com/health
```

Las dos son accesibles desde cualquier red, sin credenciales ni túnel: la API
tiene que serlo por diseño, porque la pasarela de pagos le envía el webhook
desde su propia infraestructura ([ADR-0003](adr/0003-estrategia-integracion.md)).

---

## 2. Infraestructura como código

De las cinco piezas desplegables, **cuatro están declaradas** en
[`infra/`](../infra/) y una no. La excepción está documentada, no disimulada.

| Pieza | En Terraform | Archivo |
|---|---|---|
| Sitio | Sí | [`render.tf`](../infra/render.tf) |
| Base de datos | Sí | [`supabase.tf`](../infra/supabase.tf) |
| Protección de rama | Sí | [`github.tf`](../infra/github.tf) |
| Pipeline | Sí (el workflow es código versionado) | [`ci.yml`](../.github/workflows/ci.yml) |
| **API** | **No** | Procedimiento manual en [`infra/README.md`](../infra/README.md) |

La API queda fuera porque el proveedor de Terraform de Render **no admite el
plan gratuito**: `render_web_service` acepta `starter`, `standard` y `pro`, pero
no `free` ([issue #105](https://github.com/render-oss/terraform-provider-render/issues/105)).
Se eligió costo cero sobre cobertura total de IaC, y se escribió el
procedimiento manual paso a paso para que la excepción sea repetible.

Salida real del `apply`:

```
Plan: 3 to add, 0 to change, 0 to destroy.

sitio_url            = "https://pideutb-sitio.onrender.com"
supabase_project_ref = "yrjkdtzunngjasembvlv"
```

Los secretos **no** están en Terraform, y tampoco por comodidad: el archivo de
estado guarda en claro todo lo que gestiona, así que declararlos ahí los dejaría
escritos. El motivo está anotado en [`infra/github.tf`](../infra/github.tf).

---

## 3. Chequeo de salud que no miente

```bash
curl -s https://pideutb-api.onrender.com/health
```

```json
{"status":"ok","dependencias":{"catalogo":{"estado":"ok","tipo":"memoria","latencia_ms":0.01,"detalle":null}}}
```

Tres cosas que este cuerpo demuestra y un `{"status":"ok"}` no demostraría:

1. **Sondea de verdad.** `catalogo` se obtuvo ejecutando la misma consulta que
   sirve la carta, no devolviendo una constante.
2. **Declara lo que hay.** `tipo: "memoria"` dice que el almacenamiento es
   memoria del proceso y no una base de datos. Es la limitación
   [V-09](violaciones.md), dicha en voz alta por el propio sistema.
3. **Solo reporta lo comprobado.** `base_de_datos` **no aparece**, y es
   deliberado: el código todavía no abre ninguna conexión a Supabase, así que
   anunciarla sería describir una arquitectura que no está desplegada. La sonda
   existe en [`app/salud.py`](../backend/app/salud.py) y se activa con
   `PIDEUTB_SUPABASE_URL` el día que los repositorios la usen.

El endpoint devuelve **`503`** cuando una dependencia cae. Que *pueda* fallar se
prueba en [`test_health.py`](../backend/tests/test_health.py), que lo rompe a
propósito: dependencia caída, sonda que lanza una excepción, y catálogo que
responde vacío —el fallo silencioso más peligroso, porque el usuario vería una
carta vacía y concluiría que no hay comida—.

El código HTTP importa más que el cuerpo: la plataforma decide si enrutar
tráfico leyéndolo, y un `200` con `{"estado":"mal"}` dentro la dejaría mandando
usuarios a un servicio roto. El servicio está configurado con
*Health Check Path* `/health`, así que Render lo consulta cada pocos segundos.

---

## 4. Logs estructurados

Una línea JSON por petición, a salida estándar:

```json
{"timestamp":"2026-09-27T13:56:45-0500","level":"INFO","service":"api","event":"peticion_atendida","request_id":"bb5f3c510989","method":"GET","path":"/health","status":200,"duration_ms":1.91}
```

Van a **stdout y no a un archivo** porque el disco del contenedor es efímero:
un log en disco desaparecería en cada despliegue. La plataforma recoge stdout.

Se registra la **ruta con plantilla** (`/v1/pedidos/{pedido_id}`) y no la
concreta. Sin eso, cada identificador produciría su propia serie y el percentil
por operación no serviría de nada.

El `request_id` vuelve en la respuesta, así que quien reporta un problema puede
citarlo y se encuentra su petición exacta sin adivinar por la hora:

```bash
curl -si https://pideutb-api.onrender.com/health | grep -i x-request-id
```

```
x-request-id: a68a9e249a6c
```

Si el cliente envía uno propio, se respeta, para que la traza no se corte al
cruzar de un servicio a otro.

**Qué no se registra**, y hay pruebas que lo verifican: la firma del webhook
(`X-Firma-Evento`), tokens, contraseñas ni cuerpos completos. Además `httpx`
está subido a `WARNING` porque registraba en `INFO` la URL completa de cada
llamada saliente, que es la vía más común por la que un token acaba escrito en
un log.

---

## 5. Métrica consultable, ligada a un escenario

```bash
curl -s https://pideutb-api.onrender.com/metricas
```

```json
{"ventana_maxima":1000,"operaciones":{
  "GET /health":{"muestras":9,"p50_ms":0.83,"p95_ms":2.09,"max_ms":2.09},
  "GET /v1/menu/establecimientos/{establecimiento_id}/items":{"muestras":1,"p50_ms":1.66,"p95_ms":1.66,"max_ms":1.66},
  "POST /v1/pedidos":{"muestras":1,"p50_ms":1.58,"p95_ms":1.58,"max_ms":1.58}
}}
```

El escenario es **[ESC-02](arc42/arc42.md#esc-02)**: *el proceso completo toma
menos de 2 minutos en al menos el 90 % de los intentos*.

**Qué mide esta métrica y qué no.** No mide ESC-02 entera, y decir lo contrario
sería exagerar lo que prueba: esos 120 segundos incluyen el tiempo que una
persona tarda en decidir qué comer, que no ocurre en el servidor. Mide **la
parte del presupuesto que el servidor controla**, en `p95_ms` de
`POST /v1/pedidos`. Sirve para distinguir un escenario incumplido por lentitud
del backend de uno incumplido por el arranque en frío.

Con esa lectura, el dato dice que **el backend no es el problema**: 1,58 ms
sobre un presupuesto de 120 000 ms. Lo que sí amenaza a ESC-02 es el arranque en
frío de ~60 s, que se come la mitad del presupuesto antes de que el usuario vea
la carta — y es justo el costo que [ADR-0004](adr/0004-plataforma-de-despliegue.md)
acepta a cambio de un despliegue de 0 USD.

**Límites declarados**, porque un número sin su alcance se malinterpreta:

- `muestras: 1` para `POST /v1/pedidos`. Un p95 sobre una muestra **no significa
  nada estadísticamente**; el campo `muestras` se publica precisamente para que
  nadie lo lea como si significara algo.
- La ventana mide **un** proceso, guarda las últimas 1000 peticiones y se
  reinicia con el servicio. No sustituye a un sistema de métricas; sustituye a
  no tener ninguno.
- `ventana_maxima` viaja junto a los datos porque un percentil sin su ventana no
  es interpretable.

---

## 6. El sistema funciona de punta a punta

Carta y creación de pedido, contra el entorno desplegado:

```bash
curl -s https://pideutb-api.onrender.com/v1/menu/establecimientos/1/items
curl -s -X POST https://pideutb-api.onrender.com/v1/pedidos \
  -H "Content-Type: application/json" -d '{"item_id":1,"cantidad":2}'
```

```json
{"establecimiento_id":1,"items":[{"item_id":1,"establecimiento_id":1,"nombre":"Arepa de huevo","precio_centavos":400000,"disponible":true}, …]}
```

```json
{"pedido_id":1,"establecimiento_id":1,"item_id":1,"nombre_item":"Arepa de huevo",
 "precio_unitario_centavos":400000,"cantidad":2,"total_centavos":800000,
 "estado":"pendiente_pago","codigo_canje":null}
```

Dos decisiones de diseño visibles en esa respuesta:

- **`total_centavos: 800000`** — el dinero viaja como entero en centavos, con la
  unidad en el nombre del campo. Dos arepas de 4 000 COP son 8 000 COP. Cierra
  [V-07](violaciones.md): un `float` para dinero acumula error de redondeo.
- **`codigo_canje: null`** — el código no existe hasta que el pago se confirma.
  Llega por el canal asíncrono, no en esta respuesta.

### Verificado también desde un navegador, que es lo que `curl` no prueba

Abriendo https://pideutb-sitio.onrender.com se pasó la pantalla de arranque, se
pintó la carta con los precios formateados en pesos (`$ 4.000`, `$ 3.000`) y al
pulsar **Pedir** apareció la pantalla «Tu pedido» con el total y los tres
métodos de pago. Sin errores en la consola.

Esta comprobación aporta algo que los `curl` de arriba no pueden aportar:
**demuestra que CORS está bien configurado**. `curl` ignora la política de
orígenes —no es un navegador—, así que habría funcionado igual con la
configuración mal puesta. El sitio y la API son dos desplegables distintos y en
orígenes distintos, así que sin `PIDEUTB_ORIGENES_PERMITIDOS` correcta el
navegador habría bloqueado cada llamada.

La lista de orígenes llega por variable de entorno y **nunca es `*`**
(`app/main.py`): un comodín dejaría que cualquier página de Internet llamara a
esta API con el navegador de un usuario.

---

## 7. Lo que NO está hecho

Declararlo es parte de la evidencia. Un informe que solo muestra lo que salió
bien no permite juzgar nada.

| # | Qué falta | Consecuencia real |
|---|---|---|
| 1 | El estado sigue en memoria del proceso ([V-09](violaciones.md)) | Cada redespliegue pierde los pedidos en curso, y Render redespliega en cada push a `master`. La base de datos está creada y declarada, pero los `repository.py` todavía no la usan |
| 2 | La API no está en Terraform | Recrear el entorno desde cero exige el paso manual de `infra/README.md` |
| 3 | No hay entorno de pruebas separado | Se despliega contra el mismo entorno que se demuestra |
| 4 | No hay alerta automática | El `503` lo ve la plataforma, pero nadie recibe aviso: hay que mirar |
| 5 | ESC-02 en riesgo tras inactividad | El arranque en frío consume ~60 de los 120 s disponibles. Se mitiga avisando al usuario (`sitio/config.js`), no se elimina |

El punto 1 es el que más pesa, y el chequeo de salud lo dice por su cuenta:
responde `tipo: "memoria"`. La decisión de desplegar antes de migrar fue
deliberada — una URL imperfecta que funciona vale más que una perfecta que no
existe, y la migración se hace encima del despliegue ya montado.

---

## 8. Trazabilidad

| Qué | Dónde |
|---|---|
| Comparación de las dos alternativas, 20 criterios | [`comparacion-despliegue.md`](comparacion-despliegue.md) |
| Decisión de plataforma | [ADR-0004](adr/0004-plataforma-de-despliegue.md) |
| Vista de despliegue | [arc42 §7](arc42/arc42.md#7-vista-de-despliegue) |
| Restricciones actualizadas | arc42 §2.1 |
| Infraestructura declarada | [`infra/`](../infra/) |
| Chequeo de salud | [`app/salud.py`](../backend/app/salud.py), [`test_health.py`](../backend/tests/test_health.py) |
| Logs y métricas | [`app/observabilidad.py`](../backend/app/observabilidad.py), [`test_observabilidad.py`](../backend/tests/test_observabilidad.py) |
| Contrato de las sondas | [`openapi.yaml`](api/openapi.yaml) `/health` y `/metricas`, versión 1.1.0 |
| Por qué el salto fue MINOR y no MAJOR | [`politica-versionado.md`](api/politica-versionado.md) §6 |
