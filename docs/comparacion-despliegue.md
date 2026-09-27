# Comparación de alternativas de despliegue — la API

> Entrega calificada de la semana 8. Compara dos alternativas de despliegue
> para **una pieza concreta y nombrada** del sistema, a partir de la condición
> operativa, no para el sistema entero.

---

## 1. La condición operativa

El sistema no se despliega en abstracto. Estas son las condiciones bajo las que
el equipo opera, y cada una descarta opciones:

| Condición | Valor | Qué descarta |
|---|---|---|
| **Presupuesto** | $0. Proyecto académico sin financiación | Cualquier servicio sin capa gratuita real |
| **Motor de base de datos** | **PostgreSQL** | Ver §1.1 |
| **Servidor del laboratorio** | **No disponible** — no ofrece nada | La opción «servidor propio» del enunciado |
| **Patrón de tráfico** | Dos picos de almuerzo (~11:30–13:30), resto del día casi nulo | Hace que el arranque en frío importe |
| **Equipo** | Tres estudiantes, sin turnos de guardia | Cualquier cosa que exija operación manual |
| **Infraestructura** | Todo lo posible gestionado con Terraform | Plataformas sin provider |

### 1.1 PostgreSQL y no MySQL

La decisión no es «porque Supabase lo usa». El código ya asume cosas que
Postgres hace mejor:

1. **`EstadoPedido` es un conjunto cerrado de seis valores**
   ([V-08](violaciones.md#v-08), cerrada en S7). Postgres tiene tipos `ENUM`
   nativos con integridad garantizada por el motor; el `ENUM` de MySQL es una
   cadena con validación débil y comportamiento sorprendente al reordenar.
2. **La idempotencia de `confirmar_pago` exige escritura condicional atómica.**
   [ADR-0003](adr/0003-estrategia-integracion.md) promete que un reintento de
   la pasarela no genera un segundo código de canje. Eso es
   `INSERT … ON CONFLICT DO NOTHING`, una primitiva del lenguaje en Postgres.
   En MySQL hay que usar `INSERT IGNORE`, que **silencia también errores que no
   son duplicados**.
3. **El dinero son enteros en centavos** ([V-07](violaciones.md#v-07)). Postgres
   da restricciones `CHECK` declarativas para `total_centavos >= 0`.

**Alternativa descartada: MySQL.** Motivo: nuestra garantía de idempotencia se
expresa peor y de forma menos segura.

---

## 2. La pieza comparada: **la API**

De las cinco piezas que admite el enunciado —sitio, API, base de datos,
ficheros, trabajos programados— se compara **la API**, por tres razones:

- Es la única con **código real y escenarios de calidad medibles** asociados.
- Es la pieza cuyo modo de ejecución (contenedor o función) está genuinamente
  abierto: el sitio es estático por naturaleza y la base de datos es un servicio
  gestionado en cualquier escenario.
- Es donde el sistema tiene **estado en proceso**, que es lo que la clase
  identifica como el descalificador de las funciones.

El sistema **no tiene ficheros ni trabajos programados** en el dominio: no se
sube nada y no hay procesos periódicos de negocio. No es una carencia, es una
propiedad del problema, y por eso no se comparan.

### El escenario de calidad que decide

| Escenario | Umbral | Por qué es el relevante |
|---|---|---|
| [**ESC-04**](arc42/arc42.md#esc-04) | Validación en **< 2 s** | Es el umbral de latencia más exigente del sistema |
| [**ESC-02**](arc42/arc42.md#esc-02) | **< 2 min** en el **90 %** de los intentos | Es el que mide la hora pico, que es cuando llega el tráfico |

---

## 3. Las dos alternativas

### Alternativa A — Contenedor gestionado (Render Web Service)

Un proceso que vive de forma continua y atiende todas las peticiones. Es donde
la API corre hoy en local.

### Alternativa B — Función serverless (Vercel Functions)

La API desplegada como función: cada petición la atiende una invocación nueva,
sin proceso persistente entre llamadas.

Ambas son gratuitas y **ninguna exige tarjeta**.

---

## 4. Comparación criterio por criterio

| Criterio | **A · Contenedor (Render Free)** | **B · Función (Vercel Hobby)** |
|---|---|---|
| **Condición operativa** | Cumple: $0, sin tarjeta | Cumple: $0, sin tarjeta |
| **Escenario de calidad** | ESC-02 sí; **ESC-04 falla en frío** | ESC-02 sí; ESC-04 depende del cold start medido |
| **Latencia en caliente** | p50 ~3 ms medido en proceso | Similar, más el salto a `iad1` |
| **p95** | 3,02 ms en proceso ([línea base](linea-base.md)) | Pendiente de medir en la plataforma |
| **Arranque en frío** | **~60 s** tras 15 min sin tráfico (dato oficial de Render) | Menor, pero **por invocación aislada** |
| **Duración máxima** | Sin tope | **300 s** en Hobby |
| **Estado en memoria** | **Se conserva** entre peticiones | **Se pierde** en cada invocación |
| **Persistencia / disco efímero** | Efímero: se pierde en cada redespliegue y al dormirse | Efímero por definición |
| **Conexiones a la base de datos** | **Un pool reutilizado** | **Una conexión nueva por invocación fría** → agota el límite de Supabase |
| **Complejidad** | Un despliegue, un log, un rollback | Dos despliegues si se separa; más piezas |
| **Operación** | Simple | Requiere entender invocaciones y regiones |
| **Rollback** | **Solo 2 despliegues anteriores** (límite del plan gratuito) | Instant Rollback a cualquier despliegue |
| **Disponibilidad** | Render puede reiniciarlo **en cualquier momento** | Auto-escala hasta 30 000 concurrentes |
| **Costo** | **$0** | **$0** |
| **Capa gratuita** | 750 h/mes por workspace; FS efímero; sin disco | 1 M invocaciones · 4 h Active CPU · 360 GB-hrs |
| **Requiere tarjeta** | **No** | **No** |
| **Compatible con Terraform** | ❌ **No en el plan gratuito** (issue [#105](https://github.com/render-oss/terraform-provider-render/issues/105)) | ✅ Sí, provider `vercel/vercel` 5.17 |
| **Automatización** | Auto-deploy desde Git | Auto-deploy desde Git |
| **Evidencia disponible** | Logs, métricas y health checks en panel | Observability en panel |

---

## 5. Arranque en frío contra el escenario

La clase advierte contra medir el cold start *«una vez y en caliente»*: hay que
medir su **frecuencia** contra el patrón de tráfico real.

Con el supuesto de volumen (**200 pedidos/día en 2 h de pico**):

| Cálculo | Valor |
|---|---|
| Ritmo durante el pico | 200 ÷ 120 min = **1,7 pedidos/min** → tráfico cada ~36 s |
| ¿Se duerme durante el pico? | **No.** 36 s ≪ 15 min de umbral |
| Arranques en frío por día | **~2** (uno al inicio de cada pico) |
| Llamadas API/mes | 200 × 5 × 30 = **30 000** |
| Invocaciones frías/mes | ~60 → **0,2 %** |

**Contra ESC-02** (90 % bajo 2 min): 0,2 % ≪ 10 % → **cumple**.

**Contra ESC-04** (< 2 s): el usuario que cae en frío espera 60 s →
**ese caso no cumple**.

Las dos cosas son ciertas y hay que decir las dos. El escenario se cumple en
agregado y se incumple en el peor caso individual.

> **El error que la clase señala, y que aquí se evita:** creer que el arranque
> en frío es un problema solo de las funciones. **El contenedor gratuito tiene
> uno peor** —60 s frente al de una función— porque Render lo duerme. La
> diferencia no es contenedor contra función: es plan gratuito contra plan de
> pago.

---

## 6. Modelo de costo y punto de cruce

### Supuestos declarados

| Supuesto | Valor | Origen |
|---|---|---|
| Pedidos/día | 200 | Estimación del equipo: campus de ~5 000 personas |
| Llamadas API por pedido | 5 | Carta, crear, pagar, consultar ×2 |
| Concentración | 2 h de pico | Horario de almuerzo |
| Duración media de respuesta | 50 ms | p95 medido (3 ms) más margen por red y BD |

### Costo mensual con el volumen estimado

| Recurso | Uso estimado | Incluido | Costo |
|---|---|---|---|
| **A** · Render Web Service Free | 67,5 h de 750 (9 %) | Sí | **$0** |
| **B** · Vercel invocaciones | 30 000 de 1 000 000 (3 %) | Sí | **$0** |
| **B** · Vercel Active CPU | 0,42 h de 4 h (10 %) | Sí | **$0** |
| Supabase Postgres Free | < 500 MB | Sí | **$0** |
| Render Static Site (el sitio) | — | Sí | **$0** |
| GitHub Actions (público) | — | Sí | **$0** |
| **Total** | | | **$0/mes** |

### Dónde se rompe cada capa gratuita

Las dos alternativas se rompen **por motivos distintos**, y esa es la
conclusión más útil de este análisis:

**Alternativa B se rompe por volumen.** El recurso que primero se agota es el
Active CPU, no las invocaciones:

```
4 h de CPU ÷ 50 ms por llamada = 288 000 llamadas/mes
288 000 ÷ 5 llamadas por pedido ÷ 30 días ≈ 1 920 pedidos/día
```

**Punto de cruce ≈ 1 920 pedidos/día**, unas **10 veces** el volumen estimado.
Pasado ese punto hay que subir a Pro ($20/mes), porque Hobby **no admite uso
bajo demanda**: se detiene.

**Alternativa A no se rompe por volumen.** 750 h/mes cubren incluso un servicio
despierto 24/7 (730 h). Se rompe por **latencia**, y desde el primer día: el
arranque en frío incumple ESC-04 para el primer usuario de cada pico, con
cualquier volumen.

| | Se rompe por | A qué volumen |
|---|---|---|
| **A · Contenedor Free** | **Latencia** (ESC-04) | Desde el primer día |
| **B · Función Hobby** | **Costo/cuota** (Active CPU) | ~1 920 pedidos/día |

La tercera opción, **Render Starter a $7/mes**, no se rompe por ninguna de las
dos: elimina el arranque en frío y sí se gestiona con Terraform.

---

## 7. Decisión

**Se elige la Alternativa A: contenedor gestionado en Render, plan gratuito.**

Los motivos, en orden de peso:

**1. Las conexiones a la base de datos.** Es el argumento técnico decisivo. Una
función abre una conexión nueva en cada invocación fría; un contenedor mantiene
un pool reutilizado. Supabase en capa gratuita tiene un número limitado de
conexiones simultáneas, y el patrón de tráfico del sistema es **una ráfaga
concentrada en dos horas**: exactamente el peor caso para un modelo que abre
una conexión por invocación.

**2. El estado en proceso que exige ADR-0003.** `app/eventos.py` publica
`pedido.pagado` a suscriptores en memoria. En una función, cada invocación es
un proceso nuevo: el bus sería un no-op. Migrar a serverless obligaría a
introducir un broker real, que es trabajo de otra entrega.

**3. Simplicidad operativa.** Un despliegue, un log, un rollback. Con tres
estudiantes sin turnos de guardia, cada pieza extra es una pieza que alguien
tiene que entender a las once de la noche.

### Lo que esta decisión cuesta, dicho sin adornos

| Se acepta | Detalle |
|---|---|
| **ESC-04 no se cumple siempre** | ~0,2 % de invocaciones sufren 60 s de espera |
| **La API queda fuera de Terraform** | El provider no gestiona el plan gratuito (issue #105) |
| **Rollback limitado** | Solo a los 2 despliegues anteriores |
| **Reinicios no anunciados** | Render puede reiniciar un servicio gratuito cuando quiera |

Se acepta a cambio de **$0/mes y cero dependencia de tarjeta**, que es la
primera condición operativa de la lista.

---

## 8. Alternativas descartadas y por qué

| Alternativa | Motivo del descarte |
|---|---|
| **B · Función serverless (Vercel Hobby)** | Rompe el bus de eventos en proceso de ADR-0003 y abre una conexión de BD por invocación fría, justo con un patrón de tráfico en ráfagas. Su cold start es **menor** que el del contenedor gratuito, así que el descarte **no** es por latencia |
| **Render Starter ($7/mes)** | Es técnicamente la mejor opción: sin arranque en frío y gestionable con Terraform. Se descarta por la condición operativa de presupuesto $0. **Si el presupuesto cambiara, esta sería la elección** |
| **Servidor del laboratorio** | No ofrece nada utilizable según lo confirmado por el equipo |
| **Render Postgres (gratuito)** | **Expira a los 30 días.** Supabase se pausa, que es reversible; expirar no lo es |
| **MySQL** | Ver §1.1 |

---

## 9. Rollback en la alternativa elegida

```
Versión actual  →  Nuevo despliegue  →  Health check  →  Problema  →  Rollback
```

| Tipo | Cómo se hace | Límite en el plan gratuito |
|---|---|---|
| **Aplicación** | Panel de Render → *Rollback* | **Solo los 2 despliegues anteriores** |
| **Infraestructura** | `git revert` del `.tf` + `terraform apply` | Ninguno |
| **Base de datos** | Restaurar desde copia | **La capa gratuita no incluye copias automáticas** |
| **Configuración** | Cambiar la variable de entorno y redesplegar | Ninguno |

**`terraform destroy` no es un rollback.** Elimina la infraestructura entera,
datos incluidos. Por eso [`infra/supabase.tf`](../infra/supabase.tf) lleva
`prevent_destroy = true`: un `destroy` **falla** en lugar de borrar la base de
datos. Solo tiene sentido al cerrar el semestre, y exige quitar ese bloque a
mano primero.

**El punto débil es el rollback de base de datos**, y hay que decirlo: sin
copias automáticas en la capa gratuita, un cambio de esquema destructivo no se
revierte. La mitigación es que las migraciones sean aditivas.

---

## 10. Qué queda por medir

Este documento contiene proyecciones, no mediciones de producción. Lo que falta:

- [ ] p95 real de la API desplegada, contra los 3,02 ms medidos en proceso
- [ ] Latencia real del arranque en frío, contra los ~60 s que documenta Render
- [ ] Porcentaje real de invocaciones frías con tráfico real
- [ ] Consumo real de conexiones a Supabase durante un pico

Ninguna de esas cifras se inventa aquí. Cuando el despliegue exista, se miden y
se contrastan contra lo proyectado — y si la proyección estaba mal, se dice.
