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

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx *.html *.css *.js /usr/share/nginx/html/

EXPOSE 80
