# Evidencia S14 — Evaluación: medir convirtió una preferencia en un defecto

Fecha: **18/10/2026**.

| Lo que se pide | Dónde |
|---|---|
| Medir un atributo de calidad contra su umbral | [arc42 §10.7](arc42/arc42.md#evaluacion) · `backend/scripts/medir_esc03.py` |
| arc42 §11 con riesgos y deuda técnica | [arc42 §11](arc42/arc42.md#riesgos) — 10 riesgos, 4 deudas |

---

## 1. El resultado: ESC-03 no se cumplía, y nadie lo habría notado

La S12 encontró que el sondeo del panel se comía 8 de los 10 segundos que
[ESC-03](arc42/arc42.md#esc-03) concede. Lo dejé anotado como riesgo R-01 con una
estimación —«quedan 2 segundos para la persona»— y **aplacé la decisión**, porque
bajar el intervalo cambia el comportamiento en producción y me pareció una
decisión de producto.

Esta semana lo medí entero. La estimación estaba mal:

| Tramo | Medido |
|---|---|
| [1] Espera al siguiente sondeo *(peor caso)* | 8 000,0 ms |
| [2+4] Red, dos idas y vueltas con conexión reutilizada | 301,6 ms |
| [2+4] Servidor, p95 de leer la cola y cambiar el estado | 18,7 ms |
| **Consumido sin contar a la persona** | **8 320,3 ms** |
| **Quedaba para que la persona viera y pulsara** | **1,68 s** |

Lo que faltaba en la estimación eran **los 301,6 ms de red**, que no había
contado: dos idas y vueltas, una para ver la cola y otra para cambiar el estado.

Con 1,68 s para notar un pedido nuevo mientras se cocina, **el escenario se
incumplía** en el peor caso —el pago ocurre un milisegundo después de un
sondeo—. Y se incumplía sin que nada fallara: el pedido simplemente aparecía
tarde, que es el tipo de defecto que no produce un error sino una queja.

### Eso cambió la naturaleza de la decisión

En la S12 dije que bajar el intervalo era cosa tuya, y con la información que
tenía era lo correcto: un margen estrecho es una preferencia. Un umbral que **no
se cumple** es un defecto, y eso no se aplaza.

Se bajó a **5 000 ms**:

| | Con 8 000 ms | Con 5 000 ms |
|---|---|---|
| Consumido | 8 320,3 ms | **5 320,5 ms** |
| Queda para la persona | 1,68 s | **4,68 s** |

El 5 000 no es un número redondo elegido a ojo: es el más largo que cabe
reservando 4 segundos para la persona, con 0,68 de holgura.

**El costo, medido:** 12 sondeos por minuto en vez de 7,5. A ~8 ms de servidor
cada uno son **46 segundos de CPU por turno de 8 horas y panel abierto**, contra
los 0,5 CPU del contenedor. Y el panel ya deja de sondear cuando su pestaña está
oculta, así que ese es el peor caso, no el normal.

### La prueba que nació fallando cumplió su función

En la S12 escribí `test_el_margen_de_esc_03_esta_agotado_y_eso_consta`, que
afirmaba que el margen estaba agotado para que **crear margen obligara a volver a
mirar el riesgo**. Esta semana la medición creó el margen, la prueba falló como
estaba previsto, y volví.

Ahora son dos y fijan el intervalo por los **dos** lados:

| Prueba | Qué impide |
|---|---|
| `test_el_refresco_del_panel_cabe_en_el_presupuesto_de_esc_03` | Que suba y rompa el umbral |
| `test_el_refresco_es_el_mas_largo_que_cabe_en_el_presupuesto` | Que baje sin motivo y multiplique peticiones por nada |

Las dos usan ahora el costo real de red y servidor, no un número redondo.
Comprobadas con su defecto inyectado: 6 000 ms falla la primera, 2 000 ms falla
la segunda.

---

## 2. La medición es ejecutable, no una cita

`backend/scripts/medir_esc03.py` rehace el cálculo completo y **devuelve código
de error si el escenario no se cumple**:

```
VEREDICTO: ESC-03 se cumple con 4.68 s de margen para la persona.
```

Tres decisiones de diseño del guion que son el punto:

**Exige PostgreSQL y se niega a correr sin él.** La cola del mostrador se lee con
una consulta cuyo coste crece con los pedidos del establecimiento; en memoria eso
es un filtro sobre un diccionario. Daría un número bonito y falso.

**Mide con una cola realista** (10 pedidos por defecto). Con un solo pedido
mediría el caso que nunca ocurre, y el escenario habla expresamente de «varios
pedidos simultáneos».

**La red entra por parámetro, no se mide.** Depende de dónde esté quien mira, y
una medición que depende de la red falla por motivos que no son el defecto que
busca.

---

## 3. El hallazgo de método: el portátil no es el contenedor

Todas las mediciones de servidor se hacen en la máquina de desarrollo. Antes de
usarlas había que saber cuánto se parece a producción, y la respuesta salió de la
única operación de la que hay muestras en los dos sitios:

| | `GET /v1/menu/.../items`, p50 |
|---|---|
| Portátil de desarrollo | **7,56 ms** |
| Contenedor de producción | **1,68 ms** |
| | **El portátil es 4,5× más lento** |

Dos consecuencias.

**La evaluación es conservadora.** Los números de servidor son una cota superior:
en producción son menores. Es la dirección correcta para equivocarse.

**Y confirma el riesgo R-02 por una vía independiente.** Los parámetros de scrypt
se eligieron midiendo **100 ms en el portátil** y producción deriva en unos **35**
— un factor de 2,9. Esa discrepancia podía ser un error de medición. Ahora hay
una segunda operación, sin relación con la primera, que da entre 3 y 4,5 veces en
la misma dirección: **el contenedor es más rápido que la máquina donde se tomó la
decisión**, y la defensa vale menos de lo que el ADR supone.

Es un recordatorio de algo que esta semana deja escrito en
[§10.7](arc42/arc42.md#evaluacion): **una cifra sin su máquina no es una
medición.**

---

## 4. Los otros cuatro escenarios, y lo que su holgura significa

| Escenario | Umbral | Medido | Veredicto |
|---|---|---|---|
| [ESC-01](arc42/arc42.md#esc-01) | < 3 min | ≈ 163 ms de servidor + red | **Cumple** · 0,09 % del presupuesto |
| [ESC-02](arc42/arc42.md#esc-02) | < 2 min en ≥ 90 % | ≈ 163 ms | **Cumple** · 0,14 % |
| [ESC-04](arc42/arc42.md#esc-04) | < 2 s · 100 % de reutilizaciones rechazadas | ≈ 161 ms | **Cumple** · 8 % del umbral |
| [ESC-05](arc42/arc42.md#esc-05) | Mensaje < 3 s · pedido conservado 100 % | ≈ 164 ms | **Cumple** |

Cuatro de cinco cumplen con dos o tres órdenes de magnitud de holgura, y **eso no
es un elogio**: significa que el servidor no es el cuello de botella de ninguno.
Es la misma conclusión a la que llegó [§8.6](arc42/arc42.md#consistencia) para la
caché, y por el mismo camino — medir la proporción antes de optimizar el término.

Dos de los cuatro no se cumplen por latencia sino por **estructura**, y conviene
distinguirlo:

- El 100 % de reutilizaciones rechazadas de ESC-04 no es una cifra de
  rendimiento: lo garantiza la máquina de estados, porque `entregado` es final.
- El 100 % de pedidos conservados de ESC-05 tampoco: el pedido se persiste
  **antes** de empezar el cobro ([ADR-0003](adr/0003-estrategia-integracion.md)).

Un umbral que se cumple por diseño es más fuerte que uno que se cumple por
medición, porque no depende de la máquina.

---

## 5. La línea base de ESC-02, actualizada

Estaba medida contra el almacenamiento en memoria, que era el único que había:

| | En memoria (S7) | Con PostgreSQL (S14) |
|---|---|---|
| p50 | 2,66 ms | **9,37 ms** |
| **p95** | **3,02 ms** | **11,67 ms** |

Cuadruplica, y era de esperar: hay una consulta real en medio. No cambia ningún
veredicto —pasa de usar el 0,0025 % del presupuesto de ESC-02 a usar el
0,0097 %— pero la cifra que circulaba ya no era la del sistema que corre. Queda
en [`linea-base.md` §5](linea-base.md).

---

## 6. Lo que esta evaluación deliberadamente no hizo

| | Por qué |
|---|---|
| **Prueba de carga** | R-07 —14 peticiones/s saturan el contenedor— es aritmética sobre una medición de **una** petición. Medirlo de verdad exige generar carga contra producción, y eso es un ataque a un servidor compartido con 22 equipos: se pide permiso antes, no después |
| **Medir desde el campus** | Es donde estarán los usuarios y donde la cifra de red importa. No tengo acceso a esa red |
| **Corregir R-07** | Las dos salidas se estorban: un límite por IP en memoria funciona hoy y falla en silencio con dos procesos; subir el coste de scrypt mejora R-02 y empeora R-07. Y hay un problema de fondo: detrás de un proxy, limitar por IP exige confiar en una cabecera que cualquiera puede falsificar si alcanza el origen |
| **Cerrar R-08 y R-09** | Registrar quién avanza un pedido es un cambio de modelo de datos; autenticar `/metricas` exige decidir quién tiene esa credencial |

El de R-07 merece una línea más, porque la alternativa que la medición sugiere no
es la obvia: en vez de limitar por IP, **acotar las derivaciones concurrentes**.
No depende de ninguna cabecera, el límite es exactamente el recurso que se quiere
proteger, y el modo de fallo bajo ataque es honesto —se encola o se rechaza el
inicio de sesión— en vez de dejar caer el sistema entero. Queda propuesto, no
implementado: cambia el comportamiento bajo ataque y merece su propia revisión.

---

## 7. Verificación

```
322 passed, 62 skipped — sin PostgreSQL
```

| Elemento | Dónde |
|---|---|
| Evaluación de los cinco umbrales | [arc42 §10.7](arc42/arc42.md#evaluacion) |
| Riesgos y deuda | [arc42 §11](arc42/arc42.md#riesgos) — R-01 cerrado, R-02 reforzado |
| Medición ejecutable de ESC-03 | `backend/scripts/medir_esc03.py` |
| Intervalo fijado por los dos lados | `backend/tests/test_escenarios_de_calidad.py` |
| Línea base con PostgreSQL | [`linea-base.md` §5](linea-base.md) |
| Trazabilidad de ESC-03 | [`aspectos.md`](aspectos.md) |
