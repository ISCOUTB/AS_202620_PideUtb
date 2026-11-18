-- La porción de salsa de tomate vuelve a $600.
--
-- `014` la subió a $6.000 porque así se leía en el documento de la cafetería
-- («$ 6000», sin punto de miles). El equipo lo confirmó el 18/11/2026: son
-- $600, que es lo que ya había cargado `005` y lo que cuadra con las demás
-- salsas.
--
-- `014` ya está aplicada, así que no se edita: la corrección va aquí. Su
-- comentario sobre la salsa queda desactualizado, y es esta migración la que
-- dice el precio bueno.
--
-- Los pedidos hechos mientras costó $6.000 conservan ese precio (V-06).

BEGIN;

UPDATE menu_items SET precio_centavos = 60000 WHERE id = 164;

COMMIT;
