# Infraestructura como código

Terraform gestiona aquí tres de las seis piezas del sistema. Este documento
explica qué gestiona, qué **no**, y cómo ejecutarlo sin romper nada.

## Qué gestiona y qué no

| # | Pieza | Dónde vive | ¿En Terraform? |
|---|---|---|---|
| 1 | Sitio | Render Static Site | ✅ [`render.tf`](render.tf) |
| 2 | **API** | Render Web Service | ❌ **No** — ver abajo |
| 3 | Base de datos | Supabase PostgreSQL | ✅ [`supabase.tf`](supabase.tf) |
| 4 | Archivos | — | No aplica: el sistema no almacena archivos |
| 5 | Trabajo programado | GitHub Actions cron | No: es un workflow del repositorio |
| 6 | Pipeline | GitHub Actions | ✅ Parcial — [`github.tf`](github.tf) protege la rama |

### Por qué la API no está aquí

`render_web_service` **no admite el plan gratuito**: su atributo `plan` acepta
`starter`, `standard`, `pro`… y `free` no aparece. La
[issue #105](https://github.com/render-oss/terraform-provider-render/issues/105)
del provider, abierta, lo describe como *«free-tier web services can't be
managed with Terraform […] every apply failing»*.

El equipo eligió **costo cero** sobre cobertura total de IaC. Lo que se acepta a
cambio está analizado en
[`comparacion-despliegue.md`](../docs/comparacion-despliegue.md) y decidido en
[ADR-0004](../docs/adr/0004-plataforma-de-despliegue.md):

| Se acepta | Cifra | De dónde sale |
|---|---|---|
| Arranque en frío | ~60 s tras 15 min sin tráfico | Dato oficial de Render |
| ESC-04 se incumple en el peor caso | **~0,2 %** de las invocaciones | Derivado en §5: ~60 invocaciones frías sobre 30 000 llamadas/mes |
| Rollback limitado | Solo los **2 despliegues anteriores** | Límite del plan gratuito, §9 |

Ese minuto de arranque consume además **la mitad del presupuesto** de
[ESC-02](../docs/arc42/arc42.md#esc-02) —120 s para el recorrido completo del
usuario— en el primer pedido de cada pico.

La API se crea a mano en el panel de Render. **No es un olvido: es la decisión
documentada.** El procedimiento exacto está abajo, para que el paso manual sea
repetible y no dependa de que alguien recuerde cómo lo hizo.

### Crear la API a mano, paso a paso

En el panel de Render: **New → Web Service**, y conectar este repositorio.

| Campo | Valor | Por qué |
|---|---|---|
| Language | `Python 3` | |
| Region | La misma que el sitio | Dos regiones distintas añaden latencia entre piezas que se llaman todo el tiempo |
| Branch | `master` | |
| Root Directory | `backend` | El proyecto de Python no está en la raíz del repositorio |
| Build Command | `pip install -r requirements.txt` | |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `0.0.0.0` y no `127.0.0.1`: dentro de un contenedor, escuchar solo en local significa que nadie de fuera llega. `$PORT` lo fija la plataforma y no se puede elegir |
| Instance Type | `Free` | |
| Health Check Path | `/health` | Sin esto la plataforma solo sabe si el proceso arrancó, no si sus dependencias responden |

Variables de entorno, en **Environment**:

| Variable | Valor | Si falta |
|---|---|---|
| `PIDEUTB_ORIGENES_PERMITIDOS` | La URL del sitio, sin barra final | El navegador bloquea toda llamada del sitio a la API |
| `PIDEUTB_SUPABASE_URL` | La URL del proyecto de Supabase | La sonda de base de datos no se registra y `/health` solo reporta el catálogo |
| `PIDEUTB_NIVEL_LOG` | `INFO` | Opcional; por defecto ya es `INFO` |

Después del primer despliegue quedan **dos pasos que no se pueden hacer antes**,
porque nadie conoce la URL hasta que existe:

1. Poner la URL de la API en [`sitio/config.js`](../sitio/config.js)
   (`API_PRODUCCION`) y hacer push: el sitio se redespliega solo.
2. Registrar `https://<la-api>/v1/pagos/eventos` como URL de webhook en el
   panel de la pasarela.

Comprobación de que quedó bien —las tres, no solo la primera—:

```bash
curl -s https://<la-api>/health
curl -s https://<la-api>/metricas
curl -si https://<la-api>/health | grep -i x-request-id
```

La primera llamada tras un rato de silencio tarda ~60 s: es el arranque en
frío, no un fallo.

## Antes de empezar

### 1. Terraform

```bash
terraform version
```

Debe decir `v1.9` o superior. Si no lo reconoce después de instalarlo, cerrá
la terminal y abrí una nueva: Windows solo actualiza el `PATH` en terminales
nuevas.

### 2. Las credenciales

```bash
cp terraform.tfvars.example terraform.tfvars
```

Rellená los cinco valores siguiendo los comentarios del archivo. **`terraform.tfvars`
está en `.gitignore` y no debe versionarse nunca.**

Comprobalo antes de commitear cualquier cosa:

```bash
git status --short infra/
```

Si `terraform.tfvars` aparece en esa lista, **pará**.

## Los comandos, en orden

| Comando | Qué hace | ¿Toca infraestructura? |
|---|---|---|
| `terraform init` | Descarga los providers | No |
| `terraform fmt` | Reformatea los `.tf` | No |
| `terraform validate` | Comprueba sintaxis y tipos | No |
| `terraform plan` | Calcula qué haría | **No** — solo lee |
| `terraform apply` | Ejecuta el plan | **Sí** |
| `terraform destroy` | Borra todo lo gestionado | **Sí, irreversible** |

Los cuatro primeros son seguros. Ejecutalos sin miedo.

### Antes de cada `apply`

Leé la última línea del plan:

```
Plan: 3 to add, 0 to change, 0 to destroy.
```

**Si el número de `destroy` no es cero y no pediste destruir nada, parad.**
Algo no cuadra entre la configuración y lo que existe.

## Quién aplica

**Una sola persona.**

Terraform no pregunta al proveedor qué existe: consulta su propio archivo de
state, que es su memoria de lo que creó. Ese archivo es local y no está en Git
—contiene la contraseña de la base de datos en claro—, así que si otro
integrante ejecuta `apply` desde su computador verá un state vacío e intentará
**crear todo otra vez**, duplicando los recursos.

Para esta entrega aplica **Santiago Cuesta**. Los demás leen los `.tf` y los
revisan en el pull request, que es donde está el valor de que esto sea código.

## Sobre `terraform destroy`

**No es un rollback.** Un rollback devuelve la aplicación a una versión anterior
que funcionaba; `destroy` elimina la infraestructura entera, datos incluidos.

Por eso [`supabase.tf`](supabase.tf) lleva `prevent_destroy = true`: un
`destroy` **fallará** en lugar de borrar la base de datos. Para desmontar el
proyecto al final del semestre hay que quitar ese bloque a mano primero. Esa
fricción es deliberada.

## Los secretos no están aquí

Los secretos del pipeline se configuran en **GitHub → Settings → Secrets and
variables → Actions**, no con Terraform.

El motivo es de seguridad, no de comodidad: un `github_actions_secret` guardaría
el valor **en claro dentro del state**, que es local y no cifrado. Configurado
en GitHub queda cifrado y no es legible ni por quien lo creó.

| Secreto | Para qué | Estado |
|---|---|---|
| `SONAR_TOKEN` | Análisis desde el pipeline | Pendiente — ver [`docs/calidad-sonarcloud.md`](../docs/calidad-sonarcloud.md) |

## Un aviso sobre la protección de rama

[`github.tf`](github.tf) activa `enforce_admins = true`. **Cuando se aplique,
nadie podrá volver a hacer `git push origin master` directamente**: todo cambio
pasará por un pull request con los checks en verde.

Es lo que pide el material de la semana 8 —*«bloquee el merge ante fallos»*— y
es más incómodo a propósito. Una protección que el equipo puede saltarse no
protege nada.

Requiere permisos de **administración** sobre el repositorio de la organización.
Si no los tenés, ese recurso fallará al aplicarse.
