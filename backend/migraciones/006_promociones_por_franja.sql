-- Promociones válidas solo dentro de una franja horaria del día.
--
-- El Asao tiene dos, ambas de 2:30 a 3:30 de la tarde:
--
--   1. El combo de hamburguesa de pollo baja de 24 200 a 16 500.
--   2. Un combo de perro sencillo con gaseosa de 400 ml por 11 900 que
--      **solo existe en esa franja**.
--
-- Son dos formas distintas y por eso hay dos mecanismos, no uno: una cambia el
-- precio de un producto que se vende todo el día, la otra cambia si el producto
-- se puede pedir. Mezclarlas en una sola columna obligaría a inventar un precio
-- «normal» para algo que no se vende fuera de la promoción.
--
-- ### Qué NO hace esta migración
--
-- No hay tabla de promociones. Son dos, de un establecimiento, con la misma
-- franja y sin fecha de caducidad: una tabla con su propia entidad, su clave
-- ajena y sus consultas no haría nada que estas columnas no hagan, y habría que
-- mantenerla. El día que una promoción necesite fechas, días de la semana o
-- varios productos a la vez, la tabla se justifica sola y esta migración es el
-- punto de partida para escribirla.
--
-- ### La franja no cruza la medianoche, y está impuesto
--
-- `promocion_desde < promocion_hasta` lo prohíbe. Una franja de 23:00 a 01:00
-- se compara al revés —«dentro» deja de ser un intervalo y pasa a ser dos— y
-- cada consulta tendría que acordarse. Si alguna vez hace falta, que falle aquí
-- y se decida entonces, en vez de aceptarla y devolver precios incorrectos
-- durante una noche.
--
-- ### La hora es local, no UTC
--
-- `time` sin zona, y la compara el servicio contra la hora de Bogotá. En UTC,
-- «2:30 de la tarde» sería 19:30 y dejaría de parecerse a lo que el
-- establecimiento anuncia en su cartel; y el día que el servidor cambie de
-- región, lo que no debe moverse es la franja.

BEGIN;

ALTER TABLE menu_items
    ADD COLUMN precio_promocional_centavos integer,
    ADD COLUMN promocion_desde time,
    ADD COLUMN promocion_hasta time,
    -- El producto no se vende fuera de la franja. `disponible` sigue
    -- significando lo de siempre —si el mostrador lo tiene hoy—, y son cosas
    -- distintas: un combo agotado a las 2:45 no está disponible aunque la
    -- franja esté abierta.
    ADD COLUMN solo_en_promocion boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN menu_items.precio_promocional_centavos IS
    'Precio dentro de la franja. Nulo = la franja no cambia el precio.';
COMMENT ON COLUMN menu_items.solo_en_promocion IS
    'El producto solo se puede pedir dentro de la franja.';

-- Las dos horas van juntas o no van: media franja no significa nada.
ALTER TABLE menu_items ADD CONSTRAINT franja_completa CHECK (
    (promocion_desde IS NULL) = (promocion_hasta IS NULL)
);

ALTER TABLE menu_items ADD CONSTRAINT franja_sin_cruzar_medianoche CHECK (
    promocion_desde IS NULL OR promocion_desde < promocion_hasta
);

-- Un precio promocional sin franja no se aplicaría nunca, y un producto que
-- solo se vende en promoción sin franja no se vendería jamás. Las dos son
-- maneras de dejar una promoción muerta sin que nada avise.
ALTER TABLE menu_items ADD CONSTRAINT promocion_necesita_franja CHECK (
    (precio_promocional_centavos IS NULL AND NOT solo_en_promocion)
    OR promocion_desde IS NOT NULL
);

-- Una «promoción» más cara que el precio normal es un error de carga, no una
-- promoción. Se rechaza en la base porque el daño es silencioso: nadie revisa
-- un precio que la carta muestra sin quejarse.
ALTER TABLE menu_items ADD CONSTRAINT promocion_no_encarece CHECK (
    precio_promocional_centavos IS NULL
    OR precio_promocional_centavos < precio_centavos
);

ALTER TABLE menu_items ADD CONSTRAINT promocion_positiva CHECK (
    precio_promocional_centavos IS NULL OR precio_promocional_centavos > 0
);

-- 1. El combo de pollo baja de precio en la franja.
UPDATE menu_items
SET precio_promocional_centavos = 1650000,
    promocion_desde = '14:30',
    promocion_hasta = '15:30'
WHERE id = 120;

-- 2. El combo de perro sencillo con gaseosa, que solo existe en la franja.
--
-- `precio_promocional_centavos` queda nulo a propósito: 11 900 no es un
-- descuento sobre nada, es su único precio. Lo que la franja decide aquí es si
-- se puede pedir, no cuánto cuesta.
INSERT INTO menu_items
    (id, establecimiento_id, nombre, precio_centavos, disponible, categoria,
     descripcion, promocion_desde, promocion_hasta, solo_en_promocion)
OVERRIDING SYSTEM VALUE
VALUES
    (127, 5, 'Combo perro sencillo + gaseosa 400 ml', 1190000, true,
     'Hamburguesas y perros', 'Perro sencillo con gaseosa de 400 ml',
     '14:30', '15:30', true)
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

COMMIT;
