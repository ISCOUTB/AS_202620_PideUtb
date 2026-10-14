# Imagen de la API.
#
# Dos etapas para que la imagen final no lleve herramientas de compilación.
#
# ### Por qué instala desde `requirements-ci.txt` y no desde `requirements.txt`
#
# Es el lock con hashes, resuelto para Linux y CPython 3.11/3.12 — que es
# exactamente lo que esta imagen es. `requirements.txt` existe para la
# instalación local, donde imponer ese lock rompería el entorno de quien
# trabaja en Windows (ver la cabecera de `requirements.in`).
#
# Aquí no hay esa tensión, así que se usa el archivo más estricto:
#
# - `--require-hashes` hace que una dependencia alterada en el camino falle la
#   construcción en vez de instalarse. Es la misma garantía que ya tenía el
#   pipeline, trasladada a lo que de verdad se despliega.
# - `--only-binary=:all:` prohíbe compilar nada. En el servidor del laboratorio
#   eso no es una preferencia: la construcción comparte memoria con los otros
#   22 equipos y un `pip` compilando `psycopg` desde fuentes es lo que termina
#   en «Killed» con código 137.
#
# Y resuelve de raíz el fallo de la semana 8: entonces `psycopg` estaba en el
# lock de CI pero no en lo que instalaba el despliegue, las pruebas pasaron en
# verde y producción arrancó sin la librería. Con una sola fuente para la
# imagen, ese desajuste deja de ser posible.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS dependencias
COPY requirements-ci.txt .
RUN pip install --prefix=/instalado --require-hashes --only-binary=:all: \
        -r requirements-ci.txt

FROM base
COPY --from=dependencias /instalado /usr/local

# Se copia **lo que la imagen necesita, nombrado uno a uno**, en vez de
# `COPY . .`.
#
# Con la copia recursiva, cualquier archivo que acabe en `backend/` entra en la
# imagen: un `.env` de pruebas, un volcado de base de datos, unas credenciales
# que alguien dejó mientras depuraba. El `.dockerignore` ayuda, pero funciona al
# revés que esta lista — enumera lo que se excluye, así que lo que nadie previó
# entra. Aquí lo que nadie previó se queda fuera.
#
# Es la misma lección de V-11 aplicada a la imagen: lo que no se publica no se
# puede filtrar.
COPY app ./app
COPY migraciones ./migraciones
COPY scripts/migrar.py scripts/sembrar_usuario_inicial.py ./scripts/
COPY entrypoint.sh ./entrypoint.sh

# Usuario sin privilegios. Si un fallo de la aplicación llegara a ejecutar algo,
# lo ejecuta alguien que no puede escribir ni en su propio código.
RUN useradd --uid 10001 --no-create-home app
USER app

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
