# Ficha del problema

## Sistema virtual de pedidos de comida en el campus universitario

En la universidad, los estudiantes que desean comprar alimentos deben acercarse a los diferentes establecimientos del campus para consultar las opciones disponibles, realizar el pedido y esperar para recibirlo. Durante los horarios de mayor demanda, este proceso puede generar filas y tiempos de espera que hacen que los estudiantes pierdan parte de su tiempo entre clases u otras actividades académicas.

A partir de esta situación, proponemos desarrollar un sistema que permita realizar el proceso de compra de manera virtual. Los estudiantes podrán consultar los establecimientos disponibles, revisar sus menús, precios y productos disponibles, seleccionar lo que desean comprar y realizar su pedido desde la plataforma, sin necesidad de hacer la fila para solicitarlo.

El sistema estará compuesto principalmente por un módulo para estudiantes y otro para los establecimientos. Desde el módulo del estudiante será posible consultar los diferentes menús, agregar productos a un pedido, conocer el valor total y realizar el proceso de compra. Por su parte, los establecimientos podrán recibir y gestionar los pedidos, consultar la información correspondiente y actualizar su estado a medida que sean preparados.

Como parte del proceso de compra, se contempla la integración con una pasarela de pagos. Durante el desarrollo inicial se utilizará un ambiente Sandbox, que permitirá realizar y comprobar transacciones de prueba sin utilizar dinero real. De esta manera, el equipo podrá desarrollar y probar el proceso de pago, verificar las respuestas de la pasarela y preparar el sistema para una futura implementación en un ambiente real.

Una vez confirmado el pedido y su pago, el sistema generará un código único asociado a la compra. Este código permitirá identificar el pedido y verificarlo al momento de la entrega. Cuando el estudiante se acerque al establecimiento, presentará su código y el encargado podrá comprobar que corresponde con un pedido registrado y pagado antes de entregar los productos.

El sistema también permitirá consultar el estado de los pedidos, gestionar los productos y precios de los establecimientos y mantener un historial de las compras realizadas. Con estas funcionalidades se busca reducir las filas, disminuir los tiempos de espera y organizar de una manera más eficiente el proceso de compra y entrega de alimentos dentro del campus.

La propuesta busca que el estudiante pueda realizar la mayor parte del proceso desde la plataforma y únicamente tenga que acercarse al establecimiento cuando su pedido esté listo para ser recogido. Además, el uso inicial de un ambiente Sandbox permitirá desarrollar y validar la solución de manera segura, manteniendo la posibilidad de incorporar pagos reales en una futura versión del sistema.
