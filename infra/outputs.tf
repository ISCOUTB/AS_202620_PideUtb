# Lo que Terraform devuelve al terminar.
#
# Un output es un valor que Terraform imprime tras `apply` y que se puede
# consultar después con `terraform output`. Sirve para dos cosas:
#
#   1. No tener que buscar en el panel del proveedor la URL que acaba de
#      crearse.
#   2. Alimentar otras herramientas: `terraform output -raw sitio_url` se puede
#      pasar directamente a un `curl` en el pipeline.
#
# Un output marcado `sensitive` no se imprime; hay que pedirlo explícitamente
# con `terraform output -raw <nombre>`. Igual que en las variables, eso oculta
# pero no cifra.

output "sitio_url" {
  description = "URL pública del sitio. Es la que se entrega como evidencia."
  value       = render_static_site.sitio.url
}

output "supabase_project_ref" {
  description = <<-DESC
    Identificador del proyecto de Supabase. Es la pieza que falta para armar la
    cadena de conexión, que el backend recibe por variable de entorno:

      postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres

    La contraseña no se imprime aquí a propósito: sale de `terraform.tfvars` y
    la conoce el equipo. Juntar las dos mitades en un output sería publicar la
    cadena completa en la salida de la terminal y en el log de CI.
  DESC
  value       = supabase_project.pideutb.id
}

output "rama_protegida" {
  description = "Rama sobre la que el pipeline bloquea el merge ante fallos."
  value       = github_branch_protection.rama_evaluable.pattern
}
