-- La carta de El Asao.
--
-- **Esto son datos de operación, no datos semilla.** La diferencia importa para
-- quien lea esta carpeta: los cuatro establecimientos y los cuatro ítems de
-- `002` existen cada uno para hacer comprobable una regla —uno agotado, uno de
-- un establecimiento inactivo, uno sin carta—, y por eso están escritos en las
-- pruebas. Estas 36 filas no prueban nada: son la lista de precios real de un
-- punto de venta.
--
-- ### Por qué una migración y no un script de carga
--
-- Un catálogo real pertenece a un cargador: se vuelve a ejecutar cuando suben
-- los precios y no deja una migración por cada cambio. **Aquí no se puede.** La
-- base del laboratorio no publica puertos y el panel no da terminal, así que
-- nada ejecutable alcanza producción — es el mismo motivo por el que la primera
-- cuenta del mostrador se crea con variables de entorno y no con
-- `crear_usuario.py`.
--
-- La consecuencia hay que decirla entera: **cuando la cafetería cambie un
-- precio hará falta otra migración.** Es el coste de no tener acceso, no una
-- elección. El día que lo haya, lo que sigue aquí se convierte en el primer
-- archivo que lea un cargador.
--
-- ### Por qué un establecimiento nuevo y no la carta del 1
--
-- El Asao es una fracción de la cafetería **con su propio mostrador**, y en
-- este sistema un establecimiento es exactamente eso: un punto de venta con su
-- carta y su cola. Modelarlo como tal deja intactos los cuatro casos de prueba
-- del `002`, que de otro modo habría que reescribir sin ganar nada.
--
-- Es idempotente, como el `002`: aplicarla dos veces no duplica nada.

BEGIN;

-- El horario dice «por confirmar» a propósito. No lo sé, y escribir uno
-- inventado lo convertiría en un dato que alguien da por cierto. Lo único que
-- consta es que a las 14:30 está abierto, porque ahí cae su promoción.
INSERT INTO establecimientos (id, nombre, ubicacion, horario, activo)
OVERRIDING SYSTEM VALUE
VALUES
    (5, 'El Asao', 'Cafetería central, zona de asados', 'horario por confirmar', true)
ON CONFLICT (id) DO NOTHING;

-- Los nombres van en mayúscula inicial y con las erratas del listado original
-- corregidas —«POPCION», «SALASA», «STEACK», un «CON BEBI» truncado—. Los
-- precios **no se tocan**: son los de la lista, multiplicados por 100 porque el
-- sistema guarda centavos y no decimales (V-07).
--
-- El nombre original va en el comentario de cada fila que cambió, para que
-- quien compare esta carta con el tirón del punto de venta encuentre la
-- correspondencia sin adivinar.
INSERT INTO menu_items
    (id, establecimiento_id, nombre, precio_centavos, disponible, categoria)
OVERRIDING SYSTEM VALUE
VALUES
    -- Asados
    (101, 5, 'Costillitas de cerdo ahumadas',        2980000, true, 'Asados'),
    (102, 5, 'Alitas en BBQ de tamarindo',           2240000, true, 'Asados'),
    (103, 5, 'Asado de carne beef steak con bebida', 3340000, true, 'Asados'),  -- ASADO DE CARNE BEEF STEACK CON BEBI
    (104, 5, 'Pechuga napolitana',                   2550000, true, 'Asados'),
    (105, 5, 'Especial chicharrón El Asao',          2300000, true, 'Asados'),
    (106, 5, 'Asado cerdo',                          2530000, true, 'Asados'),
    (107, 5, 'Asado pollo',                          2530000, true, 'Asados'),
    (108, 5, 'Asado mixto',                          2530000, true, 'Asados'),
    (109, 5, 'Asado parrilla',                       3110000, true, 'Asados'),
    (110, 5, 'Asado de carne con bebida',            2990000, true, 'Asados'),
    (111, 5, 'Patacón con todo',                     2930000, true, 'Asados'),
    (112, 5, 'Picada El Asao',                       2930000, true, 'Asados'),

    -- Hamburguesas y perros
    (120, 5, 'Combo hamburguesa pollo',              2420000, true, 'Hamburguesas y perros'),
    (121, 5, 'Combo hamburguesa carne',              2420000, true, 'Hamburguesas y perros'),
    (122, 5, 'Hamburguesa sencilla de carne',        2010000, true, 'Hamburguesas y perros'),
    (123, 5, 'Hamburguesa sencilla de pollo',        2010000, true, 'Hamburguesas y perros'),
    (124, 5, 'Perro caliente',                       1500000, true, 'Hamburguesas y perros'),
    (125, 5, 'Choriperro',                           1600000, true, 'Hamburguesas y perros'),
    (126, 5, 'Salchipapas',                          1730000, true, 'Hamburguesas y perros'),

    -- Adiciones y porciones
    (140, 5, 'Adición butifarra',                     220000, true, 'Adiciones'),
    (141, 5, 'Adición chorizo',                       300000, true, 'Adiciones'),  -- ADIC CHORIZO
    (142, 5, 'Adición queso mozarella',               330000, true, 'Adiciones'),  -- ADICION QSO MOZARELLA
    (143, 5, 'Porción papa cocida',                   270000, true, 'Adiciones'),
    (144, 5, 'Porción papa francesa',                 730000, true, 'Adiciones'),
    (145, 5, 'Porción patacón',                       490000, true, 'Adiciones'),
    (146, 5, 'Porción suero',                         400000, true, 'Adiciones'),

    -- Salsas
    (160, 5, 'Porción salsa BBQ El Asao',             400000, true, 'Salsas'),
    (161, 5, 'Porción salsa de la casa El Asao',      220000, true, 'Salsas'),  -- PORCION SALSA DE LA CASA ASAO
    (162, 5, 'Porción salsa napolitana El Asao',      260000, true, 'Salsas'),  -- POPCION SALSA NAPOLITANA EL ASAO
    (163, 5, 'Porción salsa tártara El Asao',         250000, true, 'Salsas'),  -- PORCION SALASA TARTARA ASAO
    (164, 5, 'Porción salsa de tomate',                60000, true, 'Salsas'),  -- PORCION SALSA TOMATE
    (165, 5, 'Chimichurri',                           140000, true, 'Salsas'),
    (166, 5, 'Vinagreta tradicional',                 140000, true, 'Salsas'),

    -- Bebidas
    (180, 5, 'Agua',                                  300000, true, 'Bebidas'),
    (181, 5, 'Gaseosa Colombiana 400 ml',             310000, true, 'Bebidas'),  -- GASEOSA PET 400 COLOMBIANA
    (182, 5, 'Gaseosa Colombiana 1,5 L',              540000, true, 'Bebidas')  -- GASEOSA PET 1.5 LT COLOMBIANA
ON CONFLICT (id) DO NOTHING;

-- Como en el `002`: la secuencia no se adelanta sola cuando se le imponen
-- identificadores, y sin esto el primer alta desde el panel chocaría con el 101.
SELECT setval(
    pg_get_serial_sequence('establecimientos', 'id'),
    (SELECT max(id) FROM establecimientos)
);
SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

COMMIT;
