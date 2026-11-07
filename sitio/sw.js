// El Service Worker de PideUTB. Hace una sola cosa: enseñar el aviso de que el
// pedido está listo, aunque la página esté cerrada o la pantalla apagada.
//
// **No guarda nada en caché, y no lleva manejador de `fetch` a propósito.** Es lo
// que casi todos los Service Worker hacen, y aquí sería volver a un fallo que ya
// costó caro: el 29 de octubre de 2026, un teléfono con un `index.html` nuevo y un
// `app.js` viejo se quedó con la página rota (ver `Dockerfile`). Sin `fetch`, este
// archivo no se interpone en ninguna petición: la red funciona como si no estuviera.
//
// El aviso llega vacío (`backend/app/avisos.py`), así que el texto se escribe aquí.
// No dice el código de canje a propósito: se vería en la pantalla de bloqueo, y
// quien tiene ese código recoge la comida.

"use strict";

// El mismo patrón y la misma etiqueta que `app.js`: si la página también se enteró
// por su cuenta, una notificación reemplaza a la otra en vez de salir dos.
self.addEventListener("push", (evento) => {
  evento.waitUntil(
    self.registration.showNotification("Tu pedido está listo", {
      body: "Pasá por el mostrador con tu código.",
      icon: "iconos/icono-192.png",
      tag: "pedido-listo",
      renotify: true,
      vibrate: [200, 100, 200, 100, 400],
    })
  );
});

// Tocar el aviso lleva a la pantalla del código: `app.js` retoma el pedido guardado
// al abrir. Si la aplicación ya estaba abierta se trae al frente, para no abrir otra.
self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  evento.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((ventanas) => {
        const abierta = ventanas.find((v) => !v.url.includes("panel.html"));
        return abierta ? abierta.focus() : self.clients.openWindow("./");
      })
  );
});
