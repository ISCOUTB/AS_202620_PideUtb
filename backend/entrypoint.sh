#!/bin/sh
# Arranque de la API: primero el esquema, después el servidor.
#
# ### Por qué las migraciones corren aquí, si ADR-0007 decía lo contrario
#
# ADR-0007 argumentó que un proceso web que modifica el esquema al arrancar lo
# hace **en cada instancia a la vez y cuando nadie está mirando**, y que por eso
# `migrar.py` debía ser un paso que alguien ejecuta.
#
# Ese argumento valía para el despliegue anterior y deja de valer aquí, por dos
# hechos del servidor del laboratorio:
#
# 1. **Hay un solo contenedor de API**, sin autoescalado. La carrera entre
#    instancias que motivaba la regla no existe.
# 2. **No hay copia de seguridad garantizada de los volúmenes.** Un volumen que
#    desaparece deja una base vacía, y con las migraciones a mano el servicio
#    arrancaría contra un esquema inexistente y fallaría en cada petición hasta
#    que alguien se diera cuenta. Corriéndolas al arrancar, un despliegue limpio
#    siempre deja la base utilizable.
#
# El riesgo que esto sí introduce: si una migración falla, el contenedor no
# arranca. Es deliberado — `set -e` hace que el despliegue quede en rojo en vez
# de levantar una API contra un esquema a medio aplicar, que es el fallo
# silencioso que cuesta horas encontrar.
set -e

echo '{"level":"INFO","service":"api","event":"migraciones_inicio"}'
python scripts/migrar.py
echo '{"level":"INFO","service":"api","event":"migraciones_fin"}'

# La primera cuenta del panel, y solo si no hay ninguna.
#
# Va aquí porque en el servidor del laboratorio no hay otra forma: la base no
# publica puertos y el panel no da terminal, así que `crear_usuario.py` no se
# puede ejecutar contra producción. Sin esto, un despliegue limpio deja un
# sistema perfecto en el que nadie puede entrar.
python scripts/sembrar_usuario_inicial.py

# `--root-path` solo cuando la API se publica bajo un prefijo que el proxy
# recorta. Vacío en local, `/api` en el laboratorio: sin esto, `/api/docs`
# genera enlaces a `/docs` y la documentación queda rota.
#
# `exec` para que uvicorn sea el PID 1 y reciba las señales de parada
# directamente. Sin él, el contenedor tarda diez segundos en morir porque este
# shell ignora el SIGTERM.
if [ -n "${PIDEUTB_ROOT_PATH:-}" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        --proxy-headers --forwarded-allow-ips '*' \
        --root-path "${PIDEUTB_ROOT_PATH}"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips '*'
