# Evidencia S10 — Lo que las correcciones destaparon

Fecha: **12/10/2026**.

Esta entrega nació como una lista de correcciones a dos retroalimentaciones.
Terminó encontrando **seis defectos que ninguna prueba veía**, y la mitad de
ellos estaban en las verificaciones mismas.

Todo lo que aparece aquí se comprobó ejecutando algo: la suite, la API
desplegada, un PostgreSQL local o un navegador. Cada bloque trae el comando o
el archivo que lo reproduce.

---

## 0. Resumen: qué se pidió y qué apareció

| Lo que la retroalimentación pedía | Lo que apareció al hacerlo |
|---|---|
| Autenticar el panel (V-10) | Cerrarlo obligó a subir el contrato a MAYOR, y al medirlo se vio que **la regla que lo exige no estaba implementada** (§2) |
| Retirar del repositorio el valor del secreto | Hecho, y la prueba que lo usaba se volvió **más fuerte** al perderlo (§3) |
| Acreditar la rotación y el despliegue seguro | Hecho contra la API de Render, sin leer el secreto (§3) |
| Reconciliar el C4 con la autenticación | El diagrama **describía una protección que no existía** durante tres entregas (§4) |
| Separar el tiempo local del flujo real en ESC-03 | **ESC-03 no se cumple con el servicio frío**, y los dos números para verlo llevaban semanas en el repositorio (§5) |
| Completar la fila ESC-03 de `aspectos.md` | Y además: tres filas del arc42 decían «pendiente» de cosas implementadas (§4) |

Y lo que no se pidió y hubo que hacer igual:

| Defecto | Cómo se encontró | §|
|---|---|---|
| El comparador de contratos daba **cero** roturas para el cambio más grande del proyecto | Midiendo en vez de suponer | §2 |
| La comparación de compatibilidad se habría **apagado para siempre** al subir de MAYOR | Leyendo por qué la prueba salía «omitida» | §2 |
| CORS no permitía `Authorization`: el panel roto con la suite en verde | Abriendo la página | §6 |
| El aviso de código incorrecto se escribía y se borraba solo | Abriendo la página | §6 |
| El botón «Entregado» quedaba gris para siempre tras un fallo | Abriendo la página | §6 |
| `crear_usuario.py` creaba la cuenta y después reventaba | Ejecutándolo | §7 |

---

## 1. La cadena de ESC-04, cerrada

**La porción:** la verificación del código de recogida. Estaba marcada como
pendiente desde la semana 5 y no podía cerrarse antes, porque **no se puede
exigir un código sin saber quién entrega**: sin sesión, el endpoint que marca
«entregado» lo puede llamar el propio estudiante.

| Eslabón | Dónde |
|---|---|
| **Aspecto** | Fila de ESC-04 en [`aspectos.md`](aspectos.md): *Confiabilidad · Seguridad* |
| **Escenario** | [ESC-04](arc42/arc42.md#esc-04) — validación en < 2 s, rechazo del 100 % de reutilizaciones |
| **Decisión propia** | [ADR-0007](adr/0007-autenticacion-del-panel.md) |
| **Código** | `app/pedidos/service.py` (`avanzar_estado`, `_codigo_coincide`) · `app/autenticacion.py` · `app/usuarios/` |
| **Esquema** | `backend/migraciones/003_autenticacion.sql` |
| **Contrato** | [`openapi.yaml`](api/openapi.yaml) **2.0.0** — `/v1/sesiones`, `codigo_canje` en `CambiarEstadoRequest` |
| **Pruebas** | [`test_panel_mostrador.py`](../backend/tests/test_panel_mostrador.py) (21) · [`test_autenticacion.py`](../backend/tests/test_autenticacion.py) (44) · [`test_cors.py`](../backend/tests/test_cors.py) (6) |

### 1.1 El rechazo del 100 % no necesitó código propio

ESC-04 exige rechazar **todas** las reutilizaciones. No hay ninguna línea que lo
haga: sale de que `entregado` sea un estado final, así que el segundo intento
falla por la transición antes de llegar a comparar el código.

Aun así hay una prueba, `test_el_codigo_no_se_puede_reutilizar`. Lo que el
escenario promete es el **rechazo**, no el mecanismo, y si algún día `entregado`
dejara de ser final la promesa se rompería sin que nadie tocara el código del
canje. Esa prueba es la que avisaría.

### 1.2 Lo que el panel dejó de mostrar

Hasta esta semana el panel pintaba el código junto al estado de cada pedido.
Eso **vacía ESC-04 de contenido**: si el código está en la pantalla del
mostrador, pedírselo al cliente es un trámite que se puede saltar leyendo la
propia lista.

Ahora no se muestra. Quien atiende tiene que pedirlo, y el servidor lo compara
con `compare_digest` —sin distinguir mayúsculas, porque se dicta en voz alta—.

### 1.3 Tres decisiones de código de estado, y su motivo

| Caso | Respuesta | Por qué no la otra |
|---|---|---|
| Pedido de **otro establecimiento** | `404` | Un `403` confirma que existe, y con eso se enumeran los pedidos del campus probando identificadores |
| **Establecimiento** de otro | `403` | Aquí no hay nada que enumerar: los establecimientos son públicos, están en el menú. Y responder los propios en silencio sería peor que un error, porque es una respuesta correcta a otra pregunta |
| Contraseña **demasiado corta** al ingresar | `401` | Un `422` le diría a quien prueba que acertó el formato y falló el valor. El mínimo se aplica al **crear** la cuenta, donde sí hay que explicarlo |

---

## 2. La corrección que destapó dos portones abiertos

Esta es la parte de la semana que menos se pidió y más vale.

### 2.1 Escribir la regla no la hace cierta

Cerrar V-10 rompe el contrato: pedir una credencial que antes no se pedía deja
fuera a todo cliente existente. Eso se añadió a
[`politica-versionado.md`](api/politica-versionado.md) como regla **I-12**.

Después se midió. El contrato 2.0.0 contra la 1.2.0 congelada, con nuestro
propio comparador:

```
1.2.0: 0 incompatibles
```

**Cero**, para el cambio más grande que este contrato ha tenido.
`comparar_contratos.py` revisaba rutas, esquemas, campos requeridos, tipos,
`enum` y códigos de respuesta, y **no miraba `security` en absoluto**. La regla
existía en un documento y en ningún otro sitio.

Tras implementarla:

```
1.2.0: 2 incompatibles
   - [INCOMPATIBLE] I-12 · GET /v1/pedidos
          pasa a exigir una credencial que antes no pedía (SesionDeMostrador)
   - [INCOMPATIBLE] I-12 · POST /v1/pedidos/{pedido_id}/estado
          pasa a exigir una credencial que antes no pedía (SesionDeMostrador)
```

### 2.2 El segundo portón, detrás del primero

`test_el_contrato_vigente_no_rompe_la_linea_base` comparaba siempre contra
`openapi-1.0.0.yaml` y se **omitía** cuando la MAYOR subía.

Los dos defectos juntos tienen una consecuencia peor que cada uno por separado:
el salto a 2.0.0 habría dejado la comparación de compatibilidad apagada **para
el resto del proyecto**, y la prueba habría seguido apareciendo como «omitida»,
que en un resumen de pytest se lee casi igual que «pasó».

La línea base la resuelve ahora `info.version` del propio contrato, en la prueba
y en el job de `oasdiff`. Un salto de MAYOR ya no apaga la comparación: la
**reapunta**, y falla si falta congelar la base nueva.

### 2.3 La simetría que faltaba

Una regla de compatibilidad sirve para dos cosas simétricas: impedir que se
rompa sin avisar, e impedir que se avise sin romper.
`test_el_salto_de_mayor_esta_justificado_por_una_rotura_real` exige que un
2.0.0 pueda **señalar** la rotura que lo justifica. Avisar sin romper parece
inofensivo y no lo es: anuncia trabajo a todos los consumidores, y si ese
trabajo no existe, la próxima vez que se anuncie nadie lo va a creer.

---

## 3. El secreto: retirado y acreditado

### 3.1 Retirado sin perder la lección

El valor que estuvo publicado seguía escrito en **cinco archivos vigentes**.
Está en el historial de git y de ahí no se puede quitar, pero repetirlo en el
código y los documentos actuales lo deja al alcance de un `grep` sin tener que
saber buscar.

La prueba que lo usaba se volvió **más fuerte** al perderlo. Antes comprobaba
que *ese* valor dejó de servir; ahora comprueba que una firma hecha con
cualquier cadena que no sea la configurada se rechaza — lo que cubre el caso
histórico y todos los demás, en vez de quedar especializada en el defecto de una
semana.

Y se añadió el guardia que faltaba:
`test_ningun_secreto_vuelve_a_tener_valor_por_defecto` persigue **la forma** del
defecto —un `os.getenv` de variable con pinta de credencial con valor por
defecto no vacío— y no el valor. Buscar el valor solo habría protegido contra
repetir aquel error exacto; buscar la forma protege contra el error. Su mensaje
de fallo imprime la **longitud** del valor encontrado y no el valor: una prueba
que lo filtra al log del pipeline lo publica otra vez.

### 3.2 Acreditado contra el despliegue

Corregir el código es la mitad del trabajo. La otra es rotar lo expuesto y
comprobar que lo desplegado es lo corregido. Comprobado el **12/10/2026**:

| Qué | Cómo | Resultado |
|---|---|---|
| La variable existe en producción | API de Render, `GET /v1/services/srv-dasroip7lnhs73ahd4c0/env-vars` | `PIDEUTB_SECRETO_PASARELA` presente, **43 caracteres** |
| Es un valor rotado | Longitud frente a la del histórico | Distinta. 43 es lo que devuelve `secrets.token_urlsafe(32)`: entropía generada, no una palabra |
| El despliegue vivo tiene la corrección | `git merge-base --is-ancestor ad0b9b1 7e973faf` | Cierto |
| Qué commit sirve | API de Render, `GET .../deploys` | `7e973faf`, `live`, 2026-10-04T17:48:39Z |
| Los servicios responden | `GET /health`, `GET /panel.html` | `200` los dos |

**El valor del secreto no se leyó, solo su longitud.** Una acreditación que para
demostrar la rotación tuviera que mirar el secreto lo deja en el historial de la
sesión que la escribió, y entonces la acreditación es la nueva fuga.

La tabla completa está en [V-11](violaciones.md#v-11).

---

## 4. La documentación decía cosas falsas

### 4.1 Supabase no autentica

El C4 de niveles 1 y 2 y el arc42 §3.1 y §4.1 decían que **Supabase provee la
autenticación**. No la provee: de Supabase se usa únicamente el PostgreSQL
gestionado, y Supabase Auth nunca estuvo integrado.

Es el error más incómodo que puede tener un diagrama de arquitectura, porque
**describía una protección que no existía**. Quien leyera el nivel 2 concluiría
que el acceso estaba resuelto por el proveedor, y por eso no iría a comprobar si
lo estaba. Durante tres entregas el panel no exigió nada mientras el diagrama
afirmaba que la identidad se validaba contra Supabase.

La flecha 3 ahora dice «incluidas credenciales y sesiones», que no es cosmético:
significa que si Supabase no responde, **tampoco se puede iniciar sesión**.

Y la lección se generaliza: un diagrama que nombra una capacidad de un servicio
externo está afirmando que esa capacidad **se usa**. Es tan verificable como una
cita con número de línea, y conviene tratarlo igual.

### 4.2 Tres filas decían «pendiente» de cosas hechas

`arc42 §4.4` daba por pendientes ESC-03, ESC-04 y ESC-05 — implementados en S9,
S10 y **S7**. Una tabla de estado que nadie vuelve a tocar no se queda neutral:
afirma que falta algo que está hecho, y hace dudar del resto del documento.

Al revisarla apareció lo de §5.

---

## 5. ESC-03 medido por capas, y lo que la cifra única tapaba

La primera medición daba **0,20 s** sobre un presupuesto de 10 s, con una nota
al pie diciendo que no incluía red ni tiempo humano. La nota era cierta y aun
así el resultado engañaba: un ✅ junto a un umbral se lee como «el escenario se
cumple», y lo medido era una fracción del escenario.

| Capa | Qué mide | Resultado |
|---|---|---|
| 1 | El trabajo del servidor, en local | **0,20 s** |
| 2 | Lo mismo por la red, contra el servicio desplegado **caliente** | **~0,7 s** (219,7 ms de p50 por petición × 3) |
| 3 | Lo mismo con el servicio **frío** | **~43 s** ❌ |
| 4 | La persona | No medida. Quedan ~9,3 s de los 10 en caliente |

**Con el servicio frío, ESC-03 no se cumple.** El arranque en frío de Render
está medido en 42,4 s ([`comparacion-despliegue.md`](comparacion-despliegue.md)
§10) y el presupuesto de ESC-03 es de 10.

No es un caso raro, es *el* caso: el patrón de tráfico documentado son dos picos
de almuerzo con el resto del día casi vacío, así que el mostrador que abre el
panel al empezar el turno es, por construcción, el que se come el arranque.

**Los dos números llevaban semanas en el repositorio**, en documentos distintos.
Esto ya estaba escrito para ESC-02, cuyo presupuesto de 120 s absorbe los 42,4 s
«comiéndose un tercio». Nadie lo había trasladado a ESC-03, que tiene un
presupuesto doce veces menor y por tanto no lo absorbe. La causa de no verlo no
fue falta de datos: fue que una medición de una sola capa no obligaba a ponerlos
juntos.

Qué lo resolvería, sin inventar: Render Starter, $7/mes. Está evaluado y
descartado en [ADR-0004](adr/0004-plataforma-de-despliegue.md) por la condición
de presupuesto $0, y la comparación ya decía que si el presupuesto cambiara esa
sería la elección. Lo que cambia hoy es que **ESC-03 pasa a ser otro argumento
para ese cambio**, y no solo ESC-02.

Detalle completo: [`evidencia-s9.md` §1.3](evidencia-s9.md).

---

## 6. Tres defectos que solo vio un navegador

Con 250 pruebas en verde y 96 % de cobertura, el panel estaba **roto**.

### 6.1 CORS no permitía `Authorization` ni `DELETE`

Toda petición autenticada fallaba en el *preflight* del navegador, y lo que se
veía era un genérico «Failed to fetch» que no menciona CORS por ninguna parte.

**Por qué no lo vio nada.** `TestClient` no hace preflight: habla con la
aplicación por ASGI, sin navegador y sin política de mismo origen. Es un punto
ciego con una forma reconocible: **la prueba y el usuario no usan el mismo
camino**.

`test_cors.py` lo convierte en algo que la construcción detecta, usando lo único
que `TestClient` sí hace llegar al middleware: una petición `OPTIONS` con las
cabeceras de preflight escritas a mano. Comprueba las dos mitades — que permite
lo que el panel necesita y que **niega** un origen cualquiera —, porque una
configuración de CORS solo está bien si hace las dos cosas.

### 6.2 El aviso de código incorrecto se borraba solo

El manejador escribía el mensaje y refrescaba la cola para mostrar la realidad.
El refresco funcionaba, así que limpiaba el error. Quien atiende tecleaba un
código equivocado y **la pantalla se quedaba igual**, que es peor que un error
visible: parece que el clic no se registró.

### 6.3 El botón «Entregado» quedaba gris para siempre

Se desactiva antes de llamar y se vuelve a crear al repintar. Pero tras un
código incorrecto la cola no ha cambiado, así que `pintar` cortaba por la huella
y el botón no se recreaba. La única salida era recargar la página en mitad de la
entrega.

### 6.4 Y uno de cascada

El bloque móvil del formulario de ingreso estaba **antes** de las reglas que
sobreescribe. Misma especificidad, gana la última, así que el formulario seguía
en fila a 375 px aunque la consulta de medios coincidiera. Una media query no
sube la especificidad; solo decide si la regla participa.

### 6.5 Lo verificado en el navegador

Contra la API local y un PostgreSQL 18 real:

| Qué | Resultado |
|---|---|
| Credencial incorrecta | «Correo o contraseña incorrectos», el mismo mensaje que daría un correo desconocido |
| Recorrido completo del mostrador | `pagado` → `en_preparacion` → `listo_para_recoger` → `entregado` |
| Código equivocado | Rechazado, el pedido **no se movió**, el aviso visible y el botón activo |
| Código correcto en minúsculas y con espacios | Aceptado |
| «Salir» | Token inservible **también del lado del servidor**: `401` al reusarlo con `curl` |
| Ancho de móvil (375 px) | Formulario apilado, botón a ancho completo |

---

## 7. Las pruebas, y una que faltaba por completo

```
256 passed, 1 skipped — 96 % de cobertura (con PostgreSQL disponible)
210 passed, 49 skipped — sin PostgreSQL
```

### 7.1 Por qué la autenticación exige PostgreSQL

`usuarios.repository` **no tiene** implementación en memoria, y es deliberado:
una autenticación de juguete que funciona sin base de datos invita a desplegar
sin ella.

La contrapartida es que sin `PIDEUTB_DATABASE_URL_PRUEBAS` esos casos se omiten,
y una prueba omitida se lee casi igual que una que pasa. Dos defensas:
`test_la_autenticacion_se_probo_contra_postgres` **falla** si la variable está
puesta y aun así nada corrió, y el paso del pipeline que vigilaba esto ahora
cubre los **dos** archivos que dependen de PostgreSQL.

### 7.2 La cobertura encontró lo que el verde no mostraba

`usuarios/router.py` estaba al **65 %**: nada tocaba la frontera HTTP de las
sesiones. Las pruebas del recorrido completo lo llevan a 100 %, y por el camino
fijan tres cosas que solo se ven desde fuera: que los tres fallos de ingreso dan
el mismo `401` y el mismo mensaje, que la respuesta no publica la derivación de
la contraseña, y que una cabecera `Authorization` malformada es un `401` y no un
`422`.

### 7.3 Una rama inalcanzable, sin excluirla de la cobertura

El `403` por rol de `personal_de_establecimiento` no se puede alcanzar hoy:
los dos roles que existen pasan. En vez de marcarla como excluida, hay una
prueba que **recorre el enum entero**. Una exclusión dice «esto no se prueba» y
se queda ahí para siempre; la prueba dice «esto no se puede alcanzar **hoy**», y
falla el día que alguien añada un tercer rol sin decidir si puede operar el
panel.

### 7.4 El guion que nadie había ejecutado

`crear_usuario.py` imprimía `usuario.id` sobre un objeto cuyo campo se llama
`usuario_id`: **creaba la cuenta y después reventaba**. Quien lo ejecutara habría
visto un traceback, supuesto que falló, y al reintentar habría recibido «ya hay
una cuenta con ese correo» sin saber que la suya ya existía.

Ahora lo corren dos pruebas, una de ellas comprobando lo que **imprime**, porque
es la única confirmación que recibe quien lo usa.

---

## 8. Lo que queda abierto

| Qué | Dónde | Por qué no ahora |
|---|---|---|
| El token vive en `sessionStorage` | [V-12](violaciones.md#v-12) | Una cookie `HttpOnly` entre orígenes distintos exige `SameSite=None`, CORS con credenciales y defensa CSRF. Se eligió la opción que deja **menos cosas que mantener correctas**, y se escribieron las tres condiciones que invalidarían esa elección |
| Sin Content-Security-Policy | [V-12](violaciones.md#v-12) | Es la defensa en profundidad que corresponde ahí. Está sin hacer, y se dice en vez de omitirlo |
| Sin límite de intentos de ingreso | [ADR-0007](adr/0007-autenticacion-del-panel.md) | Los ~100 ms de scrypt hacen caro probar en masa, pero caro no es imposible. Resolverlo bien necesita almacenamiento compartido entre instancias: es una decisión aparte |
| Sin reseteo de contraseña | [ADR-0007](adr/0007-autenticacion-del-panel.md) | Necesita correo saliente, que es una dependencia externa nueva y entra en el presupuesto de ADR-0003 |
| ESC-03 incumplido en frío | §5 · [`aspectos.md`](aspectos.md) | Depende de un plan de pago. Documentado con su número y su causa |
| SonarCloud en modo automático | [`calidad-sonarcloud.md`](calidad-sonarcloud.md) | Cambiar de modo requiere tocar la configuración del proyecto en SonarCloud; queda documentado el estado actual y qué implicaría el cambio |

---

## 9. Despliegue: dos pasos manuales

**Fusionar no basta.** La API 2.0.0 necesita las tablas `usuarios` y `sesiones`,
que no existen todavía en el proyecto desplegado, y al menos una cuenta:

```bash
cd backend
python scripts/migrar.py --estado   # ver qué falta
python scripts/migrar.py            # aplicar 003_autenticacion.sql
python scripts/crear_usuario.py     # pide la contraseña sin eco
```

Ninguno se automatiza, y por el mismo motivo de fondo. Un proceso web que
modifica el esquema al arrancar lo hace en cada instancia a la vez y cuando
nadie mira; y sembrar usuarios en una migración exigiría una contraseña en el
repositorio, que es exactamente la forma de [V-11](violaciones.md#v-11).

El detalle está en [ADR-0007](adr/0007-autenticacion-del-panel.md).

---

## 10. Trazabilidad

| Elemento | Dónde |
|---|---|
| Decisión de autenticación | [ADR-0007](adr/0007-autenticacion-del-panel.md) |
| Violación cerrada | [V-10](violaciones.md#v-10) |
| Violación abierta | [V-12](violaciones.md#v-12) |
| Escenario cerrado | [ESC-04](arc42/arc42.md#esc-04) · fila en [`aspectos.md`](aspectos.md) |
| Regla de versionado nueva | **I-12** y **§5 bis** de [`politica-versionado.md`](api/politica-versionado.md) |
| Contrato | [`openapi.yaml`](api/openapi.yaml) 2.0.0 · congelado en `api/historial/openapi-2.0.0.yaml` |
| Expectativas del consumidor | [`consumidor-web.yaml`](../contracts/consumidor-web.yaml) |
| Medición de ESC-03 por capas | [`evidencia-s9.md` §1.3](evidencia-s9.md) |
| Arranque en frío medido | [`comparacion-despliegue.md`](comparacion-despliegue.md) §10 |
| Acreditación de la rotación | [V-11](violaciones.md#v-11) |
