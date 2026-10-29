# Imagen del sitio.
#
# Una sola etapa, y eso es la consecuencia visible de una decisión vieja: el
# sitio no tiene paso de construcción. Sin framework ni empaquetador, los
# archivos que se sirven son los mismos que están en el repositorio, así que no
# hay nada que compilar ni una etapa de la que copiar artefactos.
#
# En el servidor del laboratorio eso además importa por el presupuesto: nginx
# sirviendo estáticos cabe en 64 MB, mientras que un frontend con renderizado
# en servidor pediría 160 MB de los 512 del equipo.

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
COPY *.html *.css *.js *.svg /usr/share/nginx/html/

# Las dos tipografías, servidas desde este mismo origen.
#
# No es purismo: el 3 de noviembre el público abre el sitio a la vez desde la
# red de un auditorio, y una petición menos a fonts.gstatic.com es un punto
# menos donde la demo se queda sin tipografía delante de todo el mundo. Son
# 115 KB entre las dos, variables y recortadas al subconjunto latino.
#
# En `COPY` aparte porque un directorio no se puede mezclar con comodines de
# archivos en la misma instrucción sin que el contenido acabe aplanado.
COPY fuentes/ /usr/share/nginx/html/fuentes/

EXPOSE 8080
