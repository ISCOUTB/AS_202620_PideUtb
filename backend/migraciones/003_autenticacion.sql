-- Autenticación del personal de establecimiento.
--
-- Cierra [V-10](../../docs/violaciones.md): hasta ahora cualquiera con el enlace
-- del panel podía mover los pedidos de cualquier establecimiento. La máquina de
-- estados acotaba el daño; no lo impedía.
--
-- Como el resto de migraciones, es aditiva: no borra ni altera nada existente.

BEGIN;

-- ---------------------------------------------------------------------------
-- Roles
--
-- Dos, y solo dos. Un conjunto cerrado y no texto libre, por el mismo motivo
-- que `estado_pedido` (V-08): mientras fuera texto, ningún consumidor podría
-- saber qué valores debe saber tratar, y un rol mal escrito sería un usuario
-- sin permisos en vez de un error.
-- ---------------------------------------------------------------------------

CREATE TYPE rol_usuario AS ENUM (
    'personal_establecimiento',
    'administrador'
);

-- ---------------------------------------------------------------------------
-- Usuarios · contexto Cuentas (ADR-0002: su único escritor)
-- ---------------------------------------------------------------------------

CREATE TABLE usuarios (
    id                 integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- A qué establecimiento pertenece. Nulo solo para administradores, que no
    -- pertenecen a ninguno.
    establecimiento_id integer REFERENCES establecimientos (id),

    correo             text    NOT NULL UNIQUE CHECK (position('@' in correo) > 1),

    -- **Nunca la contraseña**, ni cifrada: su derivación con scrypt. Cifrar
    -- implica poder descifrar, y nadie necesita recuperar una contraseña
    -- original — solo comprobar si la que llega produce la misma derivación.
    hash_contrasena    text    NOT NULL,

    rol                rol_usuario NOT NULL,
    activo             boolean NOT NULL DEFAULT true,
    creado_en          timestamptz NOT NULL DEFAULT now(),

    -- Un miembro del personal sin establecimiento no podría ver nada, y un
    -- administrador atado a uno dejaría de ser administrador. La restricción
    -- impide las dos filas sin sentido.
    CONSTRAINT establecimiento_segun_rol CHECK (
        (rol = 'personal_establecimiento' AND establecimiento_id IS NOT NULL)
        OR (rol = 'administrador' AND establecimiento_id IS NULL)
    )
);

CREATE INDEX usuarios_por_establecimiento ON usuarios (establecimiento_id);

-- ---------------------------------------------------------------------------
-- Sesiones
-- ---------------------------------------------------------------------------

CREATE TABLE sesiones (
    -- **El hash del token, no el token.** Si esta tabla se filtrara, lo que se
    -- lleva el atacante no sirve para entrar: tendría que invertir el hash.
    -- Es el mismo razonamiento que con las contraseñas, aplicado a algo que
    -- también es una credencial aunque dure poco.
    --
    -- Es la clave primaria porque buscar una sesión es buscar por su hash: no
    -- hay otra forma de encontrarla, y eso es deliberado.
    token_hash  text PRIMARY KEY,

    usuario_id  integer NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    creada_en   timestamptz NOT NULL DEFAULT now(),

    -- Sin caducidad, una sesión robada vale para siempre. Con ella, el daño de
    -- una fuga tiene techo.
    expira_en   timestamptz NOT NULL,

    CONSTRAINT caduca_despues_de_crearse CHECK (expira_en > creada_en)
);

-- Para borrar las caducadas sin recorrer la tabla entera.
CREATE INDEX sesiones_por_caducidad ON sesiones (expira_en);

COMMIT;
