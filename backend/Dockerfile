# Imagen de la API.
#
# Dos etapas para que la imagen final no lleve herramientas de compilación.
#
# ### Qué lock instala, y por qué hay cuatro
#
# | Archivo | Para qué |
# |---|---|
# | `requirements-prod.txt` | **Esta imagen.** 22 paquetes: lo que la aplicación importa |
# | `requirements-ci.txt` | El pipeline. Los mismos 22 más `pytest`, `httpx` y 6 dependencias suyas |
# | `requirements-calidad.txt` | Solo el job de cobertura: `pytest-cov` y `coverage` |
# | `requirements.txt` | Instalación local, con rangos, para no romper Windows |
#
# Que sean cuatro no es desorden: cada uno responde a un entorno con
# restricciones distintas, y la alternativa —un archivo para todo— es la que
# metió `pytest` en producción.
#
# Hasta la S13 esta imagen instalaba el lock de CI, así que llevaba dentro
# **ocho paquetes que ningún código de la aplicación importa**. Lo destapó la
# auditoría de dependencias: `pytest<=9.0.2` arrastra GHSA-6w46-j5rx-g56g
# (moderada, vector local) y estaba en producción sin ejecutarse nunca allí.
#
# La vulnerabilidad concreta era menor; la regla incumplida no: en la imagen no
# debería haber nada que la aplicación no use. Cada paquete de más es superficie
# que hay que vigilar y que algún día tendrá su propio aviso.
#
# `requirements-prod.txt` se deriva del de CI quitando lo que no es alcanzable
# desde `fastapi`, `uvicorn` ni `psycopg`, y el job `dependencias` del pipeline
# comprueba en Linux que la aplicación importa con solo esos 22 — porque no hay
# Docker en la máquina de desarrollo para construir la imagen y verlo
# (deuda D-01 de arc42 §11).
#
# De los tres se elige aquí el más estricto:
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
COPY requirements-prod.txt .
RUN pip install --prefix=/instalado --require-hashes --only-binary=:all: \
        -r requirements-prod.txt

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
