-- Esquema inicial de PideUTB.
--
-- Cada migración es aditiva y no se edita después de aplicarse: el rollback de
-- base de datos es el punto débil declarado de esta arquitectura, porque la
-- capa gratuita de Supabase no incluye copias automáticas
-- (`docs/comparacion-despliegue.md` §9). Con migraciones aditivas, revertir el
-- código basta; con migraciones destructivas, no habría vuelta atrás.
--
-- Este archivo usa a propósito las tres primitivas con las que
-- `comparacion-despliegue.md` §1.1 justificó elegir PostgreSQL sobre MySQL:
-- tipos ENUM nativos, restricciones CHECK declarativas y, en el código,
-- INSERT ... ON CONFLICT.

BEGIN;

-- ---------------------------------------------------------------------------
-- Tipos enumerados
--
-- Nativos del motor, no cadenas con convención. Un valor fuera del conjunto es
-- un error en el momento de escribir, no un dato malo descubierto tres meses
-- después. Deben coincidir con los `enum` de `app/pedidos/contracts.py` y
-- `app/pagos/contracts.py`, y que coincidan lo verifica
-- `tests/test_esquema_base_de_datos.py`.
-- ---------------------------------------------------------------------------

CREATE TYPE estado_pedido AS ENUM (
    'pendiente_pago',
    'pagado',
    'en_preparacion',
    'listo_para_recoger',
    'entregado',
    'cancelado'
);

CREATE TYPE estado_pago AS ENUM (
    'pendiente',
    'aprobado',
    'rechazado'
);

CREATE TYPE metodo_pago AS ENUM (
    'tarjeta',
    'nequi',
    'pse'
);

-- ---------------------------------------------------------------------------
-- Contexto Cuentas · único escritor de `establecimientos` (ADR-0002)
-- ---------------------------------------------------------------------------

CREATE TABLE establecimientos (
    id         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre     text    NOT NULL CHECK (length(trim(nombre)) > 0),
    ubicacion  text    NOT NULL,
    horario    text    NOT NULL,
    activo     boolean NOT NULL DEFAULT true,
    creado_en  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Contexto Catálogo
-- ---------------------------------------------------------------------------

CREATE TABLE menu_items (
    id                 integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    establecimiento_id integer NOT NULL REFERENCES establecimientos (id),
    nombre             text    NOT NULL CHECK (length(trim(nombre)) > 0),

    -- El dinero es un entero en centavos y la unidad va en el nombre de la
    -- columna (V-07). Nunca `numeric` ni `float`: el primero invita a redondeos
    -- implícitos y el segundo los garantiza.
    precio_centavos    integer NOT NULL CHECK (precio_centavos >= 0),

    disponible         boolean NOT NULL DEFAULT true
);

-- La carta se consulta por establecimiento en cada visita a la portada, y es la
-- consulta más frecuente del sistema.
CREATE INDEX menu_items_por_establecimiento ON menu_items (establecimiento_id, id);

-- ---------------------------------------------------------------------------
-- Contexto Pedidos
-- ---------------------------------------------------------------------------

CREATE TABLE pedidos (
    id                       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    establecimiento_id       integer NOT NULL REFERENCES establecimientos (id),
    item_id                  integer NOT NULL REFERENCES menu_items (id),

    -- Instantánea del ítem en el momento del pedido, no una referencia viva
    -- (V-06). Si mañana sube el precio de la arepa, este pedido sigue valiendo
    -- lo que valía: el importe cobrado tiene que ser auditable sin reconstruir
    -- el histórico del catálogo.
    nombre_item              text    NOT NULL,
    precio_unitario_centavos integer NOT NULL CHECK (precio_unitario_centavos >= 0),

    cantidad                 integer NOT NULL CHECK (cantidad BETWEEN 1 AND 50),
    total_centavos           integer NOT NULL CHECK (total_centavos >= 0),
    estado                   estado_pedido NOT NULL DEFAULT 'pendiente_pago',

    -- Nulo mientras el pago no se confirma. La restricción de abajo impide que
    -- exista un código sin pago detrás.
    codigo_canje             text UNIQUE,

    creado_en                timestamptz NOT NULL DEFAULT now(),
    actualizado_en           timestamptz NOT NULL DEFAULT now(),

    -- El total tiene que ser coherente con sus factores. Sin esto, un error de
    -- cálculo en el código escribiría un importe cobrable que nadie detectaría.
    CONSTRAINT total_coherente
        CHECK (total_centavos = precio_unitario_centavos * cantidad),

    -- **La restricción que más protege.** Un pedido sin pagar no puede tener
    -- código de canje, y uno pagado tiene que tenerlo. Es ESC-04 expresado en
    -- el motor: aunque un fallo del código intentara emitir un código antes de
    -- cobrar, la base de datos rechaza la escritura.
    CONSTRAINT codigo_solo_tras_el_pago CHECK (
        (estado = 'pendiente_pago' AND codigo_canje IS NULL)
        OR (estado = 'cancelado')
        OR (estado <> 'pendiente_pago' AND codigo_canje IS NOT NULL)
    )
);

CREATE INDEX pedidos_por_establecimiento ON pedidos (establecimiento_id, id DESC);

-- ---------------------------------------------------------------------------
-- Contexto Pagos
-- ---------------------------------------------------------------------------

CREATE TABLE pagos_intentos (
    referencia_pago text    PRIMARY KEY,
    pedido_id       integer NOT NULL REFERENCES pedidos (id),
    monto_centavos  integer NOT NULL CHECK (monto_centavos >= 0),
    metodo          metodo_pago NOT NULL,
    estado_pago     estado_pago NOT NULL DEFAULT 'pendiente',

    -- La URL a la que se manda al usuario. Se guarda porque el frontend puede
    -- volver a pedir el intento pendiente de un pedido y necesita reenviarlo
    -- al mismo sitio, no abrir un cobro nuevo.
    url_checkout    text    NOT NULL,

    creado_en       timestamptz NOT NULL DEFAULT now()
);

-- Hace idempotente a `iniciar_intento`: con este índice, pulsar «Pagar» dos
-- veces no abre dos cobros sobre el mismo pedido, porque el segundo `INSERT`
-- choca y `ON CONFLICT DO NOTHING` lo descarta.
--
-- Es parcial —solo sobre los pendientes— a propósito: un pedido sí puede
-- acumular varios intentos resueltos si el primero fue rechazado y el usuario
-- reintentó con otro método.
CREATE UNIQUE INDEX un_solo_intento_pendiente_por_pedido
    ON pagos_intentos (pedido_id)
    WHERE estado_pago = 'pendiente';

COMMIT;
