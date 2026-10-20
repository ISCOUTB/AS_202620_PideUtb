# Evidencia S11 — Sistemas distribuidos: lo que este sistema tiene y lo que no

Fecha: **18/10/2026**.

Los tres entregables de la semana, y dónde está cada uno:

| Lo que se pide | Dónde |
|---|---|
| Tabla de modos de fallo con su mitigación | [arc42 §6.7](arc42/arc42.md#fallos-parciales) |
| Diseño de idempotencia o saga si aplica | [arc42 §8.5](arc42/arc42.md#idempotencia) |
| ADR con la decisión de extraer o no extraer un módulo | [ADR-0009](adr/0009-no-extraer-un-servicio.md) |

Este documento no los repite: explica **cómo se llegó a cada uno** y qué se
encontró por el camino, que es lo que no cabe en una tabla.

---

## 1. Lo primero fue arreglar el inventario

Antes de analizar fallos de integraciones hay que saber cuáles existen. El
inventario que el repositorio daba por bueno **estaba mal**, y de un modo que
habría invalidado todo el análisis.

### La integración saliente a la pasarela no existe

El C4 de nivel 2 declaraba una flecha «API PideUTB → Wompi Sandbox · HTTPS ·
JSON · Síncrono». En el código:

```python
_URL_CHECKOUT = "https://sandbox.wompi.co/checkout"
...
url_checkout=f"{_URL_CHECKOUT}/{referencia}",
```

`iniciar_intento` guarda una fila y **construye una cadena de texto**. No hay
cliente HTTP, no hay llamada, no hay nadie al otro lado esperando. El usuario va
a esa URL con su navegador y la pasarela vuelve por el webhook.

**Consecuencia directa sobre lo que la semana pide:** no hay ninguna integración
saliente a la que aplicar **reintentos con backoff**. Para implementarlos habría
que inventar primero la llamada.

Es el mismo tipo de defecto que la semana 10 encontró dos veces —el diagrama
afirmando que Supabase autenticaba, y el nivel 2 diciendo que se desplegaba en
Vercel— y por tercera vez la causa es la misma: **una afirmación de integración
que nadie volvió a comprobar contra el código.**

### Las fronteras que de verdad hay

| Frontera | ¿Cruza la red? |
|---|---|
| Navegador → sitio | Sí |
| Navegador → API | Sí, y **otro origen**: depende de CORS |
| API → base de datos | **No.** Contenedor vecino, ~1 ms |
| Pasarela → API (webhook) | Sí, **entrante**, al-menos-una-vez |
| API → pasarela | **No existe** |

Son dos de verdad, y una de ellas dejó de cruzar la red esta misma semana con
[ADR-0008](adr/0008-despliegue-en-el-servidor-del-laboratorio.md).

---

## 2. El hallazgo: una ventana de inconsistencia real

`pagos.service.procesar_evento` hace dos escrituras:

```python
pedido, ya_estaba_pagado = pedidos_service.confirmar_pago(intento.pedido_id)
repository.guardar(intento.model_copy(update={"estado_pago": APROBADO}))
```

Cada repositorio abre su propia conexión y **confirma al salir**: son dos
transacciones. Un corte entre ellas deja el pedido **pagado con su código** y el
intento **todavía pendiente**.

**No se ve desde fuera.** Nadie recibe un error. El cliente se lleva su comida y
la contabilidad dice otra cosa.

### Reproducido, no descrito

`test_fallos_parciales.py` lo provoca haciendo fallar la segunda escritura:

```
test_un_corte_entre_las_dos_escrituras_deja_el_intento_descolgado  PASSED
```

y comprueba las dos mitades: que el pedido sí quedó pagado con código, y que el
intento sigue pendiente.

### Las cuatro opciones, y por qué se eligió la cuarta

| Opción | Veredicto |
|---|---|
| Una transacción compartida entre los dos contextos | **Descartada.** Exige que Pagos pase su conexión a Pedidos, rompiendo ADR-0001 en la capa de datos |
| Invertir el orden de las escrituras | **Descartada.** Empeora el daño: el cliente se queda sin código |
| Una saga con compensación | **No aplica.** Las dos escrituras van a la misma base: no falta un coordinador, falta una transacción |
| Conservar la frontera y **hacer la ventana visible** | **Elegida** |

`pagos.service.conciliar()` devuelve las referencias cuyo pedido está pagado y
cuyo intento sigue pendiente. En un sistema sano devuelve lista vacía, y hay una
prueba que lo comprueba — **sin ella, una conciliación rota devolvería siempre
vacío y pasaría por un sistema impecable**.

### Por qué la ventana es transitoria

La pasarela entrega al-menos-una-vez: si no recibe `2xx`, reintenta, y el
reintento rehace ambas escrituras. `test_el_reintento_de_la_pasarela_cierra_la_ventana`
lo demuestra, y `test_el_reintento_no_genera_un_segundo_codigo` comprueba lo que
no puede pasar al curarse.

Si la pasarela se rinde, queda abierta. Por eso la conciliación existe igual.

---

## 3. Idempotencia: tres mecanismos, y uno que sostiene a los otros

El detalle está en [arc42 §8.5](arc42/arc42.md#idempotencia). Lo que vale
resumir aquí es **por qué la condición va dentro del `UPDATE`**:

```python
confirmado = repository.marcar_pagado(pedido_id, _generar_codigo_canje())
```

```sql
UPDATE pedidos SET estado = 'pagado', codigo_canje = %s
WHERE id = %s AND estado = 'pendiente_pago'
```

Con leer–decidir–escribir, dos avisos simultáneos del mismo pago ven los dos
«pendiente» y generan **dos códigos** para un pedido; el segundo sobrescribe al
primero, de modo que el cliente que ya vio el suyo se queda con uno que no
sirve. Con la condición dentro, PostgreSQL serializa y la segunda no encuentra
fila.

**La base de datos es el árbitro** y no hace falta coordinación entre procesos.

### Y lo que a propósito no es idempotente

`pedidos.avanzar_estado` devuelve `409` al repetir. Lo dispara una persona
pulsando un botón, no un sistema reintentando, y ahí el `409` es información
útil: «otra persona ya movió este pedido». La regla que se sigue:
**idempotente donde la entrega es al-menos-una-vez; explícito donde hay alguien
mirando.**

---

## 4. No se extrae nada, y el motivo no es preferencia

[ADR-0009](adr/0009-no-extraer-un-servicio.md) evalúa el candidato real —
`pagos`, por ser la única frontera con un tercero y por ser donde está el
dinero — y lo descarta.

Lo que decide no es gusto arquitectónico sino aritmética:

| | Hoy | Con `pagos` extraído |
|---|---|---|
| **Contenedores** | **3** de 4 permitidos | **5** de 4 |
| Memoria | **416 MB** de 512 *(medido)* | **~704 MB** de 512 *(estimado)* |

Un servicio con base propia son dos contenedores más. Con la cuota del servidor
del laboratorio, extraer `pagos` **no es caro: es imposible**.

**La fila que decide es la primera**, y las dos cifras no son de la misma clase:
el 416 es la suma de los límites declarados en `deploy/compose.lab.yaml`, y el
704 es una estimación —`pagos` a ~128 MB por el piso del runtime, más ~160 del
PostgreSQL que necesitaría—. Si `pagos` pidiera lo mismo que `api` serían 768;
en los dos casos pasa de 512, así que la conclusión no depende del estimado.
El desglose está en [ADR-0009](adr/0009-no-extraer-un-servicio.md).

Y el argumento de fondo, que vale aunque la cuota cambie: **extraer `pagos`
crearía exactamente los problemas que esta semana pide analizar** —una
transacción que ya no puede ser una, una saga para compensar reembolsos, una
llamada de red donde hoy hay una llamada en proceso— sin resolver ninguno de los
seis motivos por los que un contexto se separa.

El ADR deja además las cinco condiciones comprobables que cambiarían la
decisión, y lo que se hace para que la extracción siga siendo barata: la regla
de dependencia verificada en cada push, el lenguaje publicado en las fronteras y
el canal de eventos con su contrato ya escrito.

---

## 5. La frontera que ninguna prueba cubre

Hay un hallazgo que no estaba en el guion de la semana y que es, con diferencia,
el que más costó.

La puesta en marcha en el servidor del laboratorio encontró **cinco defectos que
las 282 pruebas no podían ver**:

| Defecto | Síntoma | Por qué la suite no lo veía |
|---|---|---|
| CORS sin `Authorization` ni `DELETE` | Panel roto en el navegador | `TestClient` no hace *preflight* |
| `log_format` dentro de `server` en nginx | Contenedor reiniciando en bucle | pytest no arranca nginx |
| `add_header` sin heredar en `/panel.html` | `X-Frame-Options` ausente, **sin síntoma** | idem |
| `wget --tries` en un chequeo de Alpine | `404` de Traefik con nginx sano | idem |
| `crear_usuario.py` reventaba tras escribir | Traceback engañoso | Nadie lo ejecutaba en CI |

El patrón es el mismo en los cinco: **la prueba y el entorno real no recorren el
mismo camino**.

Dicho en los términos de la semana: la frontera más frágil de este sistema no es
ninguna de las dos integraciones de red. Es **la configuración que une las
piezas** — y es la única cuyos fallos no producen un error, sino un sistema que
parece sano y no funciona.

La mitigación está en [arc42 §7.6](arc42/arc42.md#despliegue-deuda) y es barata:
instalar Docker en la máquina de desarrollo para poder ejecutar el mismo compose
que corre el servidor. Los cinco se habrían visto en treinta segundos.

---

## 6. Lo que esta semana deliberadamente no añadió

| Patrón | Por qué no |
|---|---|
| **Reintentos con backoff** | No hay integración saliente a la que aplicarlos (§1) |
| **Saga** | Las escrituras van a la misma base: falta una transacción, no un coordinador |
| **Outbox** | El canal `pedidos-pagados` tiene contrato y publicador y **cero suscriptores**. Un mecanismo para no perder mensajes que nadie recibe resuelve un problema que no se tiene |
| **Circuit breaker** | Sin llamadas salientes, no hay circuito que abrir |

Las cuatro decisiones están atadas a algo que falla si dejan de ser ciertas. La
del outbox, por ejemplo, a
`test_el_evento_se_pierde_si_no_hay_nadie_escuchando`, que **falla el día que
aparezca un suscriptor** y obliga a revisarla en vez de heredarla.

Implementar un patrón que el sistema no necesita tiene un costo que no se ve en
la demostración y sí en la siguiente persona que lea el código: lo encuentra,
asume que resuelve algo, y construye encima.

---

## 7. Verificación

```
282 passed, 1 skipped — 96,52 % de cobertura (con PostgreSQL)
221 passed, 62 skipped — sin PostgreSQL
```

De las nuevas: **8 en `test_fallos_parciales.py`** y **3 en
`test_repositorios.py`**, estas últimas ejecutadas contra las dos
implementaciones — porque una conciliación que solo funciona en memoria no dice
nada del sistema que corre en producción.

| Elemento | Dónde |
|---|---|
| Modos de fallo parciales | [arc42 §6.7](arc42/arc42.md#fallos-parciales) |
| Diseño de idempotencia | [arc42 §8.5](arc42/arc42.md#idempotencia) |
| Decisión de no extraer | [ADR-0009](adr/0009-no-extraer-un-servicio.md) |
| Conciliación | `app/pagos/service.py::conciliar` |
| Pruebas de fallo parcial | `backend/tests/test_fallos_parciales.py` |
| Deuda de configuración | [arc42 §7.6](arc42/arc42.md#despliegue-deuda) |
