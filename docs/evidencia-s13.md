# Evidencia S13 — Seguridad: seis preguntas a cada pieza

Fecha: **18/10/2026**.

Los entregables de la semana, y dónde está cada uno:

| Lo que se pide | Dónde |
|---|---|
| Modelado de amenazas (STRIDE) | [arc42 §8.7](arc42/arc42.md#amenazas) |
| Priorización de riesgos | [arc42 §8.7](arc42/arc42.md#amenazas) *(al final)* · [§11.1](arc42/arc42.md#riesgos) |
| Mitigaciones verificables | [arc42 §8.7](arc42/arc42.md#amenazas) — cada fila con la prueba que la verifica |
| Análisis de dependencias | Este documento §2 · job `dependencias` del pipeline |
| Privacidad y datos personales | [arc42 §8.8](arc42/arc42.md#datos-personales) |
| Gestión de secretos | [arc42 §8.9](arc42/arc42.md#secretos) |

---

## 1. Por qué STRIDE encontró algo y una lista de riesgos no lo habría hecho

Una lista contiene lo que se nos ocurrió. STRIDE obliga a hacer **seis preguntas
a cada elemento**, incluidas las que nadie habría escrito.

Salieron **18 amenazas**. Catorce ya tenían mitigación con una prueba que la
verifica — no porque se trabajara en seguridad esta semana, sino porque las
violaciones V-01 a V-12 de las semanas anteriores eran, casi todas, amenazas de
este modelo encontradas de una en una.

**Tres aparecieron por preguntar.** Son el resultado de la semana.

### El hallazgo: dos defensas correctas que se estorban

`POST /v1/sesiones` es la operación más lenta del sistema, y lo es **a
propósito**: deriva scrypt para que probar contraseñas en serie sea caro
([ADR-0007](adr/0007-autenticacion-del-panel.md)). Ese mismo ADR declara que
**no hay límite de intentos**, porque hacerlo bien exige almacenamiento
compartido entre instancias. Y [ADR-0008](adr/0008-despliegue-en-el-servidor-del-laboratorio.md)
fijó el contenedor en **0,5 CPU**.

Tres decisiones correctas por separado. Juntas:

```
500 ms de CPU por segundo de reloj
÷ 35 ms por derivación en producción
≈ 14 peticiones por segundo saturan el servicio
```

Catorce peticiones por segundo. Y lo que lo convierte de molestia en amenaza es
el detalle que ninguna de las tres anticipó: **el atacante no necesita una
cuenta.** La defensa contra ataques de tiempo deriva contra un hash de descarte
cuando el correo no existe, así que un correo inventado cuesta exactamente lo
mismo que uno real.

Dicho sin adornos: **para proteger los tiempos de respuesta se hizo que
cualquiera pueda obligar al servidor a trabajar.**

### Lo que hoy lo contiene es lo que la S11 anotó como un problema

Cloudflare rechaza con `403` a los clientes que identifica como automatismos. La
semana 11 lo documentó como el **fallo 9**, un obstáculo: si la pasarela usara un
agente filtrado, sus avisos de pago no llegarían nunca.

La semana 13 lo encuentra conteniendo su amenaza más grave. Un ataque con el
cliente HTTP por defecto de un guion no llega al servidor.

No cuenta como mitigación —no la controlamos, no la configuramos, y un
`User-Agent` de navegador la pasa— pero explica por qué el riesgo es real y no ha
ocurrido. Y es la clase de cosa que solo se ve mirando el mismo hecho desde dos
semanas distintas.

### Por qué no se corrige esta semana

Porque las dos correcciones posibles **apuntan en direcciones opuestas**:

| Opción | Mejora | Empeora |
|---|---|---|
| Límite de intentos por IP, en memoria del proceso | R-07 (el agotamiento) | Funciona hoy con una instancia y **deja de funcionar en silencio con dos** — el modo de fallo de R-03 |
| Subir el coste de scrypt | R-02 (la defensa débil) | **R-07**: cada petición cuesta más, así que hacen falta menos para saturar |

Elegir sin medir sería cambiar un problema por otro. Queda para la S14, que es
la semana de medir atributos de calidad contra su umbral.

### Las otras dos

**R-08 · nadie puede decir qué persona entregó un pedido.** `avanzar_estado`
recibe `establecimiento_id`, no el usuario: el sistema sabe *qué mostrador* movió
un pedido, no *quién*. Importa porque el `codigo_canje` da derecho a comida, y
la transición a `entregado` es cuando ese derecho se consume. Si un pedido
aparece entregado y el cliente dice que no lo recogió, hoy no hay nada que
mirar. No es explotable: es **no auditable**.

**R-09 · `GET /metricas` es público.** El inventario de operaciones ya es
público a propósito (`openapi.yaml`), pero el **volumen de tráfico** no lo era, y
es información del negocio. Cerrarlo tiene un coste concreto: es la fuente de
las mediciones de [§8.6](arc42/arc42.md#consistencia) y del seguimiento de
ESC-02, y hoy se consulta sin credenciales desde fuera.

### Y una fila que se escribió para decir «no hace falta»

La firma del webhook **no lleva marca de tiempo ni nonce**, así que un evento
válido capturado se puede repetir. No importa, y el motivo merece anotarse: lo
que hace inofensiva la repetición no es una defensa contra repetición, es la
idempotencia que se construyó en la S11 por otro motivo.

---

## 2. Dependencias: el hueco era que no había ninguna comprobación

El pipeline tenía fijado por hash y verificación de procedencia (S9), pero
**ninguna consulta de vulnerabilidades**. Se auditaron los 30 paquetes fijados
contra OSV:

```
pytest 8.4.2 → GHSA-6w46-j5rx-g56g / PYSEC-2026-1845
moderada · CVSS AV:L (vector local) · corregida en 9.0.3
```

Un hallazgo de 30. Pero lo importante no es la vulnerabilidad: es **dónde
estaba**.

### Ocho paquetes en producción que la aplicación no importa

La imagen instalaba `requirements-ci.txt`, que fija `pytest` y `httpx` porque la
suite los necesita. Así que producción llevaba dentro:

```
certifi  httpcore  httpx  iniconfig  packaging  pluggy  pygments  pytest
```

El vector de la vulnerabilidad es local y en un contenedor sin shell interactiva
el riesgo real era bajo. **La regla incumplida no**: en la imagen no debería
haber nada que la aplicación no use. Cada paquete de más es superficie que
vigilar y que algún día tendrá su propio aviso.

### Que fueran ocho y no otros se calculó, no se estimó

Con las anotaciones `# via` que `pip-compile` escribe en el propio lock: son los
**no alcanzables** desde `fastapi`, `uvicorn` ni `psycopg`. Cuatro candidatos se
quedaron porque producción sí los alcanza, y conviene nombrarlos para que nadie
los quite de más:

| Paquete | Lo necesita |
|---|---|
| `anyio` | starlette, watchfiles |
| `h11` | uvicorn |
| `idna` | anyio |
| `typing-extensions` | fastapi, pydantic |

`requirements-prod.txt` queda con **22 de 30**.

### Quién lo verifica, y por qué no soy yo

No hay Docker en la máquina de desarrollo (deuda D-01), así que **la imagen no se
puede construir en local para ver si le falta algo**. Aplicar esto a ciegas
repetiría el error de la S11: cinco defectos de configuración que 282 pruebas no
podían ver.

El job `dependencias` instala **solo** el lock de producción en Linux, importa
`app.main`, y comprueba por `importlib.metadata` que ninguno de los ocho quedó
dentro. Si alguno hiciera falta de verdad, falla ahí y no en el arranque del
contenedor.

**La auditoría de producción bloquea; la del instrumental de pruebas informa.**
La asimetría es deliberada: una vulnerabilidad en `pytest` no alcanza a ningún
usuario, y un pipeline que se pone rojo por algo que no pone en riesgo a nadie
acaba ignorado.

### La prueba que más vale es la inversa

`test_dependencias.py` vigila las dos direcciones. La interesante no es «que no
vuelva a entrar pytest» sino: **un `import httpx` en `app/` sería razonable de
escribir** —ya está en el entorno de desarrollo, y la suite pasaría en verde— y
reventaría con `ModuleNotFoundError` en el arranque del contenedor.

Es el fallo de la semana 8 con `psycopg`, en la dirección contraria. Los archivos
a comprobar se derivan de los `COPY` del propio Dockerfile, no de una lista
paralela que se desincronice en silencio.

Las cinco pruebas se comprobaron con su defecto inyectado antes de contarlas.

---

## 3. Privacidad: la minimización no hubo que implementarla

| Tabla | Dato personal |
|---|---|
| `usuarios` | `correo` del personal, en claro. Es el identificador de acceso |
| `usuarios` | Contraseña: **nunca**, solo su derivación scrypt con sal propia |
| `sesiones` | Token: **nunca**, solo su hash |
| `pedidos` | **Nada.** Ni nombre, ni teléfono, ni correo, ni identificador de dispositivo |

La última fila es la que importa. **Un cliente de PideUTB no es un registro: es
quien tiene un código de canje.** Pide sin cuenta, sin dejar datos, y el sistema
no puede relacionar dos de sus pedidos entre sí.

No se decidió como política de privacidad: salió del alcance del producto y de
[ADR-0002](adr/0002-propiedad-datos-establecimiento.md). Pero el efecto es que
**el dato que no se recoge no se puede filtrar, ni hay que borrarlo, ni hay que
explicar quién lo ve.**

La contrapartida, dicha: el `codigo_canje` es un **portador** —quien lo tenga
come— así que su manejo es el control relevante. Por eso se genera con `secrets`,
es único en la tabla, y se exige al entregar.

### Retención

Dos cosas viven para siempre: los pedidos y las sesiones ya caducadas. Las dos
son honestas y ninguna urgente, por el motivo de arriba: lo que se acumula no
contiene datos de clientes.

Una sesión caducada es un hash inútil, y `borrar_sesiones_caducadas()` **existe y
no la llama nadie** — su propio docstring lo dice, en vez de dar a entender que
alguien la ejecuta. Es higiene, no seguridad.

Los pedidos acumulados son el registro contable: borrarlos sería perder la
auditoría del dinero. Lo que falta no es borrado sino una política escrita de
cuánto conservar, y eso depende de un requisito que nadie ha dado.

---

## 4. Secretos: dos propiedades valen más que la lista

Hay cuatro secretos, ninguno en el repositorio, y eso lo comprueba una prueba en
cada push que **a su vez tiene su propia prueba** de que sabe detectar lo que
dice detectar. La historia está en [V-11](violaciones.md#v-11): el secreto de la
pasarela **estuvo** escrito en el código.

Lo que vale más que el inventario:

**Fallar en cerrado.** Sin `PIDEUTB_SECRETO_PASARELA` la API no verifica firmas
contra una cadena vacía: se niega a firmar. Un despliegue mal configurado **no
arranca aceptando cualquier evento**, que es el modo de fallo que convierte un
olvido en una brecha.

**Derivar y no cifrar.** Cifrar implica poder descifrar, y nadie necesita
recuperar una contraseña original: solo comprobar si la que llega produce la
misma derivación.

### Lo que falta son dos cosas que son la misma

**La contraseña inicial se queda en el panel.** Cumple su función una sola vez
—el primer arranque con la tabla vacía— y después sigue ahí, en claro, legible
para cualquiera que entre. El sembrado acota el daño (con la tabla poblada no
hace nada), pero una credencial válida y visible mucho después de usarse es una
credencial olvidada.

Lo correcto sería cambiarla y vaciar la variable. Y ahí aparece la otra:

**No hay forma de restablecer una contraseña.** Comprobado: no existe ruta en el
contrato ni guion que lo haga. `crear_usuario.py` crea cuentas y necesita acceso
a la base, que **el despliegue no concede** — la base no publica puertos y el
panel no da terminal.

Así que cambiar la contraseña inicial hoy **no se puede** sin recrear el
despliegue, y una contraseña perdida deja el panel inaccesible por el mismo
motivo. Son la misma carencia, y es la que hace que la primera no se pueda
arreglar.

---

## 5. Lo que esta semana deliberadamente no añadió

| Patrón | Por qué no |
|---|---|
| **Límite de intentos** | Es la corrección de R-07 y **empeora o mejora según el número**: en memoria funciona hoy y falla en silencio con dos procesos. Se mide en la S14 |
| **TLS entre la API y la base** | Dejó de cruzar la red con ADR-0008: es una red privada de contenedores sin puertos publicados |
| **Marca de tiempo en la firma del webhook** | La repetición ya es inofensiva por idempotencia. Añadirla obligaría a sincronizar relojes con un tercero |
| **Cifrado de las contraseñas** | Se derivan, que es más fuerte. Cifrar sería un retroceso disfrazado de mejora |
| **Roles más finos** | Los dos roles pueden lo mismo hoy, y está **declarado** con una prueba en vez de descubierto. Afinar sin un requisito sería inventarlo |

---

## 6. Verificación

```
322 passed, 62 skipped — sin PostgreSQL
```

De las nuevas: **5 funciones en `test_dependencias.py`**, que dan **43 casos**
— cuatro fijas y una parametrizada con los 39 archivos que el Dockerfile copia a
la imagen.

| Elemento | Dónde |
|---|---|
| Modelo STRIDE, 18 amenazas | [arc42 §8.7](arc42/arc42.md#amenazas) |
| Priorización | [arc42 §8.7](arc42/arc42.md#amenazas) · [§11.1](arc42/arc42.md#riesgos) — R-07 a R-10 |
| Datos personales y retención | [arc42 §8.8](arc42/arc42.md#datos-personales) |
| Secretos | [arc42 §8.9](arc42/arc42.md#secretos) |
| Lock de producción | `backend/requirements-prod.txt` |
| Auditoría y verificación en CI | `.github/workflows/ci.yml`, job `dependencias` |
| Deriva de dependencias, en local | `backend/tests/test_dependencias.py` |
