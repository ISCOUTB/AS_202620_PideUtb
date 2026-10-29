-- La cuenta del mostrador pasa al establecimiento del que se pide.
--
-- ### Qué estaba roto
--
-- El panel del mostrador mostraba una cola que no cambiaba nunca. Se leyó como
-- «no se actualiza», y el refresco automático funcionaba perfectamente: cada
-- cinco segundos pedía los pedidos **del establecimiento 1**, que es donde
-- estaba su cuenta, mientras el sitio creaba pedidos **en el 5**, que es donde
-- vive la carta de El Asao desde `005_carta_el_asao.sql`.
--
-- Los dos lados funcionaban. Nadie los había presentado.
--
-- Se comprobó antes de escribir esto: el establecimiento 1 tiene exactamente
-- dos productos —«Arepa de huevo» y «Jugo de mango», los del seed de
-- `002_datos_semilla.sql`— y los tres pedidos que el panel mostraba eran de
-- esos dos. El 5 tiene 37.
--
-- ### Por qué una migración y no la variable de entorno
--
-- Porque la variable no puede. `sembrar_usuario_inicial.py` actúa **solo si la
-- tabla `usuarios` está vacía**, y es deliberado: si actuara con la tabla
-- poblada, quien pudiera escribir una variable de entorno podría reponer la
-- contraseña de cualquier cuenta. La cuenta ya existe, así que
-- `PIDEUTB_USUARIO_INICIAL_ESTABLECIMIENTO` la ignora por diseño.
--
-- Y por debajo de eso: en el servidor del laboratorio la base no publica
-- puertos y el panel no da terminal (ADR-0008), así que `UPDATE` a mano no es
-- una opción. Una migración es el único canal que llega a esa fila, y además
-- deja constancia de por qué se tocó.
--
-- ### Por qué el 5 va escrito y no deducido
--
-- Se consideró derivarlo —«el establecimiento que más ítems tenga»— y se
-- descartó: una migración es una foto de un momento, y en este momento el
-- sistema sirve a un establecimiento concreto. Una consulta que «adivina» el
-- correcto acierta hoy y falla el día que haya dos, y falla sin decirlo.
--
-- ### Qué pasa si ya estaba bien
--
-- Nada. El `WHERE` solo alcanza a las cuentas que siguen en el 1, así que
-- aplicarla sobre una base ya corregida no cambia ninguna fila.
--
-- ### Lo que esta migración NO arregla
--
-- Un despliegue limpio vuelve a crear el problema, porque `entrypoint.sh` corre
-- las migraciones **antes** de sembrar la cuenta: sobre una base vacía esta
-- migración no encuentra nada que mover y después el sembrado crea la cuenta
-- donde diga el entorno. Eso se arregla en `deploy/compose.lab.yaml`, donde el
-- valor por defecto era el 1, y lo vigila una prueba que compara ese número con
-- el `ESTABLECIMIENTO_ID` de `sitio/config.js`. Las dos mitades hacen falta.

BEGIN;

UPDATE usuarios
SET establecimiento_id = 5
WHERE rol = 'personal_establecimiento'
  AND establecimiento_id = 1;

COMMIT;
