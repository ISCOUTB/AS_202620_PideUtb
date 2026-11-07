-- Más gaseosas en la carta, y una descripción para cada producto.
--
-- Como el `005` y el `009`, son **datos de operación**, y por el mismo motivo van
-- en una migración: la base del laboratorio no publica puertos y el panel no da
-- terminal, así que nada más alcanza esa tabla. Es idempotente.
--
-- ### De dónde sale cada dato
--
-- **Los sabores son los clásicos de Postobón** —Manzana, Uva y Naranja—, que se
-- suman a la Colombiana que ya estaba. Al mismo precio que la Colombiana del mismo
-- tamaño ($3.100 y $5.400): lo confirmó el equipo el 07/11/2026. Un sabor que se
-- acabe se marca agotado.
--
-- **Las descripciones siguen lo que el equipo contó de cada plato.** Todo lo que
-- se llama «asado» lleva lo mismo, cambie la proteína: papitas a la francesa,
-- ensalada, un vaso de jugo, salsa de tomate y chimichurri. Los demás platos
-- fuertes llevan papas a la francesa o papa cocida. El resto se describe por su
-- nombre y su foto.
--
-- ADR-0006 rechazó generar descripciones **en tiempo de ejecución** porque
-- inventar un ingrediente puede ser un riesgo de salud. Por eso estas dicen qué
-- lleva el plato y no qué no lleva, y la carta avisa de que no sustituyen a
-- preguntar en el mostrador por una alergia (`#aviso-alergias`).
--
-- Las gaseosas nuevas no llevan foto: el marcador con la inicial está diseñado
-- para eso, y poner la foto de otra botella sería enseñar otro producto.

BEGIN;

INSERT INTO menu_items
    (id, establecimiento_id, nombre, precio_centavos, disponible, categoria, descripcion)
OVERRIDING SYSTEM VALUE
VALUES
    (183, 5, 'Gaseosa Postobón Manzana 400 ml', 310000, true, 'Bebidas', 'Gaseosa sabor manzana en botella de 400 ml.'),
    (184, 5, 'Gaseosa Postobón Manzana 1,5 L',  540000, true, 'Bebidas', 'Gaseosa sabor manzana en botella de 1,5 litros.'),
    (185, 5, 'Gaseosa Postobón Uva 400 ml',     310000, true, 'Bebidas', 'Gaseosa sabor uva en botella de 400 ml.'),
    (186, 5, 'Gaseosa Postobón Uva 1,5 L',      540000, true, 'Bebidas', 'Gaseosa sabor uva en botella de 1,5 litros.'),
    (187, 5, 'Gaseosa Postobón Naranja 400 ml', 310000, true, 'Bebidas', 'Gaseosa sabor naranja en botella de 400 ml.'),
    (188, 5, 'Gaseosa Postobón Naranja 1,5 L',  540000, true, 'Bebidas', 'Gaseosa sabor naranja en botella de 1,5 litros.')
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

UPDATE menu_items SET descripcion = texto.descripcion
FROM (VALUES
    -- Asados: todo lo que se llama «asado» lleva lo mismo, cambie la proteína.
    (103, 'Carne de res (beef steak) con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),
    (106, 'Carne de cerdo con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),
    (107, 'Pechuga de pollo con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),
    (108, 'Carnes mixtas con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),
    (109, 'Selección de carnes a la parrilla con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),
    (110, 'Carne de res con papitas a la francesa, ensalada, un vaso de jugo, salsa de tomate y chimichurri.'),

    -- Los demás platos fuertes: papas a la francesa o papa cocida.
    (101, 'Costillas de cerdo ahumadas, con papas a la francesa o papa cocida.'),
    (102, 'Alitas de pollo en salsa BBQ de tamarindo, con papas a la francesa o papa cocida.'),
    (104, 'Pechuga de pollo a la napolitana, con papas a la francesa o papa cocida.'),
    (105, 'Chicharrón, el especial de la casa, con papas a la francesa o papa cocida.'),
    (112, 'La picada de la casa, para compartir, con papas a la francesa o papa cocida.'),
    (111, 'Patacón cargado con carne, maíz y salsas.'),

    -- Hamburguesas y perros
    (120, 'Hamburguesa de pollo con papas a la francesa y gaseosa.'),
    (121, 'Hamburguesa de carne con papas a la francesa y gaseosa.'),
    (122, 'Solo la hamburguesa de carne, con vegetales.'),
    (123, 'Solo la hamburguesa de pollo, con vegetales.'),
    (124, 'Salchicha en pan con queso y salsas.'),
    (125, 'Chorizo en pan con tocineta y salsas.'),
    (126, 'Papas a la francesa con salchicha, maíz y salsas.'),

    -- Adiciones y porciones
    (140, 'Butifarra para añadir a tu plato.'),
    (141, 'Chorizo para añadir a tu plato.'),
    (142, 'Queso mozarella para añadir a tu plato.'),
    (143, 'Papa cocida como acompañante.'),
    (144, 'Papas a la francesa como acompañante.'),
    (145, 'Patacones como acompañante.'),
    (146, 'Suero para acompañar.'),

    -- Salsas
    (160, 'Salsa BBQ de la casa.'),
    (161, 'La salsa especial de la casa.'),
    (162, 'Salsa napolitana de la casa.'),
    (163, 'Salsa tártara de la casa.'),
    (164, 'Salsa de tomate.'),
    (165, 'Salsa de hierbas para carnes.'),
    (166, 'Vinagreta para ensaladas y carnes.'),

    -- Bebidas
    (180, 'Agua en botella.'),
    (181, 'Gaseosa sabor kola en botella de 400 ml.'),
    (182, 'Gaseosa sabor kola en botella de 1,5 litros.')
) AS texto(item_id, descripcion)
WHERE menu_items.id = texto.item_id;

COMMIT;
