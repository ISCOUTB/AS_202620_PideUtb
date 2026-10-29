// Configuración del recorrido de punta a punta.
//
// ### Qué añade esto a las 515 pruebas que ya hay
//
// Un navegador. Las de `backend/tests` montan la aplicación en memoria y
// comprueban contratos; `backend/scripts/verificar_flujo.py` habla HTTP contra
// un despliegue. Ninguna de las dos toca un botón.
//
// Lo que solo se ve acá: que la barra de navegación esté donde se puede
// alcanzar con el pulgar, que el carrito se vacíe al pagar, que el código
// aparezca solo cuando la pasarela confirma. Los tres fallos que el rediseño
// destapó eran de esa clase y ninguno rompía una prueba.
//
// ### Contra qué corre
//
// Contra lo que digan las variables, y por defecto contra el puesto local:
//
//   PIDEUTB_SITIO   dónde está el sitio      (http://127.0.0.1:8080)
//   PIDEUTB_API     dónde está la API        (http://127.0.0.1:8000)
//
// En CI los levanta el propio workflow. Se puede apuntar a producción, y
// entonces deja pedidos de verdad: para eso está `PIDEUTB_TOKEN_REINICIO_DEMO`,
// que el recorrido usa para limpiar al terminar si está puesta.

const { defineConfig, devices } = require("@playwright/test");

const SITIO = process.env.PIDEUTB_SITIO || "http://127.0.0.1:8080";

module.exports = defineConfig({
  testDir: ".",
  testMatch: "*.spec.js",

  // Un recorrido completo pasa por una pasarela y un sondeo cada tres segundos.
  // 60 s por prueba deja sitio para eso sin esconder un cuelgue de verdad.
  timeout: 60_000,
  expect: { timeout: 10_000 },

  // **En serie y con un solo trabajador.** Estas pruebas crean pedidos contra
  // una base compartida y una de ellas comprueba que el pedido aparece en la
  // cola del mostrador; en paralelo, dos recorridos se verían los pedidos el
  // uno al otro y el fallo saldría como intermitente.
  fullyParallel: false,
  workers: 1,

  // En CI, un reintento. Localmente ninguno: un reintento que esconde una
  // intermitencia en el portátil es una intermitencia que llega a producción.
  retries: process.env.CI ? 1 : 0,

  // Que nadie pueda dejarse un `test.only` puesto y apagar la suite entera.
  forbidOnly: !!process.env.CI,

  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"]],

  use: {
    baseURL: SITIO,
    // Solo de los fallos: una traza por prueba verde son 2 MB por nada.
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    locale: "es-CO",
    timezoneId: "America/Bogota",
  },

  projects: [
    {
      // El proyecto que importa: la charla es gente con el teléfono en la mano.
      name: "movil",
      use: { ...devices["Pixel 7"] },
    },
    {
      // Y el de escritorio, porque el mostrador se atiende desde un portátil.
      name: "escritorio",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
});
