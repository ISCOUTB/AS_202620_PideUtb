# ADR 0007: Autenticar el panel con sesiones propias en lugar de Supabase Auth

## Estado

Aceptada — 12/10/2026

## Contexto

Hasta la semana 10, el panel del mostrador no exigía nada. Cualquiera que
conociera la URL de la API podía pedir `GET /v1/pedidos?establecimiento_id=2` y
leer la cola de un establecimiento que no era el suyo, o avanzar sus pedidos.
Estaba registrado como [V-10](../violaciones.md#v-10) y declarado como deuda
abierta en [ADR-0005](0005-maquina-de-estados-del-mostrador.md), que lo dice sin
rodeos: «no hay autenticación; llega en una entrega posterior».

Dos cosas forzaron cerrarlo ahora y no más tarde:

- **[ESC-04](../arc42/arc42.md#esc-04)** —que el código de canje no se pueda
  reutilizar— no se puede cumplir sin saber *quién* entrega. Sin sesión, el
  endpoint que marca «entregado» lo puede llamar el propio estudiante.
- El diagrama C4 y el arc42 afirmaban que **Supabase proveía la
  autenticación**. No la proveía: el proyecto usa de Supabase únicamente el
  PostgreSQL gestionado. Era una afirmación falsa en la documentación de
  arquitectura, del tipo más incómodo, porque describía una protección que no
  existía.

## Decisión

**Sesiones propias**: credenciales en la tabla `usuarios`, sesiones en
`sesiones`, token opaco en la cabecera `Authorization: Bearer`. Nada de
Supabase Auth, nada de JWT firmados, nada de OAuth.

La implementación es `backend/app/usuarios/` más el módulo transversal
`backend/app/autenticacion.py`, y el esquema está en
`backend/migraciones/003_autenticacion.sql`.

### Por qué no Supabase Auth

Es la opción que la documentación ya daba por hecha, así que merece el
argumento completo y no una línea.

| | Supabase Auth | Sesiones propias |
|---|---|---|
| Esfuerzo inicial | Menor: el registro, el correo de verificación y el reseteo vienen hechos | Mayor: hay que escribir derivación, token y caducidad |
| Dependencias nuevas | El SDK de Supabase, o hablar su API REST | Ninguna: `hashlib.scrypt` y `secrets` son de la biblioteca estándar |
| Acoplamiento | La identidad vive en el proveedor. Cambiar de plataforma obliga a migrar cuentas | La identidad vive en nuestro PostgreSQL, que ya es portable |
| Qué se puede probar sin red | Casi nada: el mecanismo es un servicio externo | Todo: la derivación y la verificación son funciones puras |
| Modelo de roles | El suyo (`auth.users` + claims), traducido al nuestro | El nuestro, con la restricción de integridad que de verdad queremos |

Lo que decidió no fue el esfuerzo sino las dos últimas filas.

**El modelo de roles.** El sistema necesita que *el personal pertenezca a un
establecimiento y el administrador no pertenezca a ninguno*. Eso es una
invariante, y en una tabla propia se escribe como tal:

```sql
CONSTRAINT establecimiento_segun_rol CHECK (
    (rol = 'personal_establecimiento' AND establecimiento_id IS NOT NULL)
    OR (rol = 'administrador' AND establecimiento_id IS NULL)
)
```

Con Supabase Auth el rol sería un claim o una fila en una tabla de perfiles, y
esa invariante pasaría a ser código de aplicación que hay que acordarse de
ejecutar. Es exactamente la clase de regla que [ADR-0002](0002-propiedad-datos-establecimiento.md)
pone en la base de datos y no en el servicio: una comprobación que vive en un
solo sitio no se puede olvidar en el segundo.

**Lo que se puede probar.** Con el mecanismo adentro, la derivación y la
verificación son funciones que no tocan red ni disco, así que se prueban en
milisegundos y sin credenciales de nadie. Con un proveedor externo, probar el
inicio de sesión significa o hablar con él —y entonces las pruebas necesitan
secretos y conexión— o simularlo, y una simulación de autenticación prueba la
simulación.

### Por qué un token opaco y no un JWT

Un JWT se verifica sin consultar la base de datos, que es su única ventaja real,
y a cambio **no se puede revocar**: sigue siendo válido hasta que caduca, aunque
se cierre la sesión o se despida a quien lo tiene. Las soluciones habituales
—caducidad muy corta con refresco, o una lista de revocados— terminan
consultando el almacén en cada petición, que es justo lo que el JWT venía a
evitar.

Un token opaco contra la tabla `sesiones` cuesta una consulta por petición
—indexada por `token_hash`, en el mismo pool que ya se usa— y cerrar sesión es
un `DELETE` que surte efecto de inmediato. Para un panel de mostrador con
decenas de usuarios, esa consulta no es el problema; un turno que no se puede
cerrar sí lo sería.

### Decisiones de detalle, con su motivo

| Decisión | Motivo |
|---|---|
| `hashlib.scrypt`, N=2¹⁴, r=8, p=1 | De la biblioteca estándar: ninguna dependencia nueva. **Medido: mediana de 100 ms** por derivación (15 repeticiones en el portátil de desarrollo, mín. 99, máx. 116). Suficiente para que probar contraseñas en masa no escale, poco para que iniciar sesión se note. La cifra depende de la máquina, así que se guarda con el método y no sola |
| Se guarda el **hash** del token, no el token | Una filtración de la tabla `sesiones` no entrega sesiones usables. Es el mismo razonamiento que para las contraseñas, aplicado a algo que suele guardarse en claro |
| El mismo `401` para correo desconocido y contraseña incorrecta | Distinguirlos convierte el formulario en un oráculo de qué correos están registrados |
| Si el usuario no existe, se deriva igual contra un hash de descarte | Sin eso, un correo inexistente responde unos 100 ms antes, y esa diferencia es medible desde fuera incluso con red en medio. El mensaje idéntico no sirve de nada si el reloj habla |
| Un pedido de otro establecimiento responde `404`, no `403` | `403` confirma que existe, y con eso se enumeran los pedidos del campus probando identificadores |
| Pedir el **establecimiento** de otro sí responde `403` | Aquí no hay nada que enumerar: los establecimientos son públicos, están en el menú. Y responder los propios en silencio sería peor que un error, porque es una respuesta correcta a otra pregunta |
| `Authorization`, no cookie | El sitio es estático y vive en otro origen. Con cookies haría falta `SameSite=None`, CORS con credenciales y protección CSRF; con un token explícito no hay envío automático desde otro sitio y el CSRF deja de existir como clase de problema |
| Mínimo de 12 caracteres, y **no** declarado en el contrato | Una contraseña corta tiene que dar `401` como cualquier credencial equivocada. Un `422` le diría a quien prueba que acertó el formato y falló el valor |
| Sesión de 8 horas | Un turno de mostrador. Más corto interrumpe el trabajo; más largo deja sesiones abiertas de un día para otro en un equipo compartido |

## Consecuencias

### Lo que cierra

- **[V-10](../violaciones.md#v-10)**: el establecimiento sale de la sesión. El
  parámetro sigue existiendo para administradores y responde `403` a quien pida
  uno que no es el suyo.
- **[ESC-04](../arc42/arc42.md#esc-04)**: entregar exige presentar el código de
  canje. El rechazo del 100 % de las reutilizaciones no necesita código propio:
  sale de que `entregado` sea un estado final, así que el segundo intento falla
  por la transición antes de llegar al código.
- La afirmación falsa del C4 y del arc42, que ahora dicen lo que de verdad hace
  cada pieza.

### Lo que rompe

El contrato sube a **2.0.0**. Pedir una credencial que antes no se pedía rompe a
todo cliente existente: es la regla **I-12** de
[`politica-versionado.md`](../api/politica-versionado.md). El prefijo de ruta no
cambia a `/v2` porque §5 bis lo prohíbe cuando lo viejo **es** el defecto:
mantener `/v1` abierto 90 días mientras `/v2` exige sesión sería dejar la misma
puerta abierta tres meses más.

### Lo que deja abierto

- **[V-12](../violaciones.md#v-12)**: el token vive en `sessionStorage`, así que
  un fallo de XSS lo deja leer. Hoy el sitio no renderiza HTML de nadie —todo el
  texto entra por `textContent`— pero eso es una propiedad que hay que mantener,
  no una garantía del mecanismo.
- **No hay registro de usuarios por la API.** Las cuentas se crean con
  `crear_usuario()` desde la migración o un script. Un panel de mostrador tiene
  tantos usuarios como mostradores: un formulario público de registro sería una
  superficie de ataque a cambio de nada.
- **No hay reseteo de contraseña.** Necesita correo saliente, que es una
  dependencia externa nueva y entra en el presupuesto de
  [ADR-0003](0003-estrategia-integracion.md). Mientras no exista, la reposición
  es manual.
- **No hay límite de intentos.** Los ~100 ms de la derivación hacen que probar en
  masa sea caro, pero caro no es imposible. Queda anotado y no resuelto:
  resolverlo bien necesita almacenamiento compartido entre instancias, que es
  una decisión aparte.

## Qué cambiaría esta decisión

- **Que los usuarios dejen de ser decenas.** Si el sistema abre cuentas a
  estudiantes, aparecen el registro, la verificación de correo y el reseteo, y
  entonces lo que Supabase Auth trae hecho empieza a pesar más que el
  acoplamiento.
- **Que haga falta inicio de sesión institucional.** Si la universidad exige
  entrar con la cuenta de la UTB, esto se reemplaza por OIDC y la tabla
  `usuarios` se queda solo con los roles.
- **Que la consulta por petición se note.** No se nota hoy y se puede medir
  cuando se dude: `GET /metricas` publica el p95 por operación.

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Violación que cierra | [V-10](../violaciones.md#v-10) |
| Violación que abre | [V-12](../violaciones.md#v-12) |
| Escenario que habilita | [ESC-04](../arc42/arc42.md#esc-04) |
| Deuda que ADR-0005 dejó anotada | [ADR-0005](0005-maquina-de-estados-del-mostrador.md) |
| Regla de versionado aplicada | [I-12 y §5 bis](../api/politica-versionado.md) |
| Esquema | `backend/migraciones/003_autenticacion.sql` |
| Mecanismo | `backend/app/usuarios/credenciales.py`, `backend/app/autenticacion.py` |
| Contrato | [`openapi.yaml`](../api/openapi.yaml) · `/v1/sesiones` |
| Pruebas | `backend/tests/test_autenticacion.py`, `backend/tests/test_panel_mostrador.py` |
