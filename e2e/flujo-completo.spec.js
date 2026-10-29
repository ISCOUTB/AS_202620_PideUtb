// El recorrido que hará el público el 3 de noviembre, con un navegador.
//
// Carta → carrito → pedido → pasarela → pago confirmado → código de recogida.
//
// La pasarela se aprueba llamando a `/v1/pagos/simulador/{ref}` desde la propia
// prueba en vez de navegando a `pasarela.html`. No es un atajo: el enlace a la
// pasarela abre **otra pestaña**, y el estado del pedido —el token con el que
// se consulta— vive en la memoria de la primera. Navegando se pierde, que es
// justo lo que documenta `docs/violaciones.md`. Llamando al simulador, la
// pestaña del cliente sigue sondeando, que es lo que esta prueba quiere ver.

const { test, expect } = require("@playwright/test");

const API = process.env.PIDEUTB_API || "http://127.0.0.1:8000";
const TOKEN_DEMO = (process.env.PIDEUTB_TOKEN_REINICIO_DEMO || "").trim();
const MOSTRADOR = {
  correo: process.env.PIDEUTB_MOSTRADOR_CORREO || "",
  contrasena: process.env.PIDEUTB_MOSTRADOR_CONTRASENA || "",
};

/** Espera a que la carta esté pintada y devuelve cuántos productos hay. */
async function abrirLaCarta(page) {
  await page.goto("/index.html");

  // Se espera a los productos, **no** a que los esqueletos aparezcan.
  //
  // El primer intento afirmaba que los esqueletos se veían, y fallaba siempre
  // en local: la API responde en diez milisegundos, así que se pintan y se van
  // antes de que nadie pueda mirarlos. Afirmar que un estado de carga está
  // visible es intermitente por construcción — pasa o no según lo rápida que
  // esté la máquina ese día.
  //
  // Los esqueletos se comprueban aparte, frenando la petición a propósito, que
  // es la única forma de mirar un estado transitorio sin apostar.
  const productos = page.locator("#lista-items .item.producto");
  await expect(productos.first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator(".esqueleto")).toHaveCount(0);
  return productos;
}

/**
 * Aprueba el cobro abierto, como haría la pasarela, y devuelve su referencia.
 *
 * **Espera a que el enlace esté visible antes de leer su `href`.** El primer
 * intento lo leía en cuanto `Pagar` volvía, y a veces devolvía `null`: crear el
 * pedido y abrir el cobro son dos peticiones encadenadas, y el enlace no tiene
 * dirección hasta que vuelve la segunda. Fallaba como «Invalid URL», que no se
 * parece en nada a «leíste demasiado pronto».
 */
async function aprobarElCobro(page, request) {
  const enlace = page.locator("#ir-a-pasarela");
  await expect(enlace).toBeVisible({ timeout: 20_000 });

  const href = await enlace.getAttribute("href");
  const referencia = new URL(href).searchParams.get("referencia");
  expect(referencia, `el enlace a la pasarela no trae referencia: ${href}`)
    .toBeTruthy();

  const acuse = await request.post(
    `${API}/v1/pagos/simulador/${referencia}`,
    { data: { estado_pago: "aprobado" } }
  );
  expect(
    acuse.status(),
    `El simulador respondió ${acuse.status()}. Con 404, ` +
    "PIDEUTB_URL_PASARELA_SIMULADA no está puesta y la demo no se puede dar."
  ).toBe(202);

  return referencia;
}

test.describe("El recorrido del cliente", () => {
  test("de la carta al código de recogida", async ({ page, request }) => {
    const productos = await abrirLaCarta(page);
    expect(await productos.count()).toBeGreaterThan(0);

    // --- El carrito empieza apagado -----------------------------------
    const carrito = page.getByRole("button", { name: /Carrito vacío/ });
    await expect(carrito).toBeDisabled();
    await expect(page.getByRole("button", { name: "Mi código" })).toBeDisabled();

    // --- Dos productos ------------------------------------------------
    await productos.nth(0).getByRole("button", { name: /^Agregar/ }).click();

    // La lista se repinta entera al cambiar una cantidad, así que hay que
    // volver a localizar. Playwright lo hace solo; esto vale como recordatorio
    // de por qué la verificación a mano con referencias fijas no servía.
    await productos.nth(1).getByRole("button", { name: /^Agregar/ }).click();

    const verPedido = page.getByRole("button", { name: /Ver mi pedido/ });
    await expect(verPedido).toBeEnabled();
    await expect(page.locator("#carrito-chapa")).toHaveText("2");

    // --- El pedido ----------------------------------------------------
    await verPedido.click();
    await expect(page.getByRole("heading", { name: "Tu pedido" })).toBeVisible();
    await expect(page.locator("#lineas-pedido .item")).toHaveCount(2);

    const pagar = page.locator("#pagar");
    await expect(pagar).toBeDisabled();
    await expect(pagar).toHaveText("Elegí un método de pago");

    // Se marca por la etiqueta, que es lo que toca una persona.
    await page.getByText("Nequi", { exact: true }).click();
    await expect(pagar).toBeEnabled();
    await expect(pagar).toContainText("Pagar");

    // --- El cobro -------------------------------------------------------
    await pagar.click();
    await expect(page.getByText(/Esperando la confirmación del pago/)).toBeVisible();

    // --- La pasarela confirma --------------------------------------------
    await aprobarElCobro(page, request);

    // --- Y el código aparece solo ----------------------------------------
    // Sin recargar y sin tocar nada: lo trae el sondeo. Es el comportamiento
    // que ADR-0003 describe y lo que el público va a ver.
    const codigo = page.locator(".codigo-canje");
    await expect(codigo).toBeVisible({ timeout: 20_000 });
    await expect(codigo).toHaveText(/^[A-Z0-9]{4,}$/);

    await expect(page.getByRole("heading", { name: /Pago confirmado/ })).toBeVisible();

    // El carrito se vació al pagar. Este fue uno de los tres fallos que el
    // rediseño destapó: la barra seguía anunciando el importe de un pedido ya
    // cobrado, al lado de su código.
    await expect(page.getByRole("button", { name: /Carrito vacío/ })).toBeDisabled();

    // Y «Mi código» ya lleva a algún sitio.
    await expect(page.getByRole("button", { name: "Mi código" })).toBeEnabled();
  });

  test("el código sigue a mano después de pasear por la carta", async ({
    page,
    request,
  }) => {
    // Comprueba el destino «Mi código», que existe justamente para esto: en la
    // charla alguien va a tocar «Carta» después de pagar y va a querer volver.
    const productos = await abrirLaCarta(page);
    await productos.nth(0).getByRole("button", { name: /^Agregar/ }).click();
    await page.getByRole("button", { name: /Ver mi pedido/ }).click();
    await page.getByText("Tarjeta", { exact: true }).click();
    await page.locator("#pagar").click();

    await aprobarElCobro(page, request);

    const codigo = page.locator(".codigo-canje");
    await expect(codigo).toBeVisible({ timeout: 20_000 });
    const valor = await codigo.textContent();

    await page.getByRole("button", { name: "Carta" }).click();
    await expect(page.getByRole("heading", { name: "Carta" })).toBeVisible();
    await expect(codigo).toBeHidden();

    await page.getByRole("button", { name: "Mi código" }).click();
    await expect(codigo).toBeVisible();
    await expect(codigo).toHaveText(valor.trim());
  });
});

test.describe("Lo que el rediseño no puede volver a romper", () => {
  test("mientras la carta viaja se ven esqueletos, no una página en blanco", async ({
    page,
  }) => {
    // Se frena la respuesta de la carta un segundo y medio. Es la única forma
    // honesta de mirar un estado de carga: esperar a pillarlo al vuelo depende
    // de lo rápida que esté la máquina, y entonces la prueba pasa o falla por
    // motivos que no tienen que ver con el código.
    await page.route("**/v1/menu/establecimientos/**", async (ruta) => {
      await new Promise((seguir) => setTimeout(seguir, 1500));
      await ruta.continue();
    });

    await page.goto("/index.html");

    // Tres, y que se vean: ocupan el sitio que van a ocupar los productos, que
    // es lo que evita que la página dé un salto cuando lleguen.
    await expect(page.locator(".esqueleto")).toHaveCount(3, { timeout: 20_000 });
    await expect(page.locator(".esqueleto").first()).toBeVisible();

    // Y la pantalla de la carta ya está, con su encabezado: no se espera en la
    // de arranque a que responda la API.
    await expect(page.getByRole("heading", { name: "Carta" })).toBeVisible();

    // Cuando llegan los datos, los esqueletos se van.
    await expect(page.locator("#lista-items .item.producto").first()).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator(".esqueleto")).toHaveCount(0);
  });

  test("nada se sale por el lado", async ({ page }) => {
    await abrirLaCarta(page);

    const desborda = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth
    );
    expect(desborda, "la página se desplaza en horizontal").toBe(false);
  });

  test("todo lo que se toca mide 44 px o más", async ({ page }) => {
    // El mínimo táctil de las guías de accesibilidad. Acá no es un número de
    // cumplimiento: esta barra se toca con el pulgar, de pie y con la otra mano
    // ocupada.
    await abrirLaCarta(page);

    const chicos = await page.evaluate(() => {
      const fuera = [];
      // Medio píxel de tolerancia. El diseño pide 44 y el navegador devuelve
      // 43,996: `min-height: 44px` sobre una caja con bordes de 1,5 px y un
      // `devicePixelRatio` que no es entero deja fracciones. Comparar contra 44
      // a secas marcaba como defectuoso todo lo que mide exactamente 44.
      const MINIMO = 43.5;
      for (const el of document.querySelectorAll(
        "button:not([disabled]), a[href], input[type=radio] + label"
      )) {
        const caja = el.getBoundingClientRect();
        if (caja.width === 0 && caja.height === 0) continue; // oculto
        if (caja.height < MINIMO || caja.width < MINIMO) {
          fuera.push(
            `${el.id || el.className || el.tagName}: ` +
            `${Math.round(caja.width)}×${Math.round(caja.height)}`
          );
        }
      }
      return fuera;
    });

    // Los enlaces de texto corrido del pie no son objetivos táctiles: van
    // dentro de un párrafo y no se tocan, se leen.
    const relevantes = chicos.filter((d) => !d.startsWith("A:"));
    expect(relevantes, `objetivos por debajo de 44 px: ${relevantes.join(", ")}`)
      .toEqual([]);
  });

  test("la barra está donde se puede alcanzar", async ({ page }, info) => {
    await abrirLaCarta(page);

    const barra = await page.evaluate(() => {
      const nav = document.querySelector(".nav-inferior");
      const caja = nav.getBoundingClientRect();
      return {
        posicion: getComputedStyle(nav).position,
        arriba: Math.round(caja.top),
        abajo: Math.round(caja.bottom),
        alto: window.innerHeight,
      };
    });

    if (info.project.name === "movil") {
      // Clavada abajo. Este es el modo de fallo que una captura delató: con
      // `sticky` y el `<nav>` al final del documento, la barra se quedaba
      // debajo del pie de página.
      expect(barra.posicion).toBe("fixed");
      expect(barra.abajo).toBeLessThanOrEqual(barra.alto + 1);
    } else {
      expect(barra.posicion).toBe("sticky");
      expect(barra.arriba).toBe(0);
    }
  });
});

test.describe("El mostrador", () => {
  test.skip(
    !MOSTRADOR.correo || !MOSTRADOR.contrasena,
    "Sin PIDEUTB_MOSTRADOR_CORREO y PIDEUTB_MOSTRADOR_CONTRASENA"
  );

  test("ve los pedidos del mismo establecimiento del que se pide", async ({
    page,
  }) => {
    // Esta es la prueba del bug de la semana: el panel refrescaba cada cinco
    // segundos una cola que no podía cambiar nunca, porque su cuenta vivía en
    // el establecimiento 1 y los pedidos entraban al 5.
    await page.goto("/panel.html");

    await page.locator("#correo").fill(MOSTRADOR.correo);
    await page.locator("#contrasena").fill(MOSTRADOR.contrasena);
    await page.getByRole("button", { name: "Entrar" }).click();

    await expect(page.locator("#quien")).toBeVisible({ timeout: 15_000 });

    // `CONFIG` y no `window.CONFIG`: `config.js` lo declara con `const`, que en
    // un script clásico crea un enlace en el ámbito léxico global y **no** una
    // propiedad de `window`. Se lee por su nombre o no se lee.
    const establecimientoDelSitio = await page.evaluate(
      () => CONFIG.ESTABLECIMIENTO_ID
    );
    await expect(page.locator("#quien")).toContainText(
      `establecimiento ${establecimientoDelSitio}`
    );
  });
});

// Deja la base como estaba, si se le dio con qué.
test.afterAll(async ({ }, info) => {
  if (!TOKEN_DEMO) return;
  // `request` no está disponible en un hook `afterAll` sin fixture, así que se
  // usa fetch a secas: es una sola llamada y no necesita contexto de navegador.
  try {
    await fetch(`${API}/v1/demo/reiniciar`, {
      method: "POST",
      headers: { "X-Token-Demo": TOKEN_DEMO, "Content-Type": "application/json" },
    });
  } catch {
    // Que no se pueda limpiar no invalida lo que las pruebas acaban de
    // comprobar. Se avisa y ya.
    console.warn("No se pudo reiniciar la demo al terminar.");
  }
});
