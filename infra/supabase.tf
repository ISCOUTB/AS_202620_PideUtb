# Pieza 3 de seis: la base de datos.
#
# Crea un proyecto de Supabase, que es PostgreSQL gestionado. Sustituye a los
# diccionarios en memoria de `backend/app/*/repository.py` y cierra la
# violación V-09: hoy el estado vive en la memoria del proceso y desaparece en
# cada redespliegue.
#
# Por qué PostgreSQL y no MySQL: `EstadoPedido` es un conjunto cerrado que
# Postgres respalda con un tipo ENUM real, y la idempotencia que promete
# ADR-0003 se expresa con `INSERT … ON CONFLICT DO NOTHING`, que es una
# primitiva del lenguaje. En MySQL habría que recurrir a `INSERT IGNORE`, que
# silencia errores que no son duplicados.

resource "supabase_project" "pideutb" {
  organization_id   = var.supabase_org_id
  name              = "pideutb"
  database_password = var.supabase_db_password
  region            = var.supabase_region

  # ------------------------------------------------------------------------
  # Protección contra borrado accidental
  # ------------------------------------------------------------------------
  # `prevent_destroy` hace que `terraform destroy` **falle** en lugar de
  # borrar la base de datos. Es deliberado: el §19 del enunciado advierte que
  # `destroy` no es un rollback, y esta línea convierte esa advertencia en algo
  # que la herramienta impone.
  #
  # Para desmontar el proyecto al final del semestre hay que borrar este bloque
  # a mano primero. Esa fricción es el punto: obliga a que destruir la base de
  # datos sea una decisión y no un descuido.
  lifecycle {
    prevent_destroy = true
  }
}

# --------------------------------------------------------------------------
# Lo que este recurso NO gestiona, y por qué
# --------------------------------------------------------------------------
# El **esquema** de la base de datos —tablas, índices, restricciones— no está
# aquí. Terraform crea el proyecto; las tablas las crea una migración desde el
# código de la aplicación.
#
# Es una separación a propósito. El esquema cambia con el dominio y lo revisan
# los mismos que revisan el código; la infraestructura cambia con la plataforma.
# Mezclarlos obligaría a ejecutar `terraform apply` para añadir una columna, y
# a que quien no toca infraestructura tenga credenciales de infraestructura.
