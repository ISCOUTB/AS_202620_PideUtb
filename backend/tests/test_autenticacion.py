"""El mecanismo de autenticación, contra PostgreSQL de verdad.

Cubre [ADR-0007](../../docs/adr/0007-autenticacion-del-panel.md) y cierra
[V-10](../../docs/violaciones.md#v-10).

### Por qué este archivo exige PostgreSQL y no se conforma con memoria

`usuarios.repository` **no tiene** implementación en memoria para usuarios ni
sesiones, y es deliberado. Una autenticación de juguete que funciona sin base
de datos invita a desplegar sin ella, y lo que se despliega sin almacén de
sesiones es un sistema que no las tiene.

La contrapartida es que sin `PIDEUTB_DATABASE_URL_PRUEBAS` estos casos se
**omiten**. Omitir no es gratis —una prueba omitida se lee casi igual que una
que pasa en el resumen de pytest— así que hay dos defensas:

- `test_la_autenticacion_se_probo_contra_postgres` **falla** si la variable
  está puesta y aun así nada se ejecutó.
- El pipeline la define siempre, con un contenedor efímero. Es decir: en CI
  esto no se omite nunca, y si alguien lo rompe, se ve.

La variable es distinta de `PIDEUTB_DATABASE_URL` por el mismo motivo que en
`test_repositorios.py`: si coincidieran, tener la de la aplicación exportada en
la terminal bastaría para que la suite tocara las tablas de producción.

### Lo que **no** se prueba aquí

La autorización del panel —quién puede ver qué cola, qué responde un pedido
ajeno— está en `test_panel_mostrador.py`, con la dependencia sustituida. Separar
los dos es lo que evita que un fallo de scrypt rompa veinte pruebas que no
hablan de contraseñas, y que cada caso del panel pague los ~100 ms de una
derivación que no aporta nada a lo que ese caso comprueba.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import base_de_datos
from app.autenticacion import establecimiento_que_puede_ver, personal_de_establecimiento
from app.usuarios import credenciales, repository
from app.usuarios import service as cuentas
from app.usuarios.contracts import RolUsuario, UsuarioAutenticado

RAIZ = Path(__file__).resolve().parent.parent
MIGRACIONES = RAIZ / "migraciones"

URL_PRUEBAS = os.getenv("PIDEUTB_DATABASE_URL_PRUEBAS", "").strip()

#: Cuántos casos llegaron a correr contra PostgreSQL. Lo revisa la última
#: prueba del archivo.
_EJECUTADOS: list[str] = []


@pytest.fixture
def postgres(request, monkeypatch):
    """Deja el sistema apuntando a un PostgreSQL con el esquema aplicado."""
    if not URL_PRUEBAS:
        pytest.skip(
            "Sin PIDEUTB_DATABASE_URL_PRUEBAS: no hay PostgreSQL contra el que "
            "probar la autenticación, y no hay implementación en memoria a "
            "propósito (ADR-0007)."
        )

    import psycopg

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    base_de_datos.cerrar_pool()

    with psycopg.connect(URL_PRUEBAS) as conexion:
        with conexion.cursor() as cur:
            cur.execute("SELECT to_regclass('public.usuarios')")
            if cur.fetchone()[0] is None:
                for archivo in sorted(MIGRACIONES.glob("*.sql")):
                    cur.execute(archivo.read_text(encoding="utf-8"))
            # Las sesiones cuelgan de los usuarios con ON DELETE CASCADE, así
            # que borrar usuarios basta. `CASCADE` aquí es del TRUNCATE, no de
            # la clave ajena: hace falta porque `sesiones` referencia a
            # `usuarios`.
            cur.execute("TRUNCATE usuarios RESTART IDENTITY CASCADE")
        conexion.commit()

    _EJECUTADOS.append(request.node.name)
    yield
    base_de_datos.cerrar_pool()


def _mostrador(correo: str = "mostrador@utb.edu.co", contrasena: str = "clave-de-prueba-larga"):
    return cuentas.crear_usuario(
        correo=correo,
        contrasena=contrasena,
        rol="personal_establecimiento",
        establecimiento_id=1,
    )


# ---------------------------------------------------------------------------
# La derivación: funciones puras, sin base de datos
# ---------------------------------------------------------------------------

def test_la_derivacion_nunca_devuelve_la_contrasena():
    """Lo mínimo, y conviene tenerlo escrito.

    Una derivación que contuviera la contraseña sería un cifrado reversible con
    otro nombre. Se comprueba sobre el texto completo porque el formato
    almacenado lleva parámetros y sal en claro, y la aserción tiene que decir
    que **la contraseña** no está, no que el campo tenga cierta forma.
    """
    almacenado = credenciales.derivar("contrasena-muy-reconocible")

    assert "contrasena-muy-reconocible" not in almacenado
    assert almacenado.startswith("scrypt$")


def test_dos_derivaciones_de_la_misma_contrasena_no_coinciden():
    """Cada una lleva su propia sal.

    Sin sal, dos usuarios con la misma contraseña tendrían la misma derivación,
    y una fuga de la tabla revelaría **quiénes comparten contraseña** incluso
    sin romper nada. Además, una tabla precalculada bastaría para todos a la vez.
    """
    primera = credenciales.derivar("la-misma-contrasena")
    segunda = credenciales.derivar("la-misma-contrasena")

    assert primera != segunda
    assert credenciales.coincide("la-misma-contrasena", primera)
    assert credenciales.coincide("la-misma-contrasena", segunda)


@pytest.mark.parametrize(
    "almacenado",
    [
        "",
        "no-tiene-formato",
        "scrypt$solo$tres$campos",
        "scrypt$no-un-numero$8$1$c2Fs$Y2xhdmU=",
        "bcrypt$16384$8$1$c2Fs$Y2xhdmU=",
    ],
    ids=["vacío", "sin separadores", "campos de menos", "N no numérico", "otro algoritmo"],
)
def test_un_hash_con_formato_roto_devuelve_falso_y_no_revienta(almacenado):
    """Un registro corrupto es un intento fallido, no un error 500.

    Importa más de lo que parece: `coincide` se llama en el camino de inicio de
    sesión, y una excepción ahí convertiría una fila mal escrita —o una
    migración a medias— en una caída del endpoint. Devolver `False` deja a ese
    usuario sin poder entrar, que es lo correcto y lo que se puede diagnosticar.
    """
    assert credenciales.coincide("cualquier-cosa", almacenado) is False


def test_el_token_se_guarda_hasheado_y_no_en_claro():
    """`nuevo_token` devuelve el token y su hash, y no son lo mismo.

    La tercera aserción es la que comprueba que el hash es **determinista**, y
    por eso vale: `token_hash` lo calculó `nuevo_token` por dentro y
    `hash_de_token` lo vuelve a calcular aquí, así que son dos cómputos
    independientes de la misma entrada. Sin esa propiedad no se podría buscar
    una sesión por su hash, que es como está indexada la tabla.

    Hubo una cuarta línea comparando `hash_de_token(token)` consigo mismo. No
    añadía nada —la anterior ya cubre lo que pretendía— y era una comparación de
    una expresión contra sí misma, que es lo que marca `python:S5863`. La avisó
    SonarCloud y tenía razón.
    """
    token, token_hash = credenciales.nuevo_token()

    assert token != token_hash
    assert token not in token_hash
    assert credenciales.hash_de_token(token) == token_hash


def test_dos_tokens_seguidos_no_se_repiten():
    """Con `secrets`, no con `random`. Un token predecible no es una credencial."""
    tokens = {credenciales.nuevo_token()[0] for _ in range(50)}

    assert len(tokens) == 50


# ---------------------------------------------------------------------------
# La regla de autorización: una función pura, probada sola
#
# `establecimiento_que_puede_ver` está en `app/autenticacion.py` y no en el
# router precisamente para esto: es la regla de quién opera sobre qué, y poder
# probarla sin montar una petición es la mitad del motivo de haberla sacado de
# allí.
# ---------------------------------------------------------------------------

def _usuario(rol: RolUsuario, establecimiento_id: int | None) -> UsuarioAutenticado:
    return UsuarioAutenticado(
        usuario_id=1,
        correo="alguien@utb.edu.co",
        rol=rol,
        establecimiento_id=establecimiento_id,
    )


def test_el_personal_opera_sobre_el_suyo_lo_pida_o_no():
    personal = _usuario(RolUsuario.PERSONAL_ESTABLECIMIENTO, 1)

    assert establecimiento_que_puede_ver(personal, None) == 1
    assert establecimiento_que_puede_ver(personal, 1) == 1


def test_el_personal_que_pide_otro_recibe_403():
    personal = _usuario(RolUsuario.PERSONAL_ESTABLECIMIENTO, 1)

    with pytest.raises(HTTPException) as e:
        establecimiento_que_puede_ver(personal, 3)

    assert e.value.status_code == 403


def test_el_administrador_opera_sobre_el_que_indique():
    """Puede ver cualquiera, y por eso **tiene que decir cuál**."""
    admin = _usuario(RolUsuario.ADMINISTRADOR, None)

    assert establecimiento_que_puede_ver(admin, 3) == 3


def test_un_administrador_sin_indicar_establecimiento_recibe_422():
    """No se elige uno por él, ni se le devuelven todos.

    Devolver todos sería una ruta distinta con una respuesta distinta, y
    elegirle uno por defecto le haría creer que está viendo el que pensaba. El
    `422` le pide lo único que falta: decir cuál.
    """
    admin = _usuario(RolUsuario.ADMINISTRADOR, None)

    with pytest.raises(HTTPException) as e:
        establecimiento_que_puede_ver(admin, None)

    assert e.value.status_code == 422


@pytest.mark.parametrize("rol", list(RolUsuario), ids=lambda r: r.value)
def test_hoy_los_dos_roles_pueden_operar_el_panel(rol):
    """Y por eso el `403` por rol de `personal_de_establecimiento` es inalcanzable.

    Se comprueba recorriendo el enum entero en vez de marcar esa rama como
    excluida de la cobertura. La diferencia es la que importa: una exclusión
    dice «esto no se prueba» y se queda ahí para siempre; esta prueba dice
    «esto no se puede alcanzar **hoy**», y **falla** el día que alguien añada un
    tercer rol sin decidir si puede operar el panel. Lo que no se quiere es que
    ese tercer rol entre sin que nadie lo piense.
    """
    usuario = _usuario(
        rol, None if rol is RolUsuario.ADMINISTRADOR else 1
    )

    assert personal_de_establecimiento(usuario) is usuario


# ---------------------------------------------------------------------------
# Las cuentas, contra PostgreSQL
# ---------------------------------------------------------------------------

def test_crear_un_usuario_y_autenticarlo(postgres):
    usuario = _mostrador()

    token, autenticado = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")

    assert autenticado.usuario_id == usuario.usuario_id
    assert autenticado.rol is RolUsuario.PERSONAL_ESTABLECIMIENTO
    assert autenticado.establecimiento_id == 1
    assert cuentas.usuario_de_sesion(token).usuario_id == usuario.usuario_id


def test_el_correo_no_distingue_mayusculas_ni_espacios(postgres):
    """Quien escribe su correo con una mayúscula no está escribiendo otro correo.

    Se normaliza al crear y al autenticar. Si solo se normalizara en uno de los
    dos, la cuenta se crearía y su dueño no podría entrar.
    """
    _mostrador(correo="Mostrador@UTB.edu.co")

    token, _ = cuentas.autenticar("  mostrador@utb.edu.co  ", "clave-de-prueba-larga")

    assert token


def test_una_contrasena_incorrecta_y_un_correo_desconocido_dan_el_mismo_error(postgres):
    """El mensaje no puede distinguir los dos casos.

    Si lo hiciera, el formulario sería un oráculo de qué correos están
    registrados: se prueban mil y los que respondan «contraseña incorrecta»
    existen.
    """
    _mostrador()

    with pytest.raises(cuentas.CredencialesInvalidasError) as mala_clave:
        cuentas.autenticar("mostrador@utb.edu.co", "otra-clave-cualquiera")
    with pytest.raises(cuentas.CredencialesInvalidasError) as sin_cuenta:
        cuentas.autenticar("no-existe@utb.edu.co", "otra-clave-cualquiera")

    assert str(mala_clave.value) == str(sin_cuenta.value)


def test_un_correo_desconocido_no_responde_mas_rapido(postgres):
    """La otra mitad de la defensa anterior: el reloj tampoco puede decirlo.

    Sin derivar contra un hash de descarte, un correo inexistente volvería al
    instante y uno existente tardaría los ~100 ms de scrypt. Esa diferencia se
    mide desde fuera incluso con red en medio, y el mensaje idéntico no sirve de
    nada si el tiempo habla.

    El umbral es laxo —la mitad del tiempo de una derivación— porque lo que se
    comprueba no es que los tiempos sean iguales, sino que la diferencia no es
    del orden de una derivación entera. Un margen estrecho haría la prueba
    inestable en CI sin comprobar nada mejor.
    """
    _mostrador()

    def tardanza(correo: str) -> float:
        inicio = time.perf_counter()
        with pytest.raises(cuentas.CredencialesInvalidasError):
            cuentas.autenticar(correo, "una-clave-equivocada")
        return time.perf_counter() - inicio

    existente = min(tardanza("mostrador@utb.edu.co") for _ in range(3))
    inexistente = min(tardanza("no-existe@utb.edu.co") for _ in range(3))

    assert abs(existente - inexistente) < existente / 2, (
        f"Existente: {existente * 1000:.0f} ms · inexistente: "
        f"{inexistente * 1000:.0f} ms. La diferencia revela qué correos están "
        "registrados."
    )


def test_el_correo_repetido_se_rechaza(postgres):
    _mostrador()

    with pytest.raises(cuentas.CorreoYaRegistradoError):
        _mostrador()


def test_una_contrasena_corta_se_rechaza_al_crear(postgres):
    """Al **crear**, con un error que lo explica.

    Al **autenticar** no: ahí una contraseña corta da el mismo `401` que
    cualquier credencial equivocada, porque un error de validación le diría a
    quien prueba que acertó el formato y falló el valor.
    """
    with pytest.raises(cuentas.ContrasenaDebilError):
        cuentas.crear_usuario(
            correo="corta@utb.edu.co",
            contrasena="x" * (cuentas.LONGITUD_MINIMA_CONTRASENA - 1),
            rol="personal_establecimiento",
            establecimiento_id=1,
        )

    assert repository.buscar_usuario_por_correo("corta@utb.edu.co") is None


def test_un_usuario_desactivado_no_puede_entrar(postgres):
    """Y con el mismo error que cualquier otro fallo de credenciales.

    Decir «tu cuenta está desactivada» confirmaría que la cuenta existe, y el
    correo de alguien que trabajó ahí es exactamente lo que no hace falta
    confirmar.
    """
    usuario = _mostrador()
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        conexion.execute(
            "UPDATE usuarios SET activo = false WHERE id = %s", (usuario.usuario_id,)
        )
        conexion.commit()

    with pytest.raises(cuentas.CredencialesInvalidasError):
        cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")


def test_la_restriccion_de_rol_la_impone_la_base_de_datos(postgres):
    """Un administrador atado a un establecimiento no es una fila válida.

    Se escribe **salteando el servicio**, directo en SQL, porque lo que esta
    prueba comprueba es precisamente que la regla no depende de que el servicio
    se acuerde de aplicarla. Es el argumento de ADR-0007 para no usar Supabase
    Auth, hecho comprobable: con los roles en un proveedor externo, esto sería
    código de aplicación que hay que recordar ejecutar.
    """
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexion.execute(
                "INSERT INTO usuarios (establecimiento_id, correo, hash_contrasena, rol)"
                " VALUES (1, 'admin-mal@utb.edu.co', 'x', 'administrador')"
            )
        conexion.rollback()

        with pytest.raises(psycopg.errors.CheckViolation):
            conexion.execute(
                "INSERT INTO usuarios (establecimiento_id, correo, hash_contrasena, rol)"
                " VALUES (NULL, 'personal-mal@utb.edu.co', 'x', 'personal_establecimiento')"
            )
        conexion.rollback()


# ---------------------------------------------------------------------------
# Las sesiones
# ---------------------------------------------------------------------------

def test_un_token_inventado_no_abre_nada(postgres):
    _mostrador()
    cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")

    assert cuentas.usuario_de_sesion("un-token-que-nadie-emitio") is None
    assert cuentas.usuario_de_sesion("") is None


def test_cerrar_sesion_cierra_solo_la_presentada(postgres):
    """Quien entra desde dos navegadores y sale en uno sigue dentro en el otro.

    Es el motivo por el que `cerrar_sesion` recibe el token y no el usuario. Con
    la firma por usuario, salir en el móvil cerraría la sesión del mostrador en
    mitad del turno.
    """
    _mostrador()
    primera, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")
    segunda, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")

    assert cuentas.cerrar_sesion(primera) is True

    assert cuentas.usuario_de_sesion(primera) is None
    assert cuentas.usuario_de_sesion(segunda) is not None


def test_cerrar_una_sesion_que_no_existe_no_es_un_error(postgres):
    """Devuelve `False`, no lanza. Salir dos veces no es un fallo del servidor."""
    assert cuentas.cerrar_sesion("un-token-que-nadie-emitio") is False
    assert cuentas.cerrar_sesion("") is False


#: Envejece una sesión hasta dejarla vencida.
#:
#: Mueve **las dos** fechas, y no solo `expira_en`, porque la tabla tiene
#: `CHECK (expira_en > creada_en)`. El primer intento de escribir esta prueba
#: solo retrasaba `expira_en` y la restricción lo rechazó: una sesión que
#: caduca antes de crearse no es una sesión vencida, es una fila imposible.
#: Lo que queda es además más fiel —una sesión abierta hace nueve horas y
#: vencida hace una— y la restricción se ganó su sitio en la migración.
_ENVEJECER = (
    "UPDATE sesiones"
    "   SET creada_en = now() - interval '9 hours',"
    "       expira_en = now() - interval '1 hour'"
    " WHERE {condicion}"
)


def test_una_sesion_caducada_no_sirve(postgres):
    """Se envejece a mano en SQL en vez de esperar ocho horas.

    La alternativa sería parametrizar las horas para poder pedir una sesión
    vencida, y entonces existiría en el código de producción una forma de abrir
    sesiones que caducan cuando uno quiera. La prueba se adapta al código, no al
    contrario.
    """
    usuario = _mostrador()
    token, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        conexion.execute(
            _ENVEJECER.format(condicion="usuario_id = %s"), (usuario.usuario_id,)
        )
        conexion.commit()

    assert cuentas.usuario_de_sesion(token) is None


def test_la_base_de_datos_rechaza_una_sesion_que_caduca_antes_de_crearse(postgres):
    """La restricción que apareció al escribir la prueba de arriba.

    Vale la pena tenerla aparte: `caduca_despues_de_crearse` es lo que impide
    que un error de aritmética de fechas —restar en vez de sumar las horas de
    sesión— deje en la tabla sesiones nacidas vencidas, que serían un fallo de
    inicio de sesión imposible de explicar mirando el código.
    """
    import psycopg

    _mostrador()
    with psycopg.connect(URL_PRUEBAS) as conexion:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexion.execute(
                "INSERT INTO sesiones (token_hash, usuario_id, creada_en, expira_en)"
                " VALUES ('da-igual', 1, now(), now() - interval '1 hour')"
            )
        conexion.rollback()


def test_borrar_las_caducadas_no_toca_las_vigentes(postgres):
    """La limpieza tiene que ser segura de ejecutar en cualquier momento.

    Si barriera alguna sesión vigente, nadie se atrevería a programarla, y las
    sesiones caducadas se acumularían para siempre en la tabla.
    """
    usuario = _mostrador()
    vencida, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")
    vigente, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        conexion.execute(
            _ENVEJECER.format(condicion="token_hash = %s"),
            (credenciales.hash_de_token(vencida),),
        )
        conexion.commit()

    borradas = repository.borrar_sesiones_caducadas()

    assert borradas == 1
    assert cuentas.usuario_de_sesion(vigente).usuario_id == usuario.usuario_id


def test_borrar_el_usuario_arrastra_sus_sesiones(postgres):
    """`ON DELETE CASCADE`, y no limpieza desde el servicio.

    Una sesión huérfana apuntando a un usuario que ya no existe es una fila que
    nadie sabe interpretar. Dejar que la base de datos lo garantice es lo mismo
    que se hace con la restricción de rol: la regla vive donde no se puede
    olvidar.
    """
    usuario = _mostrador()
    token, _ = cuentas.autenticar("mostrador@utb.edu.co", "clave-de-prueba-larga")
    import psycopg

    with psycopg.connect(URL_PRUEBAS) as conexion:
        conexion.execute("DELETE FROM usuarios WHERE id = %s", (usuario.usuario_id,))
        conexion.commit()

    assert cuentas.usuario_de_sesion(token) is None


# ---------------------------------------------------------------------------
# El recorrido por HTTP: entrar, operar, salir
#
# Lo que falta aquí no es redundante con lo de arriba. Lo de arriba prueba el
# servicio; esto prueba **la frontera**, que es lo único que el panel toca: los
# códigos de estado, la cabecera `WWW-Authenticate`, qué sale en el cuerpo y
# qué no. Se descubrió que faltaba midiendo cobertura: `usuarios/router.py`
# estaba al 65 % con todas las demás pruebas en verde.
# ---------------------------------------------------------------------------

def test_el_recorrido_completo_por_http(postgres):
    """Entrar, usar el token, salir, y comprobar que ya no sirve."""
    from fastapi.testclient import TestClient

    from app.main import app

    _mostrador()
    cliente = TestClient(app)

    apertura = cliente.post(
        "/v1/sesiones",
        json={"correo": "mostrador@utb.edu.co", "contrasena": "clave-de-prueba-larga"},
    )
    assert apertura.status_code == 201
    token = apertura.json()["token"]

    cabecera = {"Authorization": f"Bearer {token}"}
    cola = cliente.get("/v1/pedidos", headers=cabecera)
    assert cola.status_code == 200
    assert cola.json()["establecimiento_id"] == 1

    assert cliente.delete("/v1/sesiones", headers=cabecera).status_code == 204

    # Y a partir de ahí el token es papel mojado.
    assert cliente.get("/v1/pedidos", headers=cabecera).status_code == 401


def test_la_respuesta_de_apertura_no_lleva_la_derivacion_de_la_contrasena(postgres):
    """Lo que no se publica no se puede filtrar por descuido.

    El cuerpo lleva el token y el usuario; `hash_contrasena` no aparece porque
    `UsuarioAutenticado` no lo tiene. La prueba vigila que nadie «enriquezca»
    ese esquema más adelante: es el tipo de campo que se añade por comodidad en
    un depurador y se queda.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    _mostrador()
    cuerpo = TestClient(app).post(
        "/v1/sesiones",
        json={"correo": "mostrador@utb.edu.co", "contrasena": "clave-de-prueba-larga"},
    ).json()

    assert set(cuerpo) == {"token", "usuario"}
    assert "hash_contrasena" not in cuerpo["usuario"]
    assert "contrasena" not in cuerpo["usuario"]


@pytest.mark.parametrize(
    "credenciales_enviadas",
    [
        {"correo": "mostrador@utb.edu.co", "contrasena": "una-clave-equivocada"},
        {"correo": "no-existe@utb.edu.co", "contrasena": "clave-de-prueba-larga"},
        {"correo": "mostrador@utb.edu.co", "contrasena": "corta"},
    ],
    ids=["clave incorrecta", "correo desconocido", "clave demasiado corta"],
)
def test_los_tres_fallos_de_ingreso_dan_401_y_no_422(postgres, credenciales_enviadas):
    """Los tres, con el mismo código y el mismo mensaje.

    El tercero es el que importa y el que se escapa fácil: `IniciarSesionRequest`
    **no** declara longitud mínima a propósito. Si la declarara, una contraseña
    corta daría `422` y quien prueba sabría que acertó el formato y falló el
    valor. El mínimo se aplica al **crear** la cuenta, donde sí hay que
    explicarlo.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    _mostrador()
    respuesta = TestClient(app).post("/v1/sesiones", json=credenciales_enviadas)

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Correo o contraseña incorrectos."
    # La especificación de HTTP la exige: sin ella, el cliente no sabe qué tipo
    # de credencial se le está pidiendo.
    assert respuesta.headers["WWW-Authenticate"] == "Bearer"


def test_cerrar_sesion_sin_sesion_da_401_y_no_204(postgres):
    """Un `204` a quien no presentó nada sería ruido inútil en los logs.

    Y algo peor: le diría a quien manda cadenas al azar que el servidor acepta
    cualquiera, lo que invita a seguir probando.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    cliente = TestClient(app)

    assert cliente.delete("/v1/sesiones").status_code == 401
    assert cliente.delete(
        "/v1/sesiones", headers={"Authorization": "Bearer inventado"}
    ).status_code == 401


@pytest.mark.parametrize(
    "cabecera",
    ["", "Bearer", "Basic dXN1YXJpbzpjbGF2ZQ==", "soloeltoken", "Bearer  "],
    ids=["vacía", "sin token", "otro esquema", "sin esquema", "token en blanco"],
)
def test_una_cabecera_malformada_es_un_401_y_no_un_422(postgres, cabecera):
    """Una credencial que no se entiende es una petición no autenticada.

    No un error de forma: `422` diría que la petición está mal construida, y lo
    que está mal es que no trae con qué entrar. Por eso la cabecera se lee de
    `Request` y no se declara con `Header(...)`, que además haría que FastAPI
    anunciara un `422` imposible en el contrato (ADR-0007).
    """
    from fastapi.testclient import TestClient

    from app.main import app

    respuesta = TestClient(app).get("/v1/pedidos", headers={"Authorization": cabecera})

    assert respuesta.status_code == 401


# ---------------------------------------------------------------------------
# El guion que da de alta a quien atiende
#
# No hay usuarios en ninguna migración, y es la lección de V-11: sembrarlos
# exigiría poner una contraseña —o su derivación— en el repositorio, que es
# exactamente la forma del defecto de la semana 9.
#
# La contrapartida es que el alta pasa por un guion, y un guion que nadie
# ejecuta en la construcción se rompe en silencio. Pasó: `crear_usuario.py`
# imprimía `usuario.id` sobre un objeto cuyo campo se llama `usuario_id`, así
# que **creaba la cuenta y después reventaba**. Quien lo ejecutara vería un
# traceback, supondría que falló y al reintentar recibiría «ya hay una cuenta
# con ese correo», sin saber que la suya ya estaba creada.
# ---------------------------------------------------------------------------

def test_el_guion_de_alta_funciona_de_principio_a_fin(postgres, monkeypatch, capsys):
    """Lo ejecuta con las entradas simuladas y comprueba que termina bien."""
    import importlib

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    respuestas = iter(["nuevo@utb.edu.co", "personal_establecimiento", "2"])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))
    monkeypatch.setattr("getpass.getpass", lambda *_: "clave-de-prueba-larga")

    guion = importlib.import_module("scripts.crear_usuario")

    assert guion.main() == 0

    # Lo que imprime importa: es la única confirmación que recibe quien lo corre.
    salida = capsys.readouterr().out
    assert "nuevo@utb.edu.co" in salida
    assert "personal_establecimiento" in salida

    creado = repository.buscar_usuario_por_correo("nuevo@utb.edu.co")
    assert creado is not None
    assert creado.establecimiento_id == 2
    # Y la contraseña quedó derivada, no guardada.
    assert "clave-de-prueba-larga" not in creado.hash_contrasena


@pytest.mark.parametrize(
    "respuestas, salida_esperada",
    [
        (["cierra@utb.edu.co", "personal_establecimiento", "1"], 0),
        (["cierra@utb.edu.co", "rol_inventado"], 2),
    ],
    ids=["camino feliz", "falla a mitad"],
)
def test_el_guion_de_alta_cierra_el_pool(postgres, monkeypatch, respuestas, salida_esperada):
    """Salga bien o mal, al terminar no quedan hilos del pool vivos.

    El síntoma era cosmético y aun así importaba: `psycopg_pool` se queja al
    apagar el intérprete con cuatro `couldn't stop thread ...`, y eso aparecía
    **después** del «Usuario N creado». Quien acababa de tocar la base de datos
    de producción leía «no pude parar» y se preguntaba si la cuenta se había
    escrito. Un aviso alarmante detrás de una operación correcta enseña a
    ignorar los avisos.

    Se comprueba el **mecanismo** —que el pool queda cerrado— y no el mensaje de
    `stderr`. Verificar el mensaje exigiría lanzar el guion como subproceso, y
    ahí `getpass` lee de la consola y no de `stdin`: sin terminal se queda
    esperando una tecla que no llega. Una prueba que cuelga dos minutos es peor
    que una que mide una capa más abajo.

    El segundo caso es el que justifica el `finally`: si el cierre colgara del
    camino feliz, un fallo a mitad dejaría los hilos igualmente, y encima el
    error de verdad se perdería entre las quejas del apagado.
    """
    import importlib

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    siguientes = iter(respuestas)
    monkeypatch.setattr("builtins.input", lambda *_: next(siguientes))
    monkeypatch.setattr("getpass.getpass", lambda *_: "clave-de-prueba-larga")

    guion = importlib.import_module("scripts.crear_usuario")
    assert guion.main() == salida_esperada

    assert base_de_datos._pool is None, (
        "El guion terminó con el pool abierto: al salir del intérprete, "
        "`psycopg_pool` se quejará de los hilos que quedan vivos."
    )


def test_el_guion_de_alta_rechaza_un_rol_que_no_existe(postgres, monkeypatch):
    """Sin crear nada. Un rol mal escrito no puede dejar media cuenta."""
    import importlib

    monkeypatch.setenv("PIDEUTB_DATABASE_URL", URL_PRUEBAS)
    respuestas = iter(["otro@utb.edu.co", "superadministrador"])
    monkeypatch.setattr("builtins.input", lambda *_: next(respuestas))

    guion = importlib.import_module("scripts.crear_usuario")

    assert guion.main() == 2
    assert repository.buscar_usuario_por_correo("otro@utb.edu.co") is None


# ---------------------------------------------------------------------------
# Que la omisión no se disfrace de éxito
# ---------------------------------------------------------------------------

def test_la_autenticacion_se_probo_contra_postgres():
    """Falla si había PostgreSQL disponible y aun así no se usó.

    Sin esta prueba, un fixture roto —un nombre de variable mal escrito, un
    `skip` que se cuela— dejaría todo el archivo omitido, y el resumen de pytest
    diría «20 skipped» en una línea que nadie lee con detenimiento. Una suite
    que no corre es indistinguible de una que pasa si nadie mira el motivo.

    Cuando no hay base de datos, esta prueba también se omite, y entonces el
    resumen dice la verdad: aquí no se probó la autenticación.
    """
    if not URL_PRUEBAS:
        pytest.skip(
            "Sin PIDEUTB_DATABASE_URL_PRUEBAS. En el pipeline la define un "
            "contenedor efímero, así que allí esto no se omite nunca."
        )

    assert _EJECUTADOS, (
        "`PIDEUTB_DATABASE_URL_PRUEBAS` está definida y ningún caso de "
        "autenticación llegó a correr contra PostgreSQL. El fixture `postgres` "
        "está omitiendo todo: revisá por qué antes de confiar en este archivo."
    )
