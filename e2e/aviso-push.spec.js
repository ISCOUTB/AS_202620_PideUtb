// El aviso de que el pedido está listo, de punta a punta menos un eslabón.
//
// Va en su propio archivo porque necesita el Chromium completo: el reducido sin
// ventana, que usa el resto de la suite, da las notificaciones por bloqueadas aunque
// se le concedan. Y esa opción no se puede cambiar a mitad de un archivo.
//
// El eslabón que falta es el servicio del fabricante (Google, Apple, Mozilla): sin él
// no hay suscripción real, así que se le da una hecha al navegador. Todo lo demás es
// de verdad: el permiso, el registro de `sw.js`, la petición a la API y el push que
// despierta al Service Worker. Lo que esta prueba no puede decir es que el aviso
// llegue a un teléfono; eso hay que mirarlo con uno en la mano.

const { test, expect } = require("@playwright/test");

test.use({ channel: "chromium" });

const API = process.env.PIDEUTB_API || "http://127.0.0.1:8000";

/** Un pedido pagado, guardado como si esta misma pestaña lo hubiera hecho. */
async function abrirUnPedidoPagado(page, request) {
  const pedido = await (
    await request.post(`${API}/v1/pedidos`, {
      data: { lineas: [{ item_id: 124, cantidad: 1 }] },
    })
  ).json();
  const intento = await (
    await request.post(`${API}/v1/pagos/intentos`, {
      data: { pedido_id: pedido.pedido_id, metodo: "pse" },
    })
  ).json();
  await request.post(`${API}/v1/pagos/simulador/${intento.referencia_pago}`, {
    data: { estado_pago: "aprobado" },
  });

  await page.addInitScript(
    ([id, token]) => {
      if (localStorage.getItem("pideutb.pedido")) return;
      localStorage.setItem(
        "pideutb.pedido",
        JSON.stringify({ pedido_id: id, token_consulta: token, guardado_en: Date.now() })
      );
    },
    [pedido.pedido_id, pedido.token_consulta]
  );

  await page.goto("/index.html");
  await expect(page.locator(".codigo-canje")).toBeVisible({ timeout: 20_000 });
}

test("pedir el aviso lo registra, y un push enseña la notificación", async ({
  page,
  context,
  request,
}) => {
  await context.grantPermissions(["notifications"]);

  await page.route("**/v1/avisos/clave-publica", (ruta) =>
    ruta.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        clave_publica:
          "BNbxGYNMhEIi9zrneh7mqV4oUanjLUK3m-mYZBc62frMKrEoMk88r3Lk596T0ck9xlT-aok0vO7KC-SjBEUDIgo",
      }),
    })
  );
  await page.addInitScript(() => {
    PushManager.prototype.subscribe = async () => ({
      endpoint: "https://fcm.googleapis.com/fcm/send/prueba-e2e",
    });
  });

  await abrirUnPedidoPagado(page, request);

  const registrada = page.waitForResponse((r) => r.url().includes("/aviso-push"));
  await page.getByRole("button", { name: "Avisarme cuando esté listo" }).click();
  expect((await registrada).status()).toBe(204);
  await expect(page.locator("#texto-aviso")).toHaveText(/Te avisamos/);
  await expect(page.locator("#activar-aviso")).toBeHidden();

  // Sigue dicho después de recargar: no se ofrece otra vez lo que ya está pedido.
  await page.reload();
  await expect(page.locator("#texto-aviso")).toHaveText(/Te avisamos/);

  // Y el Service Worker de verdad, con un push vacío como el que manda `app/avisos.py`.
  const cdp = await context.newCDPSession(page);
  const origen = new URL(page.url()).origin;
  const registro = new Promise((resolver) => {
    cdp.on("ServiceWorker.workerRegistrationUpdated", ({ registrations }) => {
      const propio = registrations.find((r) => r.scopeURL.startsWith(origen));
      if (propio) resolver(propio.registrationId);
    });
  });
  await cdp.send("ServiceWorker.enable");
  await cdp.send("ServiceWorker.deliverPushMessage", {
    origin: origen,
    registrationId: await registro,
    data: "",
  });

  await expect
    .poll(() =>
      page.evaluate(async () => {
        const activo = await navigator.serviceWorker.ready;
        const avisos = await activo.getNotifications();
        return avisos.map((n) => [n.title, n.body, n.tag]);
      })
    )
    .toEqual([["Tu pedido está listo", "Pasá por el mostrador con tu código.", "pedido-listo"]]);
});

test("si el navegador niega el permiso, se dice y no se insiste", async ({ page, request }) => {
  await page.route("**/v1/avisos/clave-publica", (ruta) =>
    ruta.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ clave_publica: "cualquiera" }),
    })
  );
  await page.addInitScript(() => {
    Object.defineProperty(Notification, "permission", { get: () => "denied" });
  });

  await abrirUnPedidoPagado(page, request);

  await expect(page.locator("#texto-aviso")).toHaveText(/bloqueadas/);
  await expect(page.locator("#activar-aviso")).toBeHidden();
});
