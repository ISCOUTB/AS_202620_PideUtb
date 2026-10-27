// Pasarela de pruebas.
//
// Hace de sistema externo cuando no hay uno. Existe para poder recorrer el
// flujo entero —pedido, cobro, código de canje— sin una cuenta de comercio,
// que es lo que hace falta para una demostración y para desarrollar sin red.
//
// **No es parte del contrato.** `contracts/consumidor-web.yaml` declara lo que
// consume el sitio del cliente; esta página habla con una ruta que la API deja
// fuera de su documentación a propósito y que solo responde donde el
// despliegue define `PIDEUTB_URL_PASARELA_SIMULADA`.
//
// Lo que **no** hace, y es lo importante: no devuelve el pedido ya pagado a
// quien pulsa. Solo dispara el evento. Quien pagó se entera por su propia
// consulta, igual que con una pasarela real (ADR-0003).

"use strict";

const $ = (id) => document.getElementById(id);

// Un `fetch` propio en vez de reutilizar el de `app.js`: cargar la aplicación
// del cliente aquí arrancaría su pantalla de comprobación y su carta. Son diez
// líneas, y mantienen separadas dos páginas que representan a dos sistemas.
async function avisarAPideutb(referencia, estadoPago) {
  const respuesta = await fetch(
    `${CONFIG.API}/v1/pagos/simulador/${encodeURIComponent(referencia)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ estado_pago: estadoPago }),
    }
  );

  if (respuesta.ok) return respuesta.json();

  let detalle = "";
  try {
    detalle = (await respuesta.json()).detail || "";
  } catch {
    // Una respuesta sin JSON no debe tumbar la página.
  }

  const error = new Error(detalle || `La API respondió ${respuesta.status}`);
  error.status = respuesta.status;
  throw error;
}

function mostrar(nombre) {
  for (const seccion of document.querySelectorAll(".pantalla")) {
    seccion.classList.toggle("activa", seccion.id === `pantalla-${nombre}`);
  }
}

function pesos(centavos) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(centavos / 100);
}

function fallar(mensaje) {
  const caja = $("error");
  caja.textContent = mensaje;
  caja.classList.remove("oculto");
}

// --------------------------------------------------------------------------
// Lo que llega en la dirección
// --------------------------------------------------------------------------

const parametros = new URLSearchParams(location.search);
const referencia = (parametros.get("referencia") || "").trim();

// El importe y el método **solo deciden lo que se pinta**. La confirmación
// viaja por referencia y el importe que cuenta es el que PideUTB tiene
// guardado, así que cambiarlos a mano en la barra de direcciones no cambia lo
// que se cobra ni lo que queda registrado.
const monto = Number.parseInt(parametros.get("monto") || "", 10);
const metodo = (parametros.get("metodo") || "").trim();

const NOMBRE_DEL_METODO = {
  tarjeta: "Tarjeta",
  nequi: "Nequi",
  pse: "PSE",
};

if (!referencia) {
  mostrar("sin-referencia");
} else {
  $("referencia").textContent = referencia;
  $("metodo").textContent = NOMBRE_DEL_METODO[metodo] || "No indicado";
  $("monto").textContent = Number.isInteger(monto) ? pesos(monto) : "—";
  mostrar("cobro");
}

// --------------------------------------------------------------------------
// Las dos respuestas posibles
// --------------------------------------------------------------------------

const RESUELTO = {
  aprobado: {
    punto: "ok",
    texto: "Pago aprobado. Ya se lo avisamos a PideUTB.",
  },
  rechazado: {
    punto: "mal",
    texto: "Pago rechazado. Ya se lo avisamos a PideUTB.",
  },
};

async function resolver(estadoPago) {
  $("error").classList.add("oculto");

  const botones = [$("aprobar"), $("rechazar")];
  for (const boton of botones) boton.disabled = true;

  try {
    await avisarAPideutb(referencia, estadoPago);
  } catch (e) {
    const mensajes = {
      404:
        "Esta referencia no existe, o este despliegue no tiene pasarela " +
        "simulada. Volvé a PideUTB e iniciá el pago otra vez.",
      422: "La respuesta no es válida.",
    };
    fallar(mensajes[e.status] || `No se pudo avisar a PideUTB: ${e.message}`);
    for (const boton of botones) boton.disabled = false;
    return;
  }

  const resuelto = RESUELTO[estadoPago];
  $("punto-resuelto").className = `punto ${resuelto.punto}`;
  $("texto-resuelto").textContent = resuelto.texto;
  mostrar("resuelto");
}

$("aprobar").addEventListener("click", () => {
  resolver("aprobado").catch((e) => fallar(`Fallo inesperado: ${e.message}`));
});

$("rechazar").addEventListener("click", () => {
  resolver("rechazado").catch((e) => fallar(`Fallo inesperado: ${e.message}`));
});
