# Evidencia S9 — Generación verificada y trazable

Fecha: **04/10/2026**.

Todo lo que aparece aquí se comprobó ejecutando algo: el código, la suite, una
API externa o un navegador. Cada bloque trae el comando o el archivo que lo
reproduce.

---

## 1. La cadena completa de una porción construida con IA

**La porción:** el **panel del mostrador**. Se construyó entero con apoyo de IA
en la semana 8 —backend, contrato y frontend— y cierra
[ESC-03](arc42/arc42.md#esc-03), que llevaba marcado como pendiente desde la
semana 5.

| Eslabón | Dónde |
|---|---|
| **Aspecto** | Fila de ESC-03 en [`aspectos.md`](aspectos.md): *Usabilidad · Rendimiento* |
| **Escenario** | [ESC-03](arc42/arc42.md#esc-03) — ≤ 10 s y ≤ 3 interacciones, sin recargar |
| **Decisión propia** | [ADR-0005](adr/0005-maquina-de-estados-del-mostrador.md) |
| **Código** | `app/pedidos/service.py` (`TRANSICIONES_DEL_MOSTRADOR`, `avanzar_estado`) · `app/pedidos/router.py` · `sitio/panel.html`, `sitio/panel.js` |
| **Contrato** | [`openapi.yaml`](api/openapi.yaml) — `GET /v1/pedidos`, `POST /v1/pedidos/{pedido_id}/estado` |
| **Pruebas** | [`test_panel_mostrador.py`](../backend/tests/test_panel_mostrador.py) — 15 casos |
| **Medición** | §1.3 de este documento |

### 1.1 La decisión fue del equipo, no de la herramienta

ADR-0005 descarta dos alternativas que la IA propuso antes:

- **Validar con condicionales en el servicio.** Descartada: una regla repartida
  en ramas de control se amplía sin que nadie lo note, porque añadir un `elif`
  no parece un cambio de política.
- **Permitir cualquier transición y auditar.** Descartada: sin autenticación,
  «permitir y auditar» significa permitir.

**Lo que decide el ADR no es lo que la tabla permite, es lo que deja fuera.**
`pendiente_pago` no es origen de ninguna transición: el mostrador **no puede
marcar un pedido como pagado**. Sin esa exclusión, cualquiera con un navegador
comería gratis, porque todavía no hay autenticación ([V-10](violaciones.md#v-10)).

### 1.2 La prueba que falla ante el defecto que cubre

```
backend/tests/test_panel_mostrador.py::test_el_mostrador_no_puede_marcar_un_pedido_como_pagado
```

Pide `estado: "pagado"` sobre un pedido sin pagar y exige `422`, además de
comprobar que el estado real **no cambió**. Si alguien añadiera `pagado` a
`EstadoSolicitable` «para poder corregir errores», esta prueba falla.

La acompaña `test_el_enum_de_peticion_coincide_con_la_maquina_de_estados`, que
impide que las dos declaraciones de la regla —el contrato y el servicio— se
separen en silencio.

### 1.3 Medición de ESC-03

> **Corregida en S10.** La primera versión de esta sección daba una sola cifra
> —0,20 s— con una nota al pie diciendo que no incluía red ni tiempo humano. La
> nota era cierta y aun así el resultado engañaba, porque un ✅ junto a un
> umbral de 10 s se lee como «el escenario se cumple», y lo que estaba medido
> era una fracción del escenario. Al separar las capas apareció algo que la
> cifra única tapaba por completo, y está en la capa 3.

ESC-03 mide **un flujo con una persona delante, a través de la red, contra el
servicio desplegado**. Nada de eso se puede medir de una vez, así que se mide
por capas y se dice cuál es cuál.

#### Capa 1 — El trabajo del servidor, en local

Tres pedidos llevados de `pagado` a `entregado` con el cliente de pruebas,
cronometrando desde la primera llamada hasta que el estado final está escrito:

| Pedido | Interacciones | Tiempo | Sin recargar |
|---|---|---|---|
| #1 | 3 | 0,20 s | sí |
| #2 | 3 | 0,20 s | sí |
| #3 | 3 | 0,20 s | sí |

Clics programáticos, API local, base de datos en memoria. **Mide el coste
algorítmico y nada más**: las tres transiciones de la máquina de estados, la
validación y el renderizado de la cola.

#### Capa 2 — La misma cosa, a través de la red, contra el servicio desplegado

Medido el **2026-10-12** desde una conexión doméstica contra
`pideutb-api.onrender.com` con el servicio **ya caliente**, 12 repeticiones por
ruta:

| Operación | p50 | mín. | máx. |
|---|---|---|---|
| `GET /v1/pedidos` | **219,7 ms** | 190,1 ms | 448,2 ms |
| `GET /v1/menu/establecimientos/1/items` | 222,0 ms | 202,3 ms | 441,0 ms |

El servidor reporta su propia parte en `GET /metricas`: **p95 de 32,75 ms** para
`GET /health` sobre 122 muestras de producción. La diferencia —unos 190 ms— es
red, TLS y el salto de Render a Supabase. Es decir: **de los 220 ms de una
petición, el código aporta el 15 %**.

Las tres interacciones de ESC-03 son tres peticiones, así que el flujo completo
en caliente cuesta del orden de **0,7 s**, contra los 0,20 s de la capa 1. Sigue
muy por debajo de 10 s.

Dos honestidades sobre esta capa:

- Se midieron **lecturas**, no los dos `POST` que avanzan el estado. No se
  escribió contra producción a propósito: habría dejado pedidos movidos en un
  servicio en marcha para obtener una cifra que no iba a ser distinta, porque
  el término dominante es la red y no el trabajo del servidor.
- El servicio desplegado está en el commit `7e973faf`, **anterior** a la
  autenticación. Esta medición no incluye, por tanto, la consulta de sesión que
  la 2.0.0 añade a cada petición: una búsqueda indexada por `token_hash` en el
  pool que ya está abierto. Es trabajo del servidor, que es el 15 % del total.

#### Capa 3 — Y aquí está lo que la cifra única tapaba

**Con el servicio frío, ESC-03 no se cumple.** El plan gratuito de Render
suspende el servicio tras unos minutos sin tráfico, y el arranque en frío está
medido en [`comparacion-despliegue.md`](comparacion-despliegue.md) §10: **42,4
segundos**. El presupuesto de ESC-03 es de 10.

No es un caso raro, es *el* caso: el patrón de tráfico documentado son dos picos
de almuerzo con el resto del día casi vacío
([`comparacion-despliegue.md`](comparacion-despliegue.md) §1). El mostrador que
abre el panel al empezar el turno es, por construcción, el que se come el
arranque.

| Umbral de ESC-03 | Caliente | Frío |
|---|---|---|
| ≤ 3 interacciones | **3** ✅ | 3 ✅ |
| ≤ 10 s | **~0,7 s** ✅ | **~43 s** ❌ |
| Sin recargar la página | sí ✅ | sí ✅ |

Esto ya estaba escrito para ESC-02, cuyo presupuesto de 120 s absorbe los 42,4 s
«comiéndose un tercio». Nadie lo había trasladado a ESC-03, que tiene un
presupuesto doce veces menor y por tanto **no lo absorbe**. La causa de no verlo
no fue falta de datos: los dos números estaban en el repositorio, en documentos
distintos, y la medición de una sola capa no obligaba a ponerlos juntos.

**Qué lo resolvería**, sin inventar: Render Starter, $7/mes, que elimina el
arranque en frío. Está evaluado y descartado en
[ADR-0004](adr/0004-plataforma-de-despliegue.md) por la condición operativa de
presupuesto $0, y la comparación dice textualmente que si el presupuesto
cambiara, esa sería la elección. Lo que cambia hoy es que **ESC-03 pasa a ser
otro argumento para ese cambio**, y no solo ESC-02.

#### Capa 4 — La persona

No medida. Hace falta alguien operando un mostrador real, y no lo hay. Lo que sí
se puede decir es cuánto presupuesto le queda: con el servicio caliente, **unos
9,3 s de los 10** quedan para las decisiones de quien atiende. Con el servicio
frío no le queda nada, porque ya se pasó.

---

## 2. Auditoría de erosión

### 2.1 El cruce de frontera

`app/salud.py`, **generado con IA en la semana 8**, importaba
`app.menu.repository`: el repositorio de otro contexto, saltándose su servicio.
Viola [ADR-0001](adr/0001-estilo-arquitectonico.md).

**Cómo se detectó.** Revisión manual de los imports del árbol, **no** por la
auditoría automática. Y ahí está lo interesante:

```python
def _modulo_de(archivo):
    relativa = archivo.relative_to(APP)
    if len(relativa.parts) < 2:
        return None          # ← los archivos sueltos en app/ se saltaban
```

`test_modularidad.py` solo auditaba archivos dentro de `app/<contexto>/`. Los
**seis** archivos sueltos en `app/` —`salud.py`, `observabilidad.py`,
`base_de_datos.py`, `main.py`, `eventos.py`, `esquemas_comunes.py`— nunca se
revisaban.

La regla estaba automatizada desde la semana 6 ([V-04](violaciones.md)). **La
generación entró por el único sitio que el detector no mira**, y la construcción
siguió en verde una entrega entera.

**Cómo se corrigió.** Dos cosas, porque arreglar solo la primera dejaría el
agujero:

1. `salud.py` llama ahora a `catalogo_service.listar_items_de_establecimiento`.
2. `_modulo_de` devuelve `TRANSVERSAL` para los archivos sueltos, que **sí se
   auditan**.

**Lo que apareció al ampliar la auditoría.** Saltó `main.py` importando los
routers de cada contexto. No se ensanchó la regla para que pasara —eso habría
sido el antipatrón— sino que se hizo una excepción acotada a la raíz de
composición, con `test_la_excepcion_de_la_raiz_de_composicion_no_se_extiende`
verificando que no alcanza a ningún otro archivo.

**Verificado que las pruebas fallan cuando deben.** Restaurando temporalmente el
punto ciego:

```
FAILED test_la_auditoria_ve_los_archivos_sueltos_en_app
FAILED test_la_excepcion_de_la_raiz_de_composicion_no_se_extiende
2 failed, 2 passed
```

### 2.2 Propiedad de datos: sin hallazgos

Se revisó si la generación cruzó alguna regla de dueño único de la semana 6. No.
Los cuatro `repository.py` siguen siendo los únicos escritores de sus tablas, y
`pagos` sigue **solicitando** a `pedidos` la transición de pago en vez de
ejecutarla ([ADR-0002](adr/0002-propiedad-datos-establecimiento.md)).

La migración a PostgreSQL de la semana 8 lo reforzó sin querer: las claves
foráneas del esquema hacen explícito en el motor qué contexto referencia a cuál.

---

## 3. Verificación de lo que el modelo trajo consigo

### 3.1 Dependencias propuestas

La comprobación no es «¿se instala?» —un paquete suplantado también se
instala— sino **«¿es el proyecto que dice ser?»**. Se contrastó cada dependencia
directa contra la API de PyPI, comparando el repositorio declarado con el
oficial:

| Paquete | Repositorio declarado | Veredicto |
|---|---|---|
| `fastapi` | `github.com/fastapi/fastapi` | ✅ |
| `httpx` | `github.com/encode/httpx` | ✅ |
| `pytest` | `github.com/pytest-dev/pytest` | ✅ |
| `psycopg` | `github.com/psycopg/psycopg` | ✅ |
| `uvicorn` | `github.com/Kludex/uvicorn` | ⚠️ **Marcado · revisado · legítimo** |

**El caso de `uvicorn` es el que vale la pena contar.** La comprobación esperaba
`encode/uvicorn` y encontró `Kludex/uvicorn`. El proyecto **se mudó**: 204
versiones publicadas desde la 0.0.1, mantenedor conocido, documentación en el
dominio oficial.

Es un falso positivo, y es exactamente lo que una comprobación así debe
producir de vez en cuando: **señaló un cambio real que una persona tuvo que
adjudicar**. Una verificación que nunca marca nada no está verificando.

Se comprobó además que no exista ningún nombre confundible registrado:

| Nombre | En PyPI |
|---|---|
| `uvicorns`, `uvicorn-standard`, `uvicom` | No existen |

Reproducible con la API pública de PyPI:

```bash
curl -s https://pypi.org/pypi/uvicorn/json | python -c "import sys,json; print(json.load(sys.stdin)['info']['project_urls'])"
```

### 3.2 Credenciales — un hallazgo serio

**El repositorio es público**, así que esto importa más que en un repositorio
privado.

**Archivos versionados: ninguna credencial.** Solo
`infra/terraform.tfvars.example` con marcadores. El `terraform.tfvars` real está
ignorado.

**Pero había un secreto en el código**, y estaba en uso:

`app/pagos/service.py` llamaba a `os.getenv("PIDEUTB_SECRETO_PASARELA", ...)`
con un **valor por defecto**, para que el repositorio fuera ejecutable sin
credenciales. El valor concreto no se reproduce en este documento: sigue en el
historial de git, de donde no se puede quitar, pero repetirlo en los archivos
vigentes lo deja al alcance de un `grep` y no aporta nada al relato.

La consulta a la API de Render confirmó que **la variable real nunca se
definió**: el servicio solo tenía `PIDEUTB_DATABASE_URL` y
`PIDEUTB_ORIGENES_PERMITIDOS`. La API en producción verificaba las firmas del
webhook contra una cadena publicada en GitHub.

**Consecuencia:** cualquiera que leyera el repositorio podía firmar un aviso de
pago válido y obtener un código de canje sin pagar.

No se explotó contra producción. La deducción es concluyente sin hacerlo —el
código lee el valor por defecto, la variable no existe— y explotarlo habría
dejado un pedido falso en el sistema sin añadir certeza.

**Corregido fallando en cerrado.** Sin la variable, `firma_valida` rechaza todo
evento. Un sistema sin su secreto deja de aceptar pagos: molesto y visible. Con
un secreto público aceptaba pagos falsos: peor y silencioso. Registrado como
[V-11](violaciones.md).

Siete pruebas en [`test_secreto_pasarela.py`](../backend/tests/test_secreto_pasarela.py),
incluida `test_el_secreto_no_aparece_en_el_codigo_fuente`, que impide que vuelva
a entrar uno. En la semana 10 se le sumó
`test_ningun_secreto_vuelve_a_tener_valor_por_defecto`, que persigue la **forma**
del defecto y no su valor, con su propio caso negativo.

**La corrección quedó acreditada contra el despliegue.** Quitar el valor por
defecto no cierra V-11 por sí solo: mientras el secreto no se rotara y el
servicio vivo no corriera la versión que falla en cerrado, la puerta seguía
abierta. La comprobación —variable presente, longitud de valor rotado, commit
`7e973faf` vivo con `ad0b9b1` como ancestro— está en la tabla de acreditación de
[V-11](violaciones.md#v-11).

### 3.3 Que las pruebas fallen de verdad

El enunciado lo pide, y se comprobó donde importaba:

| Prueba | Cómo se verificó |
|---|---|
| `test_una_firma_hecha_con_otro_secreto_no_sirve` | Firma un evento con una cadena que no es la configurada y exige `401` |
| Las dos de `test_modularidad.py` | Restaurando el punto ciego: **fallan** |
| `test_el_mostrador_no_puede_marcar_un_pedido_como_pagado` | Pide la transición prohibida y exige `422` |

---

## 4. El componente generativo: evaluado, no incorporado

[ADR-0006](adr/0006-componente-generativo.md), con el cálculo completo. Resumen:

| | |
|---|---|
| **Candidato evaluado** | Búsqueda en lenguaje natural sobre la carta |
| **Proveedor y tarifa** | Claude Haiku 4.5 — 1 USD/MTok entrada, 5 USD/MTok salida (<https://claude.com/pricing>, 04/10/2026) |
| **Costo por operación** | 0,000415 USD · **≈ 2,50 USD/mes** con 200 pedidos/día |
| **Latencia estimada** | 1–3 s · una llamada de 2 s consume el **1,7 %** del presupuesto de ESC-02 |
| **Decisión** | **No se incorpora** |

**El motivo de más peso no es el dinero.** Es que existe la alternativa
determinista y es mejor: con 4 ítems, un filtro por precio y etiquetas da el
mismo resultado en milisegundos, gratis, sin alucinar y sin caerse.

**El candidato más tentador se rechazó por seguridad.** Generar descripciones de
los ítems —con alérgenos— es el caso de uso que primero se le ocurre a
cualquiera, y alucinar u omitir un alérgeno es un riesgo de salud.

El ADR deja escrito **qué cambiaría la decisión** y, por si se incorpora algún
día, su conjunto de evaluación con umbrales y el comportamiento ante fallo del
proveedor: caer al filtro determinista con tope de 2 s, nunca mostrar un error.

---

## 5. Hallazgo adicional: una métrica que no se medía

No estaba en el guion de la semana y apareció tirando del hilo de un «0.0 %
Coverage on New Code» en un comentario automático, en vez de aceptar el verde.

**La cobertura nunca se había medido.** Ni una vez, en tres entregas.

| Check | Qué hacía |
|---|---|
| `SonarCloud` *(del workflow)* | **Se omite**: falta `SONAR_TOKEN`, y el workflow decide no fallar por ello. Termina en verde sin hacer nada |
| `SonarCloud Code Analysis` *(automático)* | Es el que analiza. **No ejecuta las pruebas**, así que no puede ingerir cobertura |

Confirmado contra la API de SonarCloud: las métricas `coverage`,
`lines_to_cover` y `tests` no tenían dato en ninguna rama. Y el README publicaba
una insignia que renderizaba literalmente **«Measure has not been found»**.

**Corregido sin tocar la configuración de SonarCloud** —esa decisión quedó
pendiente de consulta docente—: la cobertura se mide en el job `pruebas` con
`--cov-fail-under=85`, y la insignia rota se retiró.

| | |
|---|---|
| Cobertura en CI | **95,72 %** |
| Cobertura en local | 87,71 % *(sin PostgreSQL, las ramas de los `repository.py` no se ejecutan)* |
| Umbral exigido | 85 % — la construcción **falla** por debajo |

---

## 6. Lo que queda abierto

| # | Qué | Por qué sigue abierto |
|---|---|---|
| **V-10** | El panel del mostrador no está autenticado | Espera sesiones y roles. Acotado por diseño: no puede marcar como pagado, ni revertir un pago, ni saltarse estados. El panel lo avisa en su propia pantalla |
| **ESC-04** | Falta validar el código de canje en el punto de entrega | Depende de la autenticación |
| **SonarCloud** | La cobertura no entra en el Quality Gate | Exige apagar el análisis automático; pendiente de consulta docente |
| **Cobertura de rama** | Se mide cobertura de **sentencia**, no de rama | Un `if` probado solo por su lado verdadero cuenta como cubierto. Endurecerlo con `--cov-branch` bajaría el porcentaje; no se activó para no cambiar dos cosas a la vez |

---

## 7. Trazabilidad

| Elemento | Dónde |
|---|---|
| Cadena completa de ESC-03 | [`aspectos.md`](aspectos.md) · [ADR-0005](adr/0005-maquina-de-estados-del-mostrador.md) · [`test_panel_mostrador.py`](../backend/tests/test_panel_mostrador.py) |
| Registro de uso de IA | [`docs/ia.md`](ia.md) §S9 |
| Auditoría de modularidad | [`test_modularidad.py`](../backend/tests/test_modularidad.py) |
| El secreto y su corrección | [`test_secreto_pasarela.py`](../backend/tests/test_secreto_pasarela.py) · [V-11](violaciones.md) |
| Componente generativo | [ADR-0006](adr/0006-componente-generativo.md) |
| Cobertura | [`calidad-sonarcloud.md`](calidad-sonarcloud.md) §4 |
| Arranque en frío medido | [`comparacion-despliegue.md`](comparacion-despliegue.md) §10 |
