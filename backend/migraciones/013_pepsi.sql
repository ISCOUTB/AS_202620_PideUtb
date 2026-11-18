-- La Pepsi de 400 ml.
--
-- La pidió el equipo el 17/11/2026, con su foto y con su precio: el de la
-- Colombiana del mismo tamaño, $3.100. Solo en 400 ml, que es la botella de la
-- foto; a diferencia de los sabores de Postobón, nadie pidió la de 1,5 L.
--
-- Va en su propia migración y no en `012` porque es otra cosa: aquella pone fotos
-- a productos que ya existían, y esta crea uno. Como `010`, es idempotente.

BEGIN;

INSERT INTO menu_items
    (id, establecimiento_id, nombre, precio_centavos, disponible, categoria, descripcion)
OVERRIDING SYSTEM VALUE
VALUES
    (189, 5, 'Gaseosa Pepsi 400 ml', 310000, true, 'Bebidas', 'Gaseosa sabor cola en botella de 400 ml.')
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

-- La foto, en el mismo formato que `009` y `012`: así la ven las pruebas que
-- comprueban que el archivo existe y que el producto también.
UPDATE menu_items SET imagen = foto.ruta
FROM (VALUES
    (189, 'fotos/platos/gaseosa-pepsi.webp')
) AS foto(item_id, ruta)
WHERE menu_items.id = foto.item_id;

COMMIT;
