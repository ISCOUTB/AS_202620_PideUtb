-- Carrito de varias líneas, y un catálogo con imagen y categoría.
--
-- Como toda migración de este proyecto, es **aditiva y no se edita después de
-- aplicarse**: el rollback de base de datos es el punto débil declarado de
-- esta arquitectura, porque no hay copias automáticas. Con migraciones
-- aditivas, revertir el código basta.
--
-- ### Por qué hacía falta tocar el esquema
--
-- Hasta aquí un pedido **era** una línea, y la base lo imponía:
--
--     CHECK (total_centavos = precio_unitario_centavos * cantidad)
--
-- Esa restricción es correcta mientras un pedido tenga un solo producto, y
-- hace imposible que tenga dos. Un carrito no es una pantalla: es un cambio
-- de modelo.
--
-- ### Qué se hace con las cuatro columnas viejas
--
-- `item_id`, `nombre_item`, `precio_unitario_centavos` y `cantidad` **no se
-- borran**. Pasan a admitir nulo y quedan como histórico de los pedidos
-- creados antes de este cambio.
--
-- Borrarlas sería más limpio de leer y rompería la propiedad que hace segura
-- a esta arquitectura: que revertir el código baste para volver atrás. Una
-- columna borrada no vuelve con un `git revert`.
--
-- Se marcan con un comentario en la propia base para que quien las encuentre
-- sepa que no debe escribirlas.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1 · Las líneas del pedido
-- ---------------------------------------------------------------------------
--
-- Cada línea guarda su propia instantánea del nombre y del precio, por el
-- mismo motivo que ya lo hacía `pedidos` (V-06): si mañana sube el precio de
-- la arepa, este pedido sigue valiendo lo que valía. El importe cobrado tiene
-- que ser auditable sin reconstruir el histórico del catálogo.

CREATE TABLE pedido_lineas (
    id                       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- `ON DELETE CASCADE`: las líneas no tienen vida propia. Un pedido
    -- borrado no puede dejar líneas huérfanas que cuadren con nada.
    pedido_id                integer NOT NULL REFERENCES pedidos (id) ON DELETE CASCADE,

    item_id                  integer NOT NULL REFERENCES menu_items (id),

    -- La instantánea, igual que en `pedidos`.
    nombre_item              text    NOT NULL CHECK (length(trim(nombre_item)) > 0),
    precio_unitario_centavos integer NOT NULL CHECK (precio_unitario_centavos >= 0),
    cantidad                 integer NOT NULL CHECK (cantidad BETWEEN 1 AND 50),
    total_linea_centavos     integer NOT NULL CHECK (total_linea_centavos >= 0),

    -- El total de la línea sí es un producto exacto. Lo que deja de serlo es
    -- el total del pedido, que ahora es una suma.
    CONSTRAINT total_de_linea_coherente
        CHECK (total_linea_centavos = precio_unitario_centavos * cantidad),

    -- El mismo producto no se repite en dos líneas del mismo pedido: se
    -- aumenta su cantidad. Sin esto, «2 arepas» y «1 arepa» podrían convivir
    -- en el mismo pedido y el mostrador vería dos renglones de lo mismo.
    CONSTRAINT un_item_una_vez_por_pedido UNIQUE (pedido_id, item_id)
);

-- La consulta que más se hace: todas las líneas de un pedido.
CREATE INDEX pedido_lineas_por_pedido ON pedido_lineas (pedido_id);

-- ---------------------------------------------------------------------------
-- 2 · Los pedidos que ya existen pasan a tener una línea
-- ---------------------------------------------------------------------------
--
-- Va antes de relajar las restricciones a propósito: si algo fallara aquí, la
-- transacción se revierte con el esquema viejo todavía íntegro.

INSERT INTO pedido_lineas (
    pedido_id, item_id, nombre_item, precio_unitario_centavos, cantidad,
    total_linea_centavos
)
SELECT id, item_id, nombre_item, precio_unitario_centavos, cantidad,
       precio_unitario_centavos * cantidad
FROM pedidos;

-- ---------------------------------------------------------------------------
-- 3 · El total del pedido deja de ser un producto y pasa a ser una suma
-- ---------------------------------------------------------------------------

-- Se quita **solo** `total_coherente`, que es la que ataba el total a un único
-- producto. El `CHECK (total_centavos >= 0)` de la columna sigue en pie y
-- sigue siendo cierto: no se toca.
ALTER TABLE pedidos DROP CONSTRAINT total_coherente;

-- Y a cambio, el total tiene que cuadrar con la suma de sus líneas. No se
-- puede expresar como CHECK —una restricción de fila no ve otra tabla— así
-- que lo impone un disparador, que es el equivalente honesto.
CREATE FUNCTION pedido_total_cuadra() RETURNS trigger AS $$
DECLARE
    suma integer;
    objetivo integer;
BEGIN
    SELECT COALESCE(SUM(total_linea_centavos), 0) INTO suma
    FROM pedido_lineas WHERE pedido_id = COALESCE(NEW.pedido_id, OLD.pedido_id);

    SELECT total_centavos INTO objetivo
    FROM pedidos WHERE id = COALESCE(NEW.pedido_id, OLD.pedido_id);

    IF objetivo IS NOT NULL AND suma <> objetivo THEN
        RAISE EXCEPTION
            'El total del pedido % es % y sus lineas suman %',
            COALESCE(NEW.pedido_id, OLD.pedido_id), objetivo, suma;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- `DEFERRABLE INITIALLY DEFERRED`: el pedido y sus líneas se escriben en la
-- misma transacción, y entre una escritura y la siguiente el total no cuadra
-- por definición. Comprobarlo al cerrar la transacción y no en cada fila es
-- lo que permite que insertar un carrito sea posible.
CREATE CONSTRAINT TRIGGER lineas_cuadran_con_el_total
    AFTER INSERT OR UPDATE OR DELETE ON pedido_lineas
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION pedido_total_cuadra();

-- ---------------------------------------------------------------------------
-- 4 · Las columnas de línea en `pedidos` quedan como histórico
-- ---------------------------------------------------------------------------

ALTER TABLE pedidos ALTER COLUMN item_id                  DROP NOT NULL;
ALTER TABLE pedidos ALTER COLUMN nombre_item              DROP NOT NULL;
ALTER TABLE pedidos ALTER COLUMN precio_unitario_centavos DROP NOT NULL;
ALTER TABLE pedidos ALTER COLUMN cantidad                 DROP NOT NULL;

COMMENT ON COLUMN pedidos.item_id IS
    'Histórico: anterior al carrito (migración 004). No escribir. Las líneas viven en pedido_lineas.';
COMMENT ON COLUMN pedidos.nombre_item IS
    'Histórico: anterior al carrito (migración 004). No escribir.';
COMMENT ON COLUMN pedidos.precio_unitario_centavos IS
    'Histórico: anterior al carrito (migración 004). No escribir.';
COMMENT ON COLUMN pedidos.cantidad IS
    'Histórico: anterior al carrito (migración 004). No escribir.';

-- ---------------------------------------------------------------------------
-- 5 · El catálogo gana imagen, categoría y descripción
-- ---------------------------------------------------------------------------
--
-- Las tres admiten nulo porque los productos que ya existen no las tienen, y
-- porque un catálogo sin foto tiene que seguir funcionando: la interfaz
-- muestra un marcador, no una imagen rota.

ALTER TABLE menu_items ADD COLUMN imagen      text;
ALTER TABLE menu_items ADD COLUMN categoria   text;
ALTER TABLE menu_items ADD COLUMN descripcion text;

COMMENT ON COLUMN menu_items.imagen IS
    'Ruta relativa dentro del sitio, p. ej. imagenes/arepa-de-huevo.webp. Nulo = marcador.';
COMMENT ON COLUMN menu_items.categoria IS
    'Agrupación para los filtros de la carta. Nulo = aparece solo en «Todas».';

-- Los filtros de la carta consultan por categoría dentro de un
-- establecimiento.
CREATE INDEX menu_items_por_categoria
    ON menu_items (establecimiento_id, categoria);

-- Los dos productos de la semilla reciben su categoría. La imagen se queda
-- nula a propósito: hasta que existan los archivos, el marcador es la
-- respuesta honesta.
UPDATE menu_items SET categoria = 'Asados'  WHERE nombre = 'Arepa de huevo';
UPDATE menu_items SET categoria = 'Bebidas' WHERE nombre = 'Jugo de mango';

COMMIT;
