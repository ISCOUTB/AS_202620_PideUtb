-- Las fotos de la carta de El Asao.
--
-- Hasta aquí `menu_items.imagen` estaba en nulo para las 37 filas, y el
-- catálogo dibujaba el marcador con la inicial que `app.js` tiene previsto para
-- justo eso. Esta migración le pone foto a 25 de ellas.
--
-- Como el `005`, **esto son datos de operación, no datos semilla**, y por el
-- mismo motivo va en una migración y no en un cargador: la base del laboratorio
-- no publica puertos y el panel no da terminal, así que nada ejecutable alcanza
-- producción. Es idempotente: un `UPDATE ... WHERE id` aplicado dos veces deja
-- lo mismo.
--
-- ### De dónde salen
--
-- Del documento que mandó la cafetería: 22 fotos con sus nombres y sus precios,
-- que coinciden con los del `005`. Tres de las 22 llevan **dos productos en la
-- misma foto** —suero y salsa de tomate, vinagreta y chimichurri, papa francesa
-- y papa cocida—, así que se partieron por el hueco entre los dos y de ahí
-- salen 25 archivos y no 22. Una miniatura de 72 px donde la mitad es otro
-- producto no es la foto de ese producto.
--
-- El emparejamiento foto→plato está comprobado mirando las 22, no deducido del
-- orden del documento: los anclajes del ODT no son fiables, y aquí equivocarse
-- significa enseñar un perro caliente donde dice «Asado de cerdo».
--
-- ### Por qué 12 filas siguen sin foto
--
-- Porque la cafetería no mandó esas. Poner la foto de otro plato parecido sería
-- inventarse el producto, y el marcador con la inicial ya está diseñado y
-- probado para este caso. Las que faltan son: pechuga napolitana, especial
-- chicharrón, asado de carne con bebida, picada, combo hamburguesa de pollo,
-- hamburguesa sencilla de pollo, el combo de la franja, adición de chorizo,
-- adición de queso, y las salsas BBQ, de la casa y napolitana.
--
-- ### La ruta
--
-- Relativa dentro del sitio, que es lo que declara el comentario de la columna
-- desde el `004`. `sitio/fotos/` ya viaja entera al contenedor por el `COPY
-- fotos/` del Dockerfile, así que una subcarpeta no pide nada nuevo allí.
--
-- Y vale la regla de las tipografías y la portada, que aquí es más fácil de
-- cumplir porque el nombre vive en esta tabla: **una foto nueva es un archivo
-- nuevo, con nombre nuevo.** Sustituir una dejándole el mismo nombre dejaría a
-- Cloudflare sirviendo la vieja durante cuatro horas, y cambiar el nombre
-- obliga a pasar por aquí, que es exactamente donde se quiere que pase.

BEGIN;

-- El ejemplo del comentario nombraba una carpeta —`imagenes/`— que nunca
-- existió. La que hay es `fotos/`, y quien lea la columna merece el nombre real.
COMMENT ON COLUMN menu_items.imagen IS
    'Ruta relativa dentro del sitio, p. ej. fotos/platos/salchipapas.webp. Nulo = marcador.';

UPDATE menu_items SET imagen = foto.ruta
FROM (VALUES
    -- Asados
    (101, 'fotos/platos/costillitas-de-cerdo-ahumadas.webp'),
    (102, 'fotos/platos/alitas-bbq-tamarindo.webp'),
    (103, 'fotos/platos/asado-de-carne-beef-steak.webp'),
    (106, 'fotos/platos/asado-cerdo.webp'),
    (107, 'fotos/platos/asado-pollo.webp'),
    (108, 'fotos/platos/asado-mixto.webp'),
    (109, 'fotos/platos/asado-parrilla.webp'),
    (111, 'fotos/platos/patacon-con-todo.webp'),

    -- Hamburguesas y perros
    (121, 'fotos/platos/combo-hamburguesa-carne.webp'),
    (122, 'fotos/platos/hamburguesa-sencilla-carne.webp'),
    (124, 'fotos/platos/perro-caliente.webp'),
    (125, 'fotos/platos/choriperro.webp'),
    (126, 'fotos/platos/salchipapas.webp'),

    -- Adiciones y porciones
    (140, 'fotos/platos/adicion-butifarra.webp'),
    (143, 'fotos/platos/porcion-papa-cocida.webp'),     -- mitad derecha de la foto compartida
    (144, 'fotos/platos/porcion-papa-francesa.webp'),   -- mitad izquierda
    (145, 'fotos/platos/porcion-patacon.webp'),
    (146, 'fotos/platos/porcion-suero.webp'),           -- mitad izquierda de la foto compartida

    -- Salsas
    (163, 'fotos/platos/porcion-salsa-tartara.webp'),
    (164, 'fotos/platos/porcion-salsa-de-tomate.webp'), -- mitad derecha
    (165, 'fotos/platos/chimichurri.webp'),             -- mitad derecha
    (166, 'fotos/platos/vinagreta-tradicional.webp'),   -- mitad izquierda

    -- Bebidas
    (180, 'fotos/platos/agua.webp'),
    (181, 'fotos/platos/gaseosa-colombiana-400ml.webp'),
    (182, 'fotos/platos/gaseosa-colombiana-1-5l.webp')
) AS foto(item_id, ruta)
WHERE menu_items.id = foto.item_id;

COMMIT;
