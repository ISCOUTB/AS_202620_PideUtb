// Pieza 1 de seis: el Sitio.
//
// Consume la API declarada en `docs/api/openapi.yaml`. Lo que lee y los
// códigos que maneja NO son una decisión de este archivo: están declarados en
// `contracts/consumidor-web.yaml`, y el pipeline del proveedor falla si la API
// deja de emitir alguno de esos campos.
//
// Si aquí se empieza a leer un campo nuevo, hay que declararlo allí. Si no, el
// proveedor podría retirarlo sin enterarse de que alguien lo usaba.

"use strict";

// --------------------------------------------------------------------------
// Utilidades
// --------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);

const PANTALLAS = ["arranque", "carta", "pedido", "espera", "resultado"];

function mostrar(nombre) {
  for (const p of PANTALLAS) {
    $(`pantalla-${p}`).classList.toggle("activa", p === nombre);
  }
}

/** Centavos de COP a texto legible. 400000 → "$4.000". */
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

function limpiarError() {
  $("error").classList.add("oculto");
}

/**
 * Llama a la API y traduce los códigos de error a mensajes para una persona.
 *
 * El contrato declara qué códigos emite cada operación; aquí se traducen los
 * que el consumidor dice manejar. Un código no contemplado cae en el mensaje
 * genérico en lugar de romper la página.
 */
async function api(ruta, opciones = {}) {
  const respuesta = await fetch(`${CONFIG.API}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });

  if (respuesta.ok) return respuesta.json();

  // El cuerpo de error del contrato es {detail: string} en los 4xx de negocio.
  let detalle = "";
  try {
    const cuerpo = await respuesta.json();
    detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : "";
  } catch {
    // Una respuesta sin JSON válido no debe tumbar la página.
  }

  const error = new Error(detalle || `La API respondió ${respuesta.status}`);
  error.status = respuesta.status;
  throw error;
}

// --------------------------------------------------------------------------
// Estado de la sesión del usuario
// --------------------------------------------------------------------------

let pedidoActual = null;
let temporizadorConsulta = null;

// --------------------------------------------------------------------------
// Pantalla 0 · comprobar que la API responde
//
// Operación `consultarSalud`. Existe por el arranque en frío: el plan gratuito
// duerme el servicio tras 15 min sin tráfico y tarda ~60 s en despertar. Sin
// avisar, el usuario ve una página congelada y asume que está rota.
// --------------------------------------------------------------------------

async function comprobarSalud() {
  const avisar = setTimeout(
    () => $("aviso-frio").classList.remove("oculto"),
    CONFIG.MS_ANTES_DE_AVISAR_ARRANQUE_EN_FRIO
  );

  try {
    const salud = await api("/health");
    clearTimeout(avisar);

    if (salud.status !== "ok") {
      throw new Error("El servicio respondió, pero se declaró no disponible.");
    }
    await cargarCarta();
  } catch (e) {
    clearTimeout(avisar);
    $("mensaje-arranque").textContent = "No se pudo contactar con el servicio.";
    $("aviso-frio").classList.add("oculto");
    fallar(
      `${e.message} Si acabás de abrir la página, esperá un minuto y recargá: ` +
      "el servicio puede estar despertando."
    );
  }
}

// --------------------------------------------------------------------------
// Pantalla 1 · la carta
//
// Operación `listarItemsDeEstablecimiento`. Lee `establecimiento_id` e
// `items[].{item_id, nombre, precio_centavos, disponible}`.
// --------------------------------------------------------------------------

async function cargarCarta() {
  limpiarError();

  try {
    const carta = await api(
      `/v1/menu/establecimientos/${CONFIG.ESTABLECIMIENTO_ID}/items`
    );

    const lista = $("lista-items");
    lista.replaceChildren();

    // Un establecimiento sin ítems devuelve 200 con lista vacía, no 404. El
    // contrato distingue "no existe" de "no tiene nada" a propósito.
    if (carta.items.length === 0) {
      const vacio = document.createElement("li");
      vacio.className = "nota";
      vacio.textContent = "Este establecimiento todavía no cargó su carta.";
      lista.append(vacio);
    }

    for (const item of carta.items) {
      lista.append(dibujarItem(item));
    }

    mostrar("carta");
  } catch (e) {
    mostrar("carta");
    fallar(
      e.status === 404
        ? "Ese establecimiento no existe."
        : `No se pudo cargar la carta: ${e.message}`
    );
  }
}

function dibujarItem(item) {
  const fila = document.createElement("li");
  fila.className = item.disponible ? "item" : "item agotado";

  const datos = document.createElement("div");
  datos.className = "item-datos";

  const nombre = document.createElement("div");
  nombre.className = "item-nombre";
  nombre.textContent = item.nombre;

  const precio = document.createElement("div");
  precio.className = "item-precio";
  precio.textContent = pesos(item.precio_centavos);

  datos.append(nombre, precio);
  fila.append(datos);

  if (item.disponible) {
    const boton = document.createElement("button");
    boton.textContent = "Pedir";
    boton.addEventListener("click", () => crearPedido(item.item_id));
    fila.append(boton);
  } else {
    const etiqueta = document.createElement("span");
    etiqueta.className = "etiqueta-agotado";
    etiqueta.textContent = "Agotado";
    fila.append(etiqueta);
  }

  return fila;
}

// --------------------------------------------------------------------------
// Pantalla 2 · crear el pedido
//
// Operación `crearPedido`. Envía solo {item_id, cantidad}: el establecimiento
// se deriva del ítem y el contrato ignora cualquier campo extra (V-01).
// --------------------------------------------------------------------------

async function crearPedido(itemId) {
  limpiarError();

  try {
    pedidoActual = await api("/v1/pedidos", {
      method: "POST",
      body: JSON.stringify({ item_id: itemId, cantidad: 1 }),
    });

    dibujarResumen(pedidoActual);
    mostrar("pedido");
  } catch (e) {
    const mensajes = {
      404: "Ese ítem ya no existe en la carta.",
      409: e.message, // ítem agotado o establecimiento cerrado: la API explica cuál
      422: "La cantidad pedida no es válida.",
    };
    fallar(mensajes[e.status] || `No se pudo crear el pedido: ${e.message}`);
  }
}

function dibujarResumen(pedido) {
  const filas = [
    ["Producto", pedido.nombre_item],
    ["Cantidad", String(pedido.cantidad)],
    ["Precio unitario", pesos(pedido.precio_unitario_centavos)],
  ];

  const resumen = $("resumen-pedido");
  resumen.replaceChildren();

  for (const [etiqueta, valor] of filas) {
    const dt = document.createElement("dt");
    dt.textContent = etiqueta;
    const dd = document.createElement("dd");
    dd.textContent = valor;
    resumen.append(dt, dd);
  }

  const dtTotal = document.createElement("dt");
  dtTotal.className = "total";
  dtTotal.textContent = "Total";
  const ddTotal = document.createElement("dd");
  ddTotal.className = "total";
  ddTotal.textContent = pesos(pedido.total_centavos);
  resumen.append(dtTotal, ddTotal);
}

// --------------------------------------------------------------------------
// Pago
//
// Operación `iniciarIntentoDePago`. Es síncrona y devuelve a dónde ir, no el
// resultado del cobro: en ese instante el resultado todavía no existe
// (ADR-0003).
// --------------------------------------------------------------------------

async function pagar(metodo) {
  limpiarError();

  try {
    const intento = await api("/v1/pagos/intentos", {
      method: "POST",
      body: JSON.stringify({ pedido_id: pedidoActual.pedido_id, metodo }),
    });

    // `estado_pago` llega en `pendiente`: el cobro aún no ocurrió. Se pasa a
    // la pantalla de espera y se consulta el pedido, que es la única forma de
    // enterarse de algo que llega por otro canal.
    mostrar("espera");
    consultarEstadoPeriodicamente();

    // En un despliegue real aquí se redirige a `intento.url_checkout`. En
    // Sandbox se deja el enlace visible para poder demostrar el flujo sin
    // abandonar la página durante la sustentación.
    console.info("Checkout de la pasarela:", intento.url_checkout);
  } catch (e) {
    const mensajes = {
      404: "El pedido ya no existe.",
      409: "Este pedido ya no admite pago.",
      422: "El método de pago no es válido.",
    };
    fallar(mensajes[e.status] || `No se pudo iniciar el pago: ${e.message}`);
  }
}

// --------------------------------------------------------------------------
// Pantalla 3 · esperar la confirmación
//
// Operación `obtenerPedido`. Existe únicamente porque la confirmación del pago
// llega por un canal asíncrono. Con una integración síncrona el resultado
// vendría en la misma respuesta y esta pantalla sobraría.
// --------------------------------------------------------------------------

function consultarEstadoPeriodicamente() {
  detenerConsultas();
  temporizadorConsulta = setInterval(
    consultarEstado,
    CONFIG.MS_ENTRE_CONSULTAS_DE_ESTADO
  );
  consultarEstado();
}

function detenerConsultas() {
  if (temporizadorConsulta !== null) {
    clearInterval(temporizadorConsulta);
    temporizadorConsulta = null;
  }
}

async function consultarEstado() {
  try {
    const pedido = await api(`/v1/pedidos/${pedidoActual.pedido_id}`);
    pedidoActual = pedido;

    // Mientras siga pendiente de pago no hay nada nuevo que mostrar: el evento
    // de la pasarela todavía no llegó, y puede no llegar nunca.
    if (pedido.estado === "pendiente_pago") return;

    detenerConsultas();
    mostrarResultado(pedido);
  } catch (e) {
    detenerConsultas();
    mostrar("resultado");
    $("titulo-resultado").textContent = "No pudimos consultar tu pedido";
    fallar(
      e.status === 404
        ? "El pedido ya no existe."
        : `Error al consultar: ${e.message}`
    );
  }
}

// --------------------------------------------------------------------------
// Pantalla 4 · el resultado
//
// Los seis estados son exactamente los seis que declara
// `contracts/consumidor-web.yaml`. Si la API añade uno nuevo sin declararlo
// allí, la prueba de contrato del proveedor falla — que es la regla I-8 de la
// política de versionado hecha comprobable.
// --------------------------------------------------------------------------

const RESPUESTA_POR_ESTADO = {
  pendiente_pago: {
    titulo: "Tu pedido está esperando el pago",
    punto: "espera",
    texto: "Todavía no recibimos la confirmación. Tu pedido sigue guardado.",
  },
  pagado: {
    titulo: "¡Listo! Pago confirmado",
    punto: "ok",
    texto: "Presentá este código en el establecimiento para recoger tu pedido.",
    mostrarCodigo: true,
  },
  en_preparacion: {
    titulo: "Lo están preparando",
    punto: "espera",
    texto: "El establecimiento ya recibió tu pedido.",
    mostrarCodigo: true,
  },
  listo_para_recoger: {
    titulo: "¡Ya podés pasar a recogerlo!",
    punto: "ok",
    texto: "Tu pedido está listo. Presentá el código.",
    mostrarCodigo: true,
  },
  entregado: {
    titulo: "Pedido entregado",
    punto: "ok",
    texto: "Este pedido ya fue entregado. Gracias por usar PideUTB.",
  },
  cancelado: {
    titulo: "Pedido cancelado",
    punto: "mal",
    texto: "Este pedido fue cancelado. Podés hacer otro cuando quieras.",
  },
};

function mostrarResultado(pedido) {
  const respuesta = RESPUESTA_POR_ESTADO[pedido.estado];

  // Un estado que el consumidor no conoce no debe romper la página: se informa
  // con honestidad en vez de mostrar una pantalla en blanco.
  if (!respuesta) {
    $("titulo-resultado").textContent = "Estado desconocido";
    $("cuerpo-resultado").replaceChildren(
      nota(`Tu pedido está en el estado "${pedido.estado}", que esta versión
            del sitio no sabe interpretar. Consultá en el establecimiento.`)
    );
    mostrar("resultado");
    return;
  }

  $("titulo-resultado").textContent = respuesta.titulo;

  const cuerpo = $("cuerpo-resultado");
  cuerpo.replaceChildren();

  const linea = document.createElement("div");
  linea.className = "estado-linea";
  const punto = document.createElement("span");
  punto.className = `punto ${respuesta.punto}`;
  const texto = document.createElement("span");
  texto.textContent = respuesta.texto;
  linea.append(punto, texto);
  cuerpo.append(linea);

  if (respuesta.mostrarCodigo && pedido.codigo_canje) {
    const codigo = document.createElement("div");
    codigo.className = "codigo-canje";
    codigo.textContent = pedido.codigo_canje;
    cuerpo.append(codigo);
  }

  cuerpo.append(nota(`Total pagado: ${pesos(pedido.total_centavos)}`));
  mostrar("resultado");
}

function nota(texto) {
  const p = document.createElement("p");
  p.className = "nota";
  p.textContent = texto;
  return p;
}

// --------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------

for (const boton of document.querySelectorAll(".metodo")) {
  boton.addEventListener("click", () => pagar(boton.dataset.metodo));
}

$("volver-a-carta").addEventListener("click", () => {
  limpiarError();
  mostrar("carta");
});

$("dejar-de-esperar").addEventListener("click", () => {
  detenerConsultas();
  mostrarResultado(pedidoActual);
});

$("nuevo-pedido").addEventListener("click", () => {
  pedidoActual = null;
  limpiarError();
  cargarCarta();
});

comprobarSalud();
