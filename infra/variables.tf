# Entradas de la infraestructura.
#
# Una variable es un hueco en la configuración que se rellena al ejecutar. Sirve
# para dos cosas distintas:
#
#   1. No escribir credenciales dentro de archivos versionados.
#   2. Poder desplegar lo mismo con valores distintos sin tocar el código.
#
# `sensitive = true` hace que Terraform **oculte el valor** en la salida de
# `plan` y `apply`, mostrando `(sensitive value)`. Es importante entender su
# límite: **no cifra nada**. El valor sigue guardado en claro dentro del archivo
# de state. Evita que una credencial acabe en una captura de pantalla o en el
# log de CI; no evita que acabe en Git si alguien versiona el state.
#
# El nombre de cada variable coincide con el atributo del provider que alimenta.
# Es deliberado: al leer `api_key = var.render_api_key` no hay que adivinar de
# dónde sale el valor.

# --------------------------------------------------------------------------
# Render — el sitio estático
# --------------------------------------------------------------------------

variable "render_api_key" {
  description = "Clave de API de Render. Se genera en Account Settings → API Keys."
  type        = string
  sensitive   = true
}

variable "render_owner_id" {
  description = <<-DESC
    Identificador de la cuenta bajo la que se crean los recursos. Empieza por
    `usr-` en cuentas individuales y por `tea-` en cuentas de equipo. Se
    encuentra en la URL del panel de Render.
  DESC
  type        = string

  validation {
    condition     = can(regex("^(usr|tea)-", var.render_owner_id))
    error_message = "El owner_id de Render debe empezar por 'usr-' o 'tea-'. Revisá la URL del panel."
  }
}

# --------------------------------------------------------------------------
# Supabase — la base de datos PostgreSQL
# --------------------------------------------------------------------------

variable "supabase_access_token" {
  description = "Token personal de Supabase. Se genera en supabase.com/dashboard/account/tokens."
  type        = string
  sensitive   = true
}

variable "supabase_org_id" {
  description = "Identificador de la organización de Supabase donde se crea el proyecto."
  type        = string
}

variable "supabase_db_password" {
  description = <<-DESC
    Contraseña del usuario `postgres` del proyecto. La define el equipo al
    crear el proyecto y **no se puede recuperar después**, solo restablecer.

    No se inventa a mano: generala con un gestor de contraseñas o con
    `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
  DESC
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.supabase_db_password) >= 16
    error_message = "La contraseña de la base de datos debe tener al menos 16 caracteres."
  }
}

variable "supabase_region" {
  description = <<-DESC
    Región del proyecto. `us-east-1` es la más cercana a Colombia de las
    disponibles en la capa gratuita; la latencia hacia el usuario final importa
    para ESC-02, que mide el pico de almuerzo.
  DESC
  type        = string
  default     = "us-east-1"
}

# --------------------------------------------------------------------------
# GitHub — protección de rama y secretos del pipeline
# --------------------------------------------------------------------------

variable "github_token" {
  description = <<-DESC
    Token personal de GitHub con permiso de administración sobre el
    repositorio. Hace falta para configurar la protección de rama.

    Si no tenés permisos de administración sobre el repositorio de la
    organización, esa parte fallará: es una limitación de permisos, no de la
    configuración.
  DESC
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "Organización propietaria del repositorio."
  type        = string
  default     = "ISCOUTB"
}

variable "github_repo" {
  description = "Nombre del repositorio."
  type        = string
  default     = "AS_202620_PideUtb"
}

# --------------------------------------------------------------------------
# Común
# --------------------------------------------------------------------------

variable "rama_evaluable" {
  description = <<-DESC
    Rama que se despliega y que se protege. Es la misma que declara
    `correcciones.md` como rama evaluable, y por eso es una sola variable: si
    el equipo cambia de rama, cambia en un único sitio.
  DESC
  type        = string
  default     = "master"
}
