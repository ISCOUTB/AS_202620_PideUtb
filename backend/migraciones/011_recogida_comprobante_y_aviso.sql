-- Lo que hace falta para programar la recogida, mandar el comprobante y avisar.
--
-- Decisión y costes: ADR-0012.
--
-- ### El horario de El Asao es un supuesto
--
-- `005` dejó «horario por confirmar» porque nadie lo sabía, y sigue sin constar:
-- lo único seguro es que a las 14:30 está abierto. Validar la hora de recogida
-- exige un horario, así que aquí se pone uno **ancho a propósito**, de 7:00 a
-- 20:00: un horario demasiado estrecho rechazaría pedidos buenos, y este como
-- mucho deja programar una hora en la que la cafetería ya cerró. El texto lo
-- dice para que nadie lo dé por cierto. Se corrige con otra migración.
--
-- Son dos columnas y no se deduce del texto de `horario`, que es para leerlo:
-- ahí hay cosas como «L-V 07:00-18:00» y «cerrado temporalmente». Nulo significa
-- que el establecimiento no ha publicado su horario, y entonces no se programa.
--
-- ### Datos personales
--
-- `nombre_cliente` y `correo_cliente` son los primeros datos de una persona que
-- guarda esta tabla, y son opcionales: quien no los da pide exactamente como
-- antes. Solo sirven para mandar el comprobante y no los publica ninguna
-- respuesta de la API, ni siquiera la cola del mostrador (arc42 §8.8).
--
-- ### El consecutivo sale de una secuencia y no del número de pedido
--
-- Un pedido sin pagar también gasta identificador, así que los comprobantes
-- saltarían de uno a otro. Se asigna dentro del mismo `UPDATE` que marca el pago,
-- así que solo lo gasta quien gana: un aviso repetido de la pasarela no consume
-- número. Una transacción abortada sí deja un hueco, y aquí no importa: esto no
-- es una factura electrónica de la DIAN.
--
-- ### `aviso_push_endpoint` es una columna y no una tabla
--
-- Es la dirección a la que el servicio de notificaciones del navegador espera el
-- aviso. Un pedido se hace desde un teléfono, y el aviso se manda una sola vez:
-- al enviarlo se borra. Una tabla aparte resolvería varios teléfonos por pedido,
-- que no es algo que pueda pasar sin compartir el token.

BEGIN;

ALTER TABLE establecimientos
    ADD COLUMN hora_apertura time,
    ADD COLUMN hora_cierre   time,
    ADD CONSTRAINT horario_con_sentido CHECK (hora_apertura < hora_cierre);

-- Los tres primeros repiten lo que su `horario` ya decía (`002`).
UPDATE establecimientos SET hora_apertura = '07:00', hora_cierre = '18:00' WHERE id = 1;
UPDATE establecimientos SET hora_apertura = '09:00', hora_cierre = '16:00' WHERE id = 2;
UPDATE establecimientos SET hora_apertura = '10:00', hora_cierre = '15:00' WHERE id = 4;

UPDATE establecimientos
SET hora_apertura = '07:00',
    hora_cierre   = '20:00',
    horario       = '7:00 a 20:00 (por confirmar)'
WHERE id = 5;

ALTER TABLE pedidos
    ADD COLUMN hora_recogida       timestamptz,
    ADD COLUMN nombre_cliente      text,
    ADD COLUMN correo_cliente      text,
    ADD COLUMN numero_comprobante  bigint UNIQUE,
    ADD COLUMN pagado_en           timestamptz,
    ADD COLUMN aviso_push_endpoint text;

CREATE SEQUENCE comprobantes_consecutivo AS bigint;

COMMIT;
