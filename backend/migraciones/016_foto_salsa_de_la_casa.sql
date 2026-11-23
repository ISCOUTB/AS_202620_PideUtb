-- La foto de la salsa de la casa.
--
-- `012` la dejó sin foto: nadie sabía de qué color era, y cualquier foto habría
-- sido inventarse la salsa. El 23/11/2026 el equipo mandó la foto. Con ella,
-- todos los productos de la carta tienen foto.
--
-- `012` ya está aplicada, así que no se edita: la foto va aquí. El archivo es
-- nuevo, y por eso también su nombre (ver `sitio/fotos/LEEME.md`).
--
-- Es idempotente, por lo mismo que `009`.

BEGIN;

UPDATE menu_items SET imagen = 'fotos/platos/porcion-salsa-de-la-casa.webp' WHERE id = 161;

COMMIT;
