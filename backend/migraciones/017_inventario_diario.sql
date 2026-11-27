-- Inventario diario por producto: cuántas unidades hay hoy de cada uno.
--
-- Decisión y costes: ADR-0015.
--
-- ### Por qué hacía falta tocar el esquema
--
-- Hasta aquí `disponible` era lo único que decía si un producto se podía
-- vender, y es un sí o un no que el mostrador marca a mano. En la sustentación
-- del 25/11/2026 se señaló lo que eso no cubre: nada impide pagar diez arepas
-- cuando quedan tres, porque la app no sabe cuántas hay. Un conteo que se fija
-- cada mañana y se descuenta con cada pedido es lo mínimo que hace falta para
-- no vender lo que no hay.
--
-- ### `NULL` significa «sin control», y es el valor de todos los productos
--
-- La columna admite nulo y **no tiene valor por defecto**: un producto con
-- `unidades_hoy` nulo se vende como hasta ahora, sin descontar nada. Es lo que
-- hace que esta migración no cambie el comportamiento de ninguna carta hasta
-- que un mostrador decida contar. Cero, en cambio, sí significa algo: se agotó.
-- Son dos estados distintos y por eso no se usa cero para los dos.
--
-- ### Un entero y no una tabla de movimientos
--
-- Un historial de entradas y salidas permitiría auditar cada unidad, y
-- costaría una tabla, sus consultas y una pantalla para leerla. Lo que el
-- mostrador necesita es poner un número por la mañana y que la carta lo
-- respete; el día que haga falta saber por qué quedan dos y no tres, una tabla
-- de movimientos se justifica sola y esta columna es su saldo.
--
-- Como toda migración de este proyecto, es aditiva y no se edita después de
-- aplicarse. Es idempotente como `002` y `009`, aunque por otro medio: un
-- `ALTER TABLE ... ADD COLUMN` a secas falla la segunda vez, y `IF NOT EXISTS`
-- es lo que lo convierte en «aplicarla dos veces no cambia nada».

BEGIN;

ALTER TABLE menu_items
    ADD COLUMN IF NOT EXISTS unidades_hoy integer CHECK (unidades_hoy >= 0);

COMMENT ON COLUMN menu_items.unidades_hoy IS
    'Unidades que quedan hoy. Nulo = sin control de inventario; cero = agotado.';

COMMIT;
