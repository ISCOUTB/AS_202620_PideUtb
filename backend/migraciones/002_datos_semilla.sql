-- Datos semilla: los mismos que tenían los repositorios en memoria.
--
-- Se mantienen idénticos a propósito. Cambiarlos durante la migración habría
-- mezclado dos cosas que conviene poder distinguir al depurar: «el sistema
-- funciona igual contra PostgreSQL» y «además los datos son otros».
--
-- Es **idempotente**: aplicarla dos veces no duplica nada. Una semilla que
-- duplica al reaplicarse convierte un reintento inocente en datos corruptos, y
-- los reintentos ocurren —una migración interrumpida por un fallo de red se
-- vuelve a lanzar sin pensarlo.

BEGIN;

-- `OVERRIDING SYSTEM VALUE` permite fijar los identificadores, que están
-- escritos en las pruebas y en los ejemplos del contrato. Después se ajusta la
-- secuencia para que los siguientes no choquen.
-- Cuatro establecimientos, y los cuatro están por un motivo: tres de ellos son
-- el único caso de prueba de una regla del sistema.
INSERT INTO establecimientos (id, nombre, ubicacion, horario, activo)
OVERRIDING SYSTEM VALUE
VALUES
    (1, 'Cafetería Central',  'Bloque A, primer piso',   'L-V 07:00-18:00', true),
    (2, 'Kiosco Bloque D',    'Bloque D, entrada norte', 'L-V 09:00-16:00', true),
    -- Inactivo: es el caso que hace comprobable el rechazo de pedidos a un
    -- establecimiento que no opera.
    (3, 'Punto Café',         'Biblioteca, piso 2',      'cerrado temporalmente', false),
    -- Opera pero no ha cargado su carta. Obliga a distinguir «no existe» (404)
    -- de «existe y no tiene nada» (200 con lista vacía): sin este caso, el
    -- frontend no puede saber si mostrar un error o «aún sin productos».
    (4, 'Carrito de frutas',  'Plazoleta central',       'L-V 10:00-15:00', true)
ON CONFLICT (id) DO NOTHING;

INSERT INTO menu_items (id, establecimiento_id, nombre, precio_centavos, disponible)
OVERRIDING SYSTEM VALUE
VALUES
    (1, 1, 'Arepa de huevo', 400000, true),
    (2, 1, 'Jugo de mango',  300000, true),
    -- Agotado: el caso que hace comprobable el rechazo por indisponibilidad.
    (3, 2, 'Empanada',       250000, false),
    -- Disponible, pero su establecimiento está inactivo. La consecuencia es que
    -- **ningún ítem de la semilla permite crear un pedido fuera del
    -- establecimiento 1**, y conviene saberlo antes de escribir una prueba que
    -- lo dé por hecho.
    (4, 3, 'Café americano', 200000, true)
ON CONFLICT (id) DO NOTHING;

-- Sin esto, el primer `INSERT` sin identificador explícito intentaría usar el 1
-- y chocaría con la semilla. `GENERATED ALWAYS AS IDENTITY` no adelanta su
-- secuencia cuando se le imponen valores.
SELECT setval(
    pg_get_serial_sequence('establecimientos', 'id'),
    (SELECT max(id) FROM establecimientos)
);
SELECT setval(
    pg_get_serial_sequence('menu_items', 'id'),
    (SELECT max(id) FROM menu_items)
);

COMMIT;
