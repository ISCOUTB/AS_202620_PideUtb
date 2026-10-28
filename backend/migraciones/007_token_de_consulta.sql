-- Un identificador no adivinable para consultar un pedido.
--
-- ### Qué estaba roto
--
-- `GET /v1/pedidos/{pedido_id}` era público y devolvía `codigo_canje`. Los
-- identificadores son secuenciales, así que **cualquiera, sin credenciales,
-- podía recorrer `/v1/pedidos/1`, `/2`, `/3`… y cosechar los códigos de canje
-- de los pedidos pagados** — el papel con el que se recoge la comida en el
-- mostrador. Comprobado contra la API antes de escribir esto: cinco peticiones,
-- tres códigos.
--
-- No estaba en el modelo de amenazas de arc42 §8.7. I-1 cubre enumerar los
-- pedidos *de otro establecimiento* por el panel, que exige sesión; esta puerta
-- no exigía nada.
--
-- ### Por qué un token y no autenticación
--
-- Porque **no hay cuentas de cliente, y es una decisión, no una carencia**
-- (arc42 §8.8): pedir comida no debería exigir registrarse, y no registrar es
-- lo que hace que no haya datos personales que proteger. Un pedido necesita
-- entonces algo que lo identifique sin identificar a nadie, y eso es un token
-- opaco: lo recibe quien crea el pedido, en la respuesta de su creación, y no
-- se puede derivar del identificador.
--
-- ### Por qué `text` y no `uuid`
--
-- El valor lo genera el servicio con `secrets.token_urlsafe(24)`, que son 192
-- bits de aleatoriedad frente a los 122 útiles de un UUIDv4. Guardarlo como
-- `uuid` obligaría a generar menos entropía para que cupiera en el tipo.
--
-- ### Los pedidos que ya existen
--
-- Reciben un valor derivado de `sha256` con la marca de tiempo y el
-- identificador. No es `secrets`, y aquí da igual: son pedidos anteriores al
-- cambio, cuyos clientes ya recogieron o ya no van a consultar. Lo que importa
-- es que la columna quede `NOT NULL` y que ninguno comparta token.

BEGIN;

ALTER TABLE pedidos ADD COLUMN token_consulta text;

COMMENT ON COLUMN pedidos.token_consulta IS
    'Identificador no adivinable para consultar el pedido sin tener cuenta. '
    'Se entrega una sola vez, al crearlo.';

UPDATE pedidos
SET token_consulta = encode(
    sha256(
        (id::text || clock_timestamp()::text || random()::text)::bytea
    ),
    'hex'
)
WHERE token_consulta IS NULL;

ALTER TABLE pedidos ALTER COLUMN token_consulta SET NOT NULL;

-- Dos pedidos con el mismo token dejarían a uno leyendo el otro. Con 192 bits
-- la colisión no va a ocurrir; la restricción está para que, si alguna vez el
-- generador se cambia por uno peor, falle aquí en vez de en silencio.
ALTER TABLE pedidos ADD CONSTRAINT token_consulta_unico UNIQUE (token_consulta);

ALTER TABLE pedidos ADD CONSTRAINT token_consulta_no_vacio
    CHECK (length(token_consulta) >= 16);

COMMIT;
