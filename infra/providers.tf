# Qué herramientas usa Terraform y con qué versiones.
#
# Este archivo no crea nada. Declara dos cosas:
#
#   1. `terraform { required_providers }` — qué plugins hay que descargar.
#   2. `provider "x" {}`                  — cómo autenticarse contra cada uno.
#
# Las versiones se fijan con `~>`, que permite parches y correcciones pero no
# saltos de versión menor: `~> 1.9` acepta 1.9.1 y 1.9.7, y rechaza 1.10.0. Es
# la misma disciplina que `backend/requirements-ci.txt` — que una construcción
# cambie sola nunca es una buena noticia.
#
# El archivo `.terraform.lock.hcl` que genera `terraform init` **sí se versiona**
# en Git: fija la versión exacta y su hash, igual que el lock de Python. Es lo
# que hace que el mismo código produzca la misma infraestructura en otra
# máquina.

terraform {
  required_version = ">= 1.9"

  required_providers {
    # Gestiona el sitio estático. El web service de la API NO se gestiona aquí:
    # el plan gratuito no se puede administrar con Terraform (issue #105 del
    # provider), y se documenta esa limitación en el ADR de plataforma.
    render = {
      source  = "render-oss/render"
      version = "~> 1.9"
    }

    # Gestiona el proyecto de base de datos PostgreSQL.
    supabase = {
      source  = "supabase/supabase"
      version = "~> 1.11"
    }

    # Gestiona la protección de rama y los secretos del pipeline. Que el
    # "bloquear el merge ante fallos" sea código y no un clic en una interfaz
    # es justamente lo que pide la semana 8.
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
  }
}

# --------------------------------------------------------------------------
# Autenticación
#
# Ninguna credencial se escribe aquí. Todas llegan por variable, y las
# variables llegan por `terraform.tfvars` —que está en .gitignore— o por
# variables de entorno `TF_VAR_*`.
# --------------------------------------------------------------------------

provider "render" {
  api_key  = var.render_api_key
  owner_id = var.render_owner_id
}

provider "supabase" {
  access_token = var.supabase_access_token
}

provider "github" {
  token = var.github_token
  owner = var.github_owner
}
