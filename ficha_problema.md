# Ficha del problema

## Sistema virtual de pedidos de comida en el campus universitario

En la universidad, los estudiantes que desean comprar alimentos deben acercarse a los diferentes establecimientos del campus para consultar las opciones disponibles, realizar el pedido y esperar para recibirlo. Durante los horarios de mayor demanda, este proceso puede generar filas y tiempos de espera que hacen que los estudiantes pierdan parte de su tiempo entre clases u otras actividades académicas.

A partir de esta situación, proponemos desarrollar un sistema que permita realizar el proceso de compra de manera virtual. Los estudiantes podrán consultar los establecimientos disponibles, revisar sus menús, precios y productos disponibles, seleccionar lo que desean comprar y realizar su pedido desde la plataforma, sin necesidad de hacer la fila para solicitarlo.

El sistema estará compuesto principalmente por un módulo para estudiantes y otro para los establecimientos. Desde el módulo del estudiante será posible consultar los diferentes menús, agregar productos a un pedido, conocer el valor total y realizar el proceso de compra. Por su parte, los establecimientos podrán recibir y gestionar los pedidos, consultar la información correspondiente y actualizar su estado a medida que sean preparados.

Como parte del proceso de compra, se contempla la integración con una pasarela de pagos. Durante el desarrollo inicial se utilizará un ambiente Sandbox, que permitirá realizar y comprobar transacciones de prueba sin utilizar dinero real. De esta manera, el equipo podrá desarrollar y probar el proceso de pago, verificar las respuestas de la pasarela y preparar el sistema para una futura implementación en un ambiente real.

Una vez confirmado el pedido y su pago, el sistema generará un código único asociado a la compra. Este código permitirá identificar el pedido y verificarlo al momento de la entrega. Cuando el estudiante se acerque al establecimiento, presentará su código y el encargado podrá comprobar que corresponde con un pedido registrado y pagado antes de entregar los productos.

El sistema también permitirá consultar el estado de los pedidos, gestionar los productos y precios de los establecimientos y mantener un historial de las compras realizadas. Con estas funcionalidades se busca reducir las filas, disminuir los tiempos de espera y organizar de una manera más eficiente el proceso de compra y entrega de alimentos dentro del campus.

La propuesta busca que el estudiante pueda realizar la mayor parte del proceso desde la plataforma y únicamente tenga que acercarse al establecimiento cuando su pedido esté listo para ser recogido. Además, el uso inicial de un ambiente Sandbox permitirá desarrollar y validar la solución de manera segura, manteniendo la posibilidad de incorporar pagos reales en una futura versión del sistema.

## Usuarios del sistema

| Usuario | Qué hace en PideUTB |
|---|---|
| **Usuario del campus** (estudiante o profesor) | Consulta establecimientos y menús, arma y paga su pedido, y presenta el código de recogida |
| **Personal del establecimiento** | Gestiona productos y precios, recibe pedidos, actualiza su estado y valida el código en la entrega |
| **Administrador de la plataforma** | Administra establecimientos y aspectos generales del sistema |

## Alcance

**Dentro del alcance:** catálogo de establecimientos y menús, armado del
pedido, pago mediante Wompi en ambiente Sandbox, generación y validación del
código de recogida, gestión del estado del pedido por el establecimiento e
historial de compras.

**Fuera del alcance:** domicilios o entrega fuera del campus, pagos con dinero
real en producción, aplicación móvil nativa y gestión de inventario o
contabilidad de los establecimientos.

## Atributos de calidad y tensiones

El atributo prioritario es la **usabilidad**, porque el objetivo del proyecto
es reducir el tiempo que se pierde haciendo fila; le siguen confiabilidad,
seguridad, disponibilidad y rendimiento. El detalle, con escenarios medibles,
está en [`docs/aspectos.md`](docs/aspectos.md) y en
[`docs/arc42/arc42.md` §10](docs/arc42/arc42.md#arbol-utilidad).

Estas son las **dos tensiones de calidad** que el diseño debe arbitrar:

### T-1 · Usabilidad ⟷ Seguridad

Un pedido debe completarse en menos de 3 minutos y sin fricción
([ESC-01](docs/arc42/arc42.md#esc-01)), pero el código de recogida debe ser de
un solo uso y rechazar el 100 % de los intentos de reutilización
([ESC-04](docs/arc42/arc42.md#esc-04)). Cada verificación adicional que se
añade para proteger la entrega es un paso más que el usuario debe dar.

**Resolución adoptada:** se privilegia la usabilidad durante la compra y se
concentra la validación estricta en el momento de la entrega, que ocurre una
sola vez por pedido y lo ejecuta el personal del establecimiento, no el
usuario.

### T-2 · Rendimiento y disponibilidad ⟷ Simplicidad de construcción

En hora pico el proceso debe completarse en menos de 2 minutos en al menos el
90 % de los intentos ([ESC-02](docs/arc42/arc42.md#esc-02)), lo que empujaría
hacia servicios escalables de forma independiente. En contra pesan las
restricciones reales del proyecto: tres integrantes generalistas, sin
presupuesto y con fecha límite fija.

**Resolución adoptada:** monolito modular en un solo desplegable
([ADR-0001](docs/adr/0001-estilo-arquitectonico.md)). Se acepta perder escalado
independiente a cambio de entregar a tiempo, manteniendo fronteras de módulo
que permitan extraer `pedidos` como servicio si la medición muestra que el
umbral de ESC-02 no se cumple.
