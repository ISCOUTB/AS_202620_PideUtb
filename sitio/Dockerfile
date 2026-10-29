# Imagen del sitio.
#
# Dos etapas, y la primera no compila nada: **sella**. El sitio sigue sin tener
# paso de construcción —sin framework ni empaquetador, los archivos que se
# sirven son los mismos que están en el repositorio—, pero sí tiene algo que
# calcular, y la razón está contada abajo.
#
# En el servidor del laboratorio eso además importa por el presupuesto: nginx
# sirviendo estáticos cabe en 64 MB, mientras que un frontend con renderizado
# en servidor pediría 160 MB de los 512 del equipo. La etapa de sellado se tira
# al terminar y no pesa nada en la imagen final.

# ---------------------------------------------------------------------------
# El sellado: cada hoja y cada guion llevan su huella en la URL
# ---------------------------------------------------------------------------
#
# `nginx.conf` manda `expires -1` para todo, o sea `Cache-Control: no-cache`.
# Cloudflare lo reescribe: el HTML le llega al navegador con `no-cache`, pero
# los `.css` y los `.js` con `max-age=14400`. Cuatro horas.
#
# Esa mezcla no es «la página tarda en actualizarse»: es **la página rota**. El
# 29 de octubre de 2026, con el rediseño recién desplegado, un teléfono que
# había abierto el sitio esa misma tarde se descargó el `index.html` nuevo y
# siguió usando el `app.js` viejo. El guion viejo buscaba `#barra-carrito`, que
# el HTML nuevo ya no tiene, y la primera línea que lo tocaba reventaba:
#
#     null is not an object (evaluating 'barra.classList')
#
# Media carta cargada y ningún botón respondiendo. Y no se arregla pidiéndole
# al público que recargue con el teclado: no hay teclado, y son sesenta.
#
# El origen no puede arreglarlo —ya manda la cabecera correcta y Cloudflare la
# pisa—, así que se arregla donde sí tenemos mando: **en la URL**. Si el HTML
# pide `app.js?v=1a2b3c4d` y la huella cambia con el contenido, el navegador no
# tiene nada en caché con ese nombre y lo pide entero. Lo viejo se queda
# guardado con su URL vieja, que ya no pide nadie, y caduca solo.
#
# Funciona porque el `index.html` sí llega siempre fresco. Es la única pieza
# que Cloudflare no cachea, y es justo la que decide qué versión del resto se
# carga.
FROM alpine:3.21 AS sellado

WORKDIR /sitio
COPY *.html *.css *.js *.svg ./

# Ocho caracteres del sha256 bastan: no es una firma, es un nombre distinto
# para un contenido distinto. Una prueba comprueba que esta lista cubre todo lo
# que los HTML piden, porque el fallo realista no es que el sellado se rompa,
# es que alguien añada un guion nuevo y no lo apunte acá.
RUN set -eu; \
    for activo in estilos.css pasarela.css config.js app.js panel.js pasarela.js; do \
        huella="$(sha256sum "$activo" | cut -c1-8)"; \
        sed -i "s|=\"$activo\"|=\"$activo?v=$huella\"|g" *.html; \
    done; \
    grep -q 'app.js?v=' index.html

# ---------------------------------------------------------------------------
# El servidor
# ---------------------------------------------------------------------------
#
# `nginx-unprivileged` y no la imagen oficial: esta corre como un usuario sin
# privilegios desde el primer proceso, no solo en los trabajadores. A cambio
# escucha en el **8080**, porque un proceso sin privilegios no puede tomar el
# puerto 80.
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Sin `--chown`: los archivos quedan de root y nginx solo puede **leerlos**. Con
# la propiedad cambiada al usuario que sirve, un fallo en el servidor podría
# reescribir las páginas que entrega — que es justo lo que no se quiere de un
# contenedor cuyo contenido no cambia nunca en caliente.
COPY --from=sellado /sitio/ /usr/share/nginx/html/

# Las dos tipografías, servidas desde este mismo origen.
#
# No es purismo: el 3 de noviembre el público abre el sitio a la vez desde la
# red de un auditorio, y una petición menos a fonts.gstatic.com es un punto
# menos donde la demo se queda sin tipografía delante de todo el mundo. Son
# 115 KB entre las dos, variables y recortadas al subconjunto latino.
#
# No se sellan: las referencia la hoja de estilos, que ya va sellada, y un
# archivo de tipografía no cambia sin cambiar de nombre.
COPY fuentes/ /usr/share/nginx/html/fuentes/

EXPOSE 8080
