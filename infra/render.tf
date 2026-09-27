# Pieza 1 de seis: el sitio.
#
# Publica el frontend como sitio estático servido desde la CDN de Render.
#
# Un sitio estático no tiene arranque en frío: no hay proceso que despertar,
# solo archivos en una red de distribución. Por eso la pieza 1 no sufre el
# problema que sí tiene la pieza 2, aunque ambas vivan en la misma plataforma.
#
# Los sitios estáticos de Render **son gratuitos** y sí se pueden gestionar con
# Terraform: `render_static_site` no tiene siquiera atributo `plan`. Es la
# diferencia con `render_web_service`, que se explica abajo.

resource "render_static_site" "sitio" {
  name     = "pideutb-sitio"
  repo_url = "https://github.com/ISCOUTB/AS_202620_PideUtb"
  branch   = var.rama_evaluable

  # El sitio es HTML, CSS y JavaScript sin transpilar: no hay nada que
  # construir. Render exige un comando de build, así que se le da uno que no
  # hace nada en vez de inventar un paso de construcción ornamental.
  build_command = "echo 'sitio estatico: sin paso de construccion'"

  # Carpeta del repositorio que se publica.
  publish_path = "sitio"

  # Cada push a la rama evaluable redespliega el sitio. Es aceptable aquí
  # porque un sitio estático no tiene estado que perder: el peor caso de un
  # despliegue malo es servir HTML viejo, y el rollback es inmediato.
  auto_deploy = true
}

# --------------------------------------------------------------------------
# Pieza 2: la API. No está aquí, y es una limitación conocida.
# --------------------------------------------------------------------------
# `render_web_service` **no admite el plan gratuito**. El atributo `plan` acepta
# `starter`, `standard`, `pro`… y la palabra `free` no aparece en el esquema.
# La issue #105 del provider, abierta, lo describe:
#
#   «Free-tier web services can't be managed with Terraform. […] The result:
#    a perpetual diff on import, and every apply failing with "maintenance mode
#    can only be configured for non-free tier services"»
#
#   https://github.com/render-oss/terraform-provider-render/issues/105
#
# El equipo eligió costo cero sobre cobertura total de infraestructura como
# código. La API se crea a mano en el panel, y se acepta a cambio:
#
#   - ~60 s de arranque en frío tras 15 min sin tráfico
#   - incumplimiento de ESC-04 (< 2 s) en ~0,2 % de invocaciones
#   - rollback limitado a los dos despliegues anteriores
#
# La alternativa descartada es el plan `starter`, 7 USD/mes, que elimina el
# arranque en frío y sí se gestiona con Terraform. Queda documentada en el ADR
# de plataforma con su costo y su motivo de descarte.
#
# Si algún día se adopta el plan de pago, la API entra aquí como un recurso más
# y esta nota desaparece.
