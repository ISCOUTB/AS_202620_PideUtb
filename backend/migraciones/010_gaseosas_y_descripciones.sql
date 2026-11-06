-- Más gaseosas en la carta, y una descripción para cada producto.
--
-- Como el `005` y el `009`, son **datos de operación**, y por el mismo motivo van
-- en una migración: la base del laboratorio no publica puertos y el panel no da
-- terminal, así que nada más alcanza esa tabla. Es idempotente.
--
-- ### Lo que aquí es un supuesto, dicho sin rodeos
--
-- **Los precios de las gaseosas nuevas no los dio la cafetería.** Cada sabor se
-- vende a lo que hoy vale la Colombiana del mismo tamaño ($3.100 y $5.400), que
-- es lo único que consta. Tampoco consta que tengan todos estos sabores. Un
-- sabor que no haya se marca agotado; un precio distinto se corrige con otra
-- migración.
--
-- **Las descripciones tampoco.** El documento de la cafetería solo trae nombres
-- y precios, así que estas se redactaron mirando el nombre y la foto de cada
-- producto. ADR-0006 rechazó generar descripciones **en tiempo de ejecución**
-- porque inventar un ingrediente puede ser un riesgo de salud, y ese riesgo no
-- desaparece por escribirlas a mano: por eso son cortas, no enumeran recetas ni
-- afirman que algo no contenga nada, y la carta avisa de que son orientativas
-- (`#aviso-alergias`). Hay que validarlas con la cafetería.
--
-- Las gaseosas nuevas no llevan foto: el marcador con la inicial está diseñado
-- para eso, y poner la foto de otra botella sería enseñar otro producto.

BEGIN;

INSERT INTO menu_items
    (id, establecimiento_id, nombre, precio_centavos, disponible, categoria, descripcion)
OVERRIDING SYSTEM VALUE
VALUES
    (183, 5, 'Gaseosa Coca-Cola 400 ml',        310000, true, 'Bebidas', 'Gaseosa sabor cola en botella de 400 ml.'),
    (184, 5, 'Gaseosa Coca-Cola 1,5 L',         540000, true, 'Bebidas', 'Gaseosa sabor cola en botella de 1,5 litros.'),
    (185, 5, 'Gaseosa Postobón Manzana 400 ml', 310000, true, 'Bebidas', 'Gaseosa sabor manzana en botella de 400 ml.'),
    (186, 5, 'Gaseosa Postobón Manzana 1,5 L',  540000, true, 'Bebidas', 'Gaseosa sabor manzana en botella de 1,5 litros.'),
    (187, 5, 'Gaseosa Sprite 400 ml',           310000, true, 'Bebidas', 'Gaseosa sabor lima-limón en botella de 400 ml.'),
    (188, 5, 'Gaseosa Sprite 1,5 L',            540000, true, 'Bebidas', 'Gaseosa sabor lima-limón en botella de 1,5 litros.'),
    (189, 5, 'Gaseosa Fanta 400 ml',            310000, true, 'Bebidas', 'Gaseosa sabor naranja en botella de 400 ml.'),
    (190, 5, 'Gaseosa Fanta 1,5 L',             540000, true, 'Bebidas', 'Gaseosa sabor naranja en botella de 1,5 litros.'),
    (191, 5, 'Gaseosa Pepsi 400 ml',            310000, true, 'Bebidas', 'Gaseosa sabor cola en botella de 400 ml.'),
    (192, 5, 'Gaseosa Pepsi 1,5 L',             540000, true, 'Bebidas', 'Gaseosa sabor cola en botella de 1,5 litros.')
ON CONFLICT (id) DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

UPDATE menu_items SET descripcion = texto.descripcion
FROM (VALUES
    -- Asados
    (101, 'Costillas de cerdo ahumadas con papa y ensalada.'),
    (102, 'Alitas de pollo bañadas en salsa BBQ de tamarindo.'),
    (103, 'Carne de res a la parrilla con papas a la francesa y bebida.'),
    (104, 'Pechuga de pollo a la napolitana.'),
    (105, 'El especial de la casa, con chicharrón.'),
    (106, 'Cerdo a la parrilla con acompañantes.'),
    (107, 'Pollo a la parrilla con acompañantes.'),
    (108, 'Combinación de carnes a la parrilla con acompañantes.'),
    (109, 'Selección de carnes servida en tabla de parrilla.'),
    (110, 'Carne de res a la parrilla con bebida.'),
    (111, 'Patacón cargado con carne, maíz y salsas.'),
    (112, 'La picada de la casa, para compartir.'),

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
