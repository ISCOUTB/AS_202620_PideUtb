-- Las fotos que faltaban en la carta de El Asao.
--
-- `009` dejó 12 productos sin foto porque la cafetería no las había mandado, y
-- `010` sumó seis gaseosas sin foto. Esta migración le pone foto a 17 de esas 18.
-- Es idempotente, por lo mismo que `009`.
--
-- ### De dónde sale cada una
--
-- **Doce las mandó el equipo**, con nombres que dicen de qué producto son:
-- pechuga napolitana, picada, combo y hamburguesa sencilla de pollo, asado de
-- carne con bebida, adición de chorizo y de queso, salsas BBQ y napolitana, y la
-- gaseosa de manzana. La de manzana va en los dos tamaños: es la misma bebida.
--
-- **Una se rehízo.** La del combo de perro y gaseosa llegó con la marca de agua
-- de un banco de imágenes —era la vista previa, no una foto con licencia—, así
-- que no se usó. La miniatura se compuso con dos fotos que la cafetería ya había
-- mandado: la del perro caliente y la de la Colombiana de 400 ml.
--
-- **Tres salen de bancos con licencia libre**, porque el equipo pidió buscar las
-- que faltaran: el chicharrón (Wikimedia Commons) y las gaseosas de uva y de
-- naranja (Open Food Facts). Las tres son CC BY-SA, piden atribución, y la tienen
-- en `sitio/fotos/LEEME.md`. Las de uva y naranja van, igual que la de manzana,
-- en los dos tamaños.
--
-- ### La que sigue sin foto
--
-- La **salsa de la casa**. Nadie sabe de qué color es, y cualquier foto sería
-- inventarse la salsa. Sigue con el marcador de la inicial.

BEGIN;

UPDATE menu_items SET imagen = foto.ruta
FROM (VALUES
    -- Asados
    (104, 'fotos/platos/pechuga-napolitana.webp'),
    (105, 'fotos/platos/especial-chicharron.webp'),
    (110, 'fotos/platos/asado-de-carne-con-bebida.webp'),
    (112, 'fotos/platos/picada-el-asao.webp'),

    -- Hamburguesas y perros
    (120, 'fotos/platos/combo-hamburguesa-pollo.webp'),
    (123, 'fotos/platos/hamburguesa-sencilla-pollo.webp'),
    (127, 'fotos/platos/combo-perro-gaseosa.webp'),

    -- Adiciones
    (141, 'fotos/platos/adicion-chorizo.webp'),
    (142, 'fotos/platos/adicion-queso-mozarella.webp'),

    -- Salsas
    (160, 'fotos/platos/porcion-salsa-bbq.webp'),
    (162, 'fotos/platos/porcion-salsa-napolitana.webp'),

    -- Bebidas
    (183, 'fotos/platos/gaseosa-postobon-manzana.webp'),
    (184, 'fotos/platos/gaseosa-postobon-manzana.webp'),
    (185, 'fotos/platos/gaseosa-postobon-uva.webp'),
    (186, 'fotos/platos/gaseosa-postobon-uva.webp'),
    (187, 'fotos/platos/gaseosa-postobon-naranja.webp'),
    (188, 'fotos/platos/gaseosa-postobon-naranja.webp')
) AS foto(item_id, ruta)
WHERE menu_items.id = foto.item_id;

COMMIT;
