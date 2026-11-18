-- Tres precios que no coincidían con el documento de la cafetería.
--
-- `009` dice que los precios del documento «coinciden con los del `005`». Tres no
-- coincidían, y como `005` y `009` ya están aplicadas, se corrigen aquí:
--
-- | Producto | Documento | Había |
-- |---|---|---|
-- | Gaseosa Colombiana 400 ml | $3.200 | $3.100 |
-- | Porción de salsa de tomate | $6.000 | $600 |
-- | Porción de butifarras | $5.200 | $2.200 |
--
-- ### Las gaseosas de 400 ml suben con la Colombiana
--
-- Manzana, Uva, Naranja (`010`) y la Pepsi (`013`) se pusieron «al precio de la
-- Colombiana del mismo tamaño»: así lo pidió el equipo. Si la Colombiana sube,
-- ellas también. Las de 1,5 L no cambian: ahí el documento ya decía $5.400.
--
-- ### La butifarra era una porción
--
-- `005` la cargó como «Adición butifarra», pero el documento la vende como
-- **porción**, y a $5.200 una «adición» sería la más cara de la lista. Pasa a
-- llamarse como las demás porciones. La foto no cambia: es la del documento.
--
-- ### Los pedidos ya hechos no cambian
--
-- Cada línea de pedido guarda el precio con el que se pidió (V-06). Esto solo
-- afecta a los pedidos que se hagan a partir de aquí.

BEGIN;

UPDATE menu_items SET precio_centavos = nuevo.precio
FROM (VALUES
    -- Gaseosas de 400 ml
    (181, 320000),
    (183, 320000),
    (185, 320000),
    (187, 320000),
    (189, 320000),

    -- Porciones
    (164, 600000),
    (140, 520000)
) AS nuevo(item_id, precio)
WHERE menu_items.id = nuevo.item_id;

UPDATE menu_items
SET nombre = 'Porción butifarra',
    descripcion = 'Butifarras como acompañante.'
WHERE id = 140;

COMMIT;
