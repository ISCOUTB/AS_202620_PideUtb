# Pieza 6 de seis: el pipeline.
#
# El workflow ya existe en `.github/workflows/ci.yml` y no se gestiona desde
# aquí: es un archivo del repositorio, versionado y revisable como cualquier
# otro. Lo que sí falta —y es lo que este archivo aporta— es **que el pipeline
# pueda bloquear**.
#
# El material de la semana 8 lo pide con esas palabras: «un pipeline de CI que
# ejecute pruebas y análisis estático y **bloquee el merge ante fallos**».
# Hasta ahora el pipeline informa; con esto, impide.
#
# Que la regla sea código y no un clic en una interfaz es la diferencia entre
# una protección que se puede revisar en un pull request y una que solo conoce
# quien la configuró.

resource "github_branch_protection" "rama_evaluable" {
  repository_id = var.github_repo
  pattern       = var.rama_evaluable

  # ------------------------------------------------------------------------
  # Los checks que deben pasar antes de poder mezclar
  # ------------------------------------------------------------------------
  # Los nombres tienen que coincidir **exactamente** con los que publica cada
  # job. Un nombre mal escrito no da error: GitHub simplemente espera para
  # siempre un check que nunca llega, y el pull request queda bloqueado sin
  # explicación.
  #
  # Verificados contra la API de checks de un commit real de `master`.
  required_status_checks {
    # `strict = true` exige además que la rama esté al día con `master` antes
    # de mezclar. Evita el caso clásico: dos cambios que pasan por separado y
    # se rompen al juntarse.
    strict = true

    contexts = [
      "pytest (Python 3.11)",
      "pytest (Python 3.12)",
      "Contrato de API",
      "SonarCloud",
      "SonarCloud Code Analysis",
    ]
  }

  # ------------------------------------------------------------------------
  # Esto cambia cómo trabaja el equipo. Conviene saberlo antes de aplicarlo.
  # ------------------------------------------------------------------------
  # Con `enforce_admins = true` la regla se aplica **también a los
  # administradores**. Consecuencia concreta: nadie podrá volver a hacer
  # `git push origin master` directamente; todo cambio pasará por un pull
  # request con los checks en verde.
  #
  # Es más incómodo y es el punto. Una protección que el propio equipo puede
  # saltarse no protege de nada: el día que haya prisa, alguien la saltará.
  enforce_admins = true

  # Nadie borra ni reescribe la rama evaluable. `master` es la referencia de la
  # entrega y los enlaces de evidencia de `correcciones.md` apuntan a commits
  # concretos suyos: un force-push los dejaría apuntando al vacío.
  allows_deletions    = false
  allows_force_pushes = false
}

# --------------------------------------------------------------------------
# Los secretos del pipeline NO se gestionan aquí, y es una decisión de seguridad
# --------------------------------------------------------------------------
# El provider ofrece `github_actions_secret`, y sería tentador usarlo para
# tenerlo «todo en Terraform». No se hace, por dos motivos:
#
#   1. El valor acabaría **en claro dentro del archivo de state**. El state es
#      local y no está cifrado; su única protección es el `.gitignore`. Meter
#      ahí `SONAR_TOKEN` multiplica las copias del secreto sin ganar nada.
#   2. Los atributos `plaintext_value` y `encrypted_value` están marcados como
#      **deprecados** en el provider.
#
# Los secretos se configuran en la interfaz de GitHub, donde quedan cifrados y
# no son legibles ni siquiera por quien los creó. Qué secretos hacen falta y de
# dónde salen está documentado en `README.md` de esta carpeta.
#
# «Todo lo posible en Terraform» no incluye lo que empeora la postura de
# seguridad al meterlo.
