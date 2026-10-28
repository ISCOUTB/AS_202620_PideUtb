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

  // La barra del carrito acompaña mientras se recorre la carta y desaparece en
  // el resto. En la pantalla del pedido repetiría la cuenta y el total que ya
  // están ahí arriba, y se comería 104 px de los 812 de un teléfono.
  dibujarBarraCarrito();
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
  // Las cabeceras se **fusionan**, no se reemplazan. Con el `...opciones`
  // detrás del objeto entero, pasar una sola cabecera borraba `Content-Type` y
  // el `POST` dejaba de llevar tipo: funcionaba por casualidad mientras nadie
  // pasara cabeceras, y la primera que lo hizo tuvo que repetirla a mano.
  const { headers, ...resto } = opciones;
  const respuesta = await fetch(`${CONFIG.API}${ruta}`, {
    ...resto,
    headers: { "Content-Type": "application/json", ...headers },
  });

  if (respuesta.ok) return respuesta.json();

  // El cuerpo de error del contrato es {detail: string} en los 4xx de negocio.
  // El 503 de `/health` no lo sigue: trae {status, dependencias}, porque la
  // pregunta que responde no es «qué hiciste mal» sino «qué está caído».
  let detalle = "";
  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
    detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : "";
  } catch {
    // Una respuesta sin JSON válido no debe tumbar la página.
  }

  const error = new Error(detalle || `La API respondió ${respuesta.status}`);
  error.status = respuesta.status;
  error.cuerpo = cuerpo;
  throw error;
}


// --------------------------------------------------------------------------
// Lanzar una función asíncrona desde un sitio que no puede esperarla.
//
// Los manejadores de eventos y los temporizadores no son `async`, así que
// llamar a una función asíncrona desde ellos deja una promesa suelta. Las
// funciones de abajo capturan sus propios errores y los muestran, pero si algo
// fallara **fuera** de ese `try` el rechazo se perdería: la pantalla se
// quedaría igual y en la consola aparecería un error que el usuario no ve.
//
// Peor que un fallo visible es uno que parece que no ocurrió.
// --------------------------------------------------------------------------
function lanzar(promesa) {
  Promise.resolve(promesa).catch((e) => {
    fallar(`Algo falló de forma inesperada: ${e.message}`);
  });
}

// --------------------------------------------------------------------------
// Estado de la sesión del usuario
// --------------------------------------------------------------------------

let pedidoActual = null;
let temporizadorConsulta = null;

/**
 * El carrito, antes de que exista el pedido.
 *
 * Vive en el navegador a propósito: hasta que alguien pulsa «Pagar» no hay
 * nada que cobrar, y crear un pedido por cada producto añadido llenaría la
 * cola del mostrador de pedidos que nadie va a pagar.
 *
 * Es un `Map` de `item_id` a `{item, cantidad}`: la clave impide tener el
 * mismo producto en dos entradas, que es justo lo que la base de datos
 * también prohíbe (`un_item_una_vez_por_pedido`).
 */
const carrito = new Map();

/** Método de pago elegido, o `null` mientras no se haya elegido ninguno. */
let metodoElegido = null;

/**
 * Token con el que se consulta el pedido.
 *
 * Lo entrega la API **una sola vez**, al crear el pedido, y sin él
 * `GET /v1/pedidos/{id}` responde `404`. Existe porque los identificadores son
 * secuenciales: sin token, cualquiera podía recorrerlos y cosechar los códigos
 * de canje de los pedidos pagados (contrato 4.0.0).
 *
 * Vive en memoria, como el resto del pedido: recargar la página pierde el
 * pedido igual que antes de esto, porque no hay cuentas de cliente y no hay
 * dónde volver a buscarlo.
 */
let tokenDelPedido = null;

/**
 * Referencia del cobro en curso.
 *
 * Hace falta porque el pedido **no puede decir si el pago fue rechazado**: un
 * rechazo lo deja en `pendiente_pago`, igual que un pago que todavía no ha
 * confirmado. El estado del cobro vive en el contexto Pagos y se consulta por
 * su referencia.
 */
let referenciaDelCobro = null;

/** Categoría activa del filtro. `null` = todas. */
let categoriaActiva = null;

/** La carta completa, para filtrar sin volver a pedirla. */
let cartaCompleta = [];

// --------------------------------------------------------------------------
// Pantalla 0 · comprobar que la API responde
//
// Operación `consultarSalud`. Comprueba que la API responde antes de pintar la
// carta, y avisa si tarda. Nació por el arranque en frío de Render; esa causa
// murió con ADR-0008, pero la pantalla no, porque el aviso vale para cualquier
// motivo por el que `/health` se demore. Lo que ya no se hace es decirle al
// usuario cuál es: desde aquí no se sabe.
// --------------------------------------------------------------------------

async function comprobarSalud() {
  const avisar = setTimeout(
    () => $("aviso-lentitud").classList.remove("oculto"),
    CONFIG.MS_ANTES_DE_AVISAR_LENTITUD
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
    $("aviso-lentitud").classList.add("oculto");

    // Un 503 y un fallo de red no son lo mismo y no merecen el mismo mensaje.
    // En el 503 la API contestó: sabemos que existe, que llegamos a ella y
    // cuál de sus dependencias falló. Decirle al usuario «no se pudo
    // contactar» en ese caso sería mandarlo a revisar su wifi por un problema
    // que no está en su lado. El 503 está declarado en
    // `contracts/consumidor-web.yaml`, y la prueba de contrato falla si se
    // deja de manejar aquí.
    if (e.status === 503) {
      const caidas = Object.entries(e.cuerpo?.dependencias ?? {})
        .filter(([, dep]) => dep.estado !== "ok")
        .map(([nombre]) => nombre);

      $("mensaje-arranque").textContent = "El servicio no está disponible ahora mismo.";
      fallar(
        caidas.length
          ? `El servicio está en mantenimiento: no responde ${caidas.join(", ")}. ` +
            "Tu pedido no se perdió; volvé a intentarlo en unos minutos."
          : "El servicio está en mantenimiento. Volvé a intentarlo en unos minutos."
      );
      return;
    }

    $("mensaje-arranque").textContent = "No se pudo contactar con el servicio.";
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

    cartaCompleta = carta.items;
    dibujarCategorias();
    dibujarCarta();
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

/**
 * Las categorías que de verdad hay en la carta, más «Todas».
 *
 * Salen de los datos y no de una lista fija: añadir una categoría en la base
 * la hace aparecer aquí sin tocar este archivo. Un producto sin categoría no
 * inventa una: aparece solo en «Todas».
 */
function dibujarCategorias() {
  // `localeCompare` y no `sort()` a secas: el orden por defecto compara
  // unidades UTF-16, así que «adiciones» caería detrás de «Zumos» por ir en
  // minúscula, y la ñ quedaría donde no le toca. En una carta en español eso
  // se ve en cuanto alguien escribe «Añadidos».
  const presentes = [...new Set(
    cartaCompleta.map((i) => i.categoria).filter(Boolean)
  )].sort((a, b) => a.localeCompare(b, "es"));

  const barra = $("categorias");
  barra.replaceChildren();

  // Con una sola categoría el filtro no filtra nada: ocupar sitio con un
  // control que no hace nada es peor que no tenerlo.
  if (presentes.length < 2) return;

  const opciones = [[null, "Todas"]];
  for (const c of presentes) opciones.push([c, c]);

  for (const [valor, texto] of opciones) {
    const pastilla = document.createElement("button");
    pastilla.className = "categoria";
    pastilla.type = "button";
    pastilla.textContent = texto;
    pastilla.setAttribute("aria-pressed", String(categoriaActiva === valor));
    pastilla.addEventListener("click", () => {
      categoriaActiva = valor;
      dibujarCategorias();
      dibujarCarta();
    });
    barra.append(pastilla);
  }

  // La pastilla elegida se trae a la vista.
  //
  // Con las cinco categorías de una carta real la fila no cabe en 375 px, así
  // que «Hamburguesas y perros» queda fuera de la pantalla. Sin esto, al
  // elegirla la lista se filtraba y **no se veía ninguna pastilla marcada**:
  // la fila seguía mostrando las primeras, todas sin marcar, que es
  // exactamente la señal de «no hay filtro».
  const elegida = barra.querySelector('[aria-pressed="true"]');
  if (elegida) {
    elegida.scrollIntoView({ inline: "center", block: "nearest" });
  }
}

function dibujarCarta() {
  const lista = $("lista-items");
  lista.replaceChildren();

  const visibles = categoriaActiva === null
    ? cartaCompleta
    : cartaCompleta.filter((i) => i.categoria === categoriaActiva);

  // Un establecimiento sin ítems devuelve 200 con lista vacía, no 404. El
  // contrato distingue "no existe" de "no tiene nada" a propósito.
  if (visibles.length === 0) {
    const vacio = document.createElement("li");
    vacio.className = "nota";
    vacio.textContent = categoriaActiva === null
      ? "Este establecimiento todavía no cargó su carta."
      : "No hay nada en esa categoría por ahora.";
    lista.append(vacio);
    return;
  }

  for (const item of visibles) {
    lista.append(dibujarItem(item));
  }
}

function dibujarItem(item) {
  const fila = document.createElement("li");
  fila.className = item.disponible ? "item producto" : "item producto agotado";

  // La foto. Cuando el producto no tiene, se dibuja un marcador con su
  // inicial en vez de una imagen rota: `imagen` es nulo a propósito mientras
  // no exista el archivo.
  const figura = document.createElement("div");
  figura.className = "item-foto";
  if (item.imagen) {
    const img = document.createElement("img");
    img.src = item.imagen;
    img.alt = "";              // decorativa: el nombre ya está en el texto
    img.loading = "lazy";
    figura.append(img);
  } else {
    figura.classList.add("sin-foto");
    figura.textContent = item.nombre.trim().charAt(0).toUpperCase();
    figura.setAttribute("aria-hidden", "true");
  }
  fila.append(figura);

  const datos = document.createElement("div");
  datos.className = "item-datos";

  const nombre = document.createElement("div");
  nombre.className = "item-nombre";
  nombre.textContent = item.nombre;
  datos.append(nombre);

  if (item.descripcion) {
    const desc = document.createElement("div");
    desc.className = "item-descripcion";
    desc.textContent = item.descripcion;
    datos.append(desc);
  }

  datos.append(dibujarPrecio(item));
  fila.append(datos);

  if (!item.disponible) {
    const etiqueta = document.createElement("span");
    etiqueta.className = "etiqueta-agotado";
    etiqueta.textContent = "Agotado";
    fila.append(etiqueta);
    return fila;
  }

  fila.append(controlDeCantidad(item));
  return fila;
}

/**
 * El precio, con el anterior tachado si hay promoción en curso.
 *
 * **Aquí no se decide nada.** `precio_centavos` ya viene con el descuento
 * aplicado y `precio_antes_centavos` solo llega mientras la promoción está
 * abierta: quien resuelve la franja es la API. El navegador no puede hacerlo,
 * porque su reloj se cambia en dos toques y lo que se cobra no.
 *
 * Por eso tampoco hay un temporizador que quite la promoción a las 3:30: la
 * carta se vuelve a pedir al recargar, y si alguien pulsa «Pagar» pasada la
 * hora, el pedido se crea con el precio que la API diga en ese momento.
 */
function dibujarPrecio(item) {
  const caja = document.createElement("div");
  caja.className = "item-precio";

  if (item.precio_antes_centavos) {
    const antes = document.createElement("s");
    antes.className = "precio-antes";
    antes.textContent = pesos(item.precio_antes_centavos);
    caja.append(antes, " ");
  }

  const ahora = document.createElement("span");
  if (item.precio_antes_centavos) ahora.className = "precio-promo";
  ahora.textContent = pesos(item.precio_centavos);
  caja.append(ahora);

  // La hora de fin solo se escribe cuando hay promoción: «hasta las 15:30» en
  // un producto que vale lo mismo todo el día no significa nada.
  if (item.promocion_hasta) {
    const hasta = document.createElement("span");
    hasta.className = "promo-hasta";
    hasta.textContent = "Promo hasta " + item.promocion_hasta;
    caja.append(hasta);
  }

  return caja;
}

/**
 * «+» mientras no hay ninguno, y −/cantidad/+ en cuanto lo hay.
 *
 * Que sea el mismo sitio y no dos controles distintos evita que el dedo tenga
 * que buscar: la acción siguiente siempre está donde estaba la anterior.
 *
 * Dice «+» y no «Agregar» por una razón medida, no estética: con la palabra,
 * el botón ocupaba 111 px de los 343 de la pantalla y dejaba 97 px para el
 * nombre, así que «Arepa de huevo» partía en dos líneas y la carta entera se
 * leía a trompicones. El signo deja 171 px. La palabra no se pierde: va en
 * `aria-label`, que es lo que lee un lector de pantalla.
 */
function controlDeCantidad(item) {
  const enCarrito = carrito.get(item.item_id);

  if (!enCarrito) {
    const agregar = document.createElement("button");
    agregar.className = "agregar";
    agregar.type = "button";
    agregar.textContent = "+";
    agregar.setAttribute("aria-label", "Agregar " + item.nombre);
    agregar.addEventListener("click", () => cambiarCantidad(item, +1));
    return agregar;
  }

  const grupo = document.createElement("div");
  grupo.className = "cantidad";

  const menos = document.createElement("button");
  menos.className = "secundario";
  menos.type = "button";
  menos.textContent = "\u2212";
  menos.setAttribute("aria-label", "Quitar uno de " + item.nombre);
  menos.addEventListener("click", () => cambiarCantidad(item, -1));

  const cuenta = document.createElement("span");
  cuenta.className = "cantidad-valor";
  cuenta.textContent = String(enCarrito.cantidad);

  const mas = document.createElement("button");
  mas.type = "button";
  mas.textContent = "+";
  mas.setAttribute("aria-label", "Agregar otro " + item.nombre);
  mas.addEventListener("click", () => cambiarCantidad(item, +1));

  // 50 es el tope que el contrato declara por línea: pasarlo daría 422, así
  // que el botón se apaga antes en vez de dejar pedir algo que la API
  // rechazará.
  mas.disabled = enCarrito.cantidad >= 50;

  grupo.append(menos, cuenta, mas);
  return grupo;
}

function cambiarCantidad(item, delta) {
  const actual = carrito.get(item.item_id);
  const cantidad = (actual ? actual.cantidad : 0) + delta;

  if (cantidad <= 0) {
    carrito.delete(item.item_id);
  } else {
    carrito.set(item.item_id, { item, cantidad: Math.min(cantidad, 50) });
  }

  dibujarCarta();
  dibujarBarraCarrito();
}

function totalDelCarrito() {
  let total = 0;
  for (const linea of carrito.values()) {
    total += linea.item.precio_centavos * linea.cantidad;
  }
  return total;
}

function unidadesDelCarrito() {
  let n = 0;
  for (const linea of carrito.values()) n += linea.cantidad;
  return n;
}

function dibujarBarraCarrito() {
  const barra = $("barra-carrito");
  const unidades = unidadesDelCarrito();
  const enLaCarta = $("pantalla-carta").classList.contains("activa");

  barra.classList.toggle("oculto", unidades === 0 || !enLaCarta);
  if (unidades === 0 || !enLaCarta) return;

  $("carrito-cuenta").textContent =
    unidades === 1 ? "1 producto" : unidades + " productos";
  $("carrito-total").textContent = pesos(totalDelCarrito());
}

// --------------------------------------------------------------------------
// Pantalla 2 · crear el pedido
//
// Operación `crearPedido`. Envía solo {item_id, cantidad}: el establecimiento
// se deriva del ítem y el contrato ignora cualquier campo extra (V-01).
// --------------------------------------------------------------------------

/**
 * Lleva el carrito a la pantalla de confirmación.
 *
 * **No crea el pedido todavía.** El pedido nace cuando se pulsa «Pagar», y no
 * antes: así la cola del mostrador no se llena de pedidos que nadie pagó. Lo
 * que se pinta aquí sale del carrito del navegador.
 */
function verPedido() {
  limpiarError();
  if (carrito.size === 0) return;

  metodoElegido = null;
  dibujarLineasDelCarrito();
  dibujarResumenDelCarrito();
  dibujarMetodos();
  mostrar("pedido");
}

function dibujarLineasDelCarrito() {
  const lista = $("lineas-pedido");
  lista.replaceChildren();

  for (const linea of carrito.values()) {
    const fila = document.createElement("li");
    fila.className = "item";

    const datos = document.createElement("div");
    datos.className = "item-datos";

    const nombre = document.createElement("div");
    nombre.className = "item-nombre";
    nombre.textContent = linea.item.nombre;

    const precio = document.createElement("div");
    precio.className = "item-precio";
    precio.textContent =
      linea.cantidad + " \u00d7 " + pesos(linea.item.precio_centavos);

    datos.append(nombre, precio);
    fila.append(datos, controlDeCantidadEnPedido(linea.item));
    lista.append(fila);
  }
}

/**
 * El mismo control de cantidad, pero aquí redibuja esta pantalla.
 *
 * Se puede cambiar el pedido en el último momento sin volver a la carta: es
 * donde la gente se arrepiente, y obligar a navegar hacia atrás para quitar
 * algo es la forma más fácil de perder una venta.
 */
function controlDeCantidadEnPedido(item) {
  const grupo = controlDeCantidad(item);

  grupo.addEventListener("click", () => {
    // Se redibuja después de que el manejador de `controlDeCantidad` haya
    // actualizado el carrito.
    queueMicrotask(() => {
      if (carrito.size === 0) {
        volverALaCarta();
        return;
      }
      dibujarLineasDelCarrito();
      dibujarResumenDelCarrito();
    });
  });

  return grupo;
}

function dibujarResumenDelCarrito() {
  const resumen = $("resumen-pedido");
  resumen.replaceChildren();

  // No se repite aquí la cuenta de productos: las líneas de arriba ya dicen
  // qué hay y cuánto de cada cosa, y una fila «3 productos» sin cifra al lado
  // dibujaba una línea vacía en la rejilla.
  const dtTotal = document.createElement("dt");
  dtTotal.className = "total";
  dtTotal.textContent = "Total";
  const ddTotal = document.createElement("dd");
  ddTotal.className = "total";
  ddTotal.textContent = pesos(totalDelCarrito());
  resumen.append(dtTotal, ddTotal);
}

/**
 * Pone los radios de acuerdo con `metodoElegido` y enciende «Pagar».
 *
 * **Quien marca la pastilla es el CSS**, con `:checked`, no este código: el
 * estado lo tiene el control y no una clase que haya que mantener en sincronía.
 * Aquí solo se refleja el estado de la aplicación en el control, que es lo que
 * hace falta al volver a esta pantalla tras un rechazo —entonces
 * `metodoElegido` vuelve a ser `null` y los radios tienen que quedar en
 * blanco—.
 */
function dibujarMetodos() {
  for (const radio of document.querySelectorAll('input[name="metodo-de-pago"]')) {
    radio.checked = radio.value === metodoElegido;
  }

  const pagar = $("pagar");
  pagar.disabled = metodoElegido === null;
  pagar.textContent = metodoElegido === null
    ? "Elegí un método de pago"
    : "Pagar " + pesos(totalDelCarrito());
}

function volverALaCarta() {
  limpiarError();
  dibujarCarta();
  dibujarBarraCarrito();
  mostrar("carta");
}

/**
 * Crea el pedido con todas las líneas del carrito y abre el cobro.
 *
 * Las dos cosas van juntas a propósito: entre crear el pedido y abrir el
 * intento no hay ninguna decisión que tomar, y partirlo en dos pantallas
 * dejaría pedidos en `pendiente_pago` creados por gente que solo estaba
 * mirando.
 */
async function pagarCarrito() {
  if (metodoElegido === null || carrito.size === 0) return;

  limpiarError();
  const boton = $("pagar");
  boton.disabled = true;
  boton.textContent = "Creando tu pedido\u2026";

  // Un pedido ya creado no se vuelve a crear. Es lo que hace que reintentar
  // tras un rechazo abra **otro cobro del mismo pedido** y no un pedido
  // duplicado — y de paso, que un doble toque en «Pagar» no cueste dos veces.
  if (pedidoActual !== null && pedidoActual.estado === "pendiente_pago") {
    await pagar(metodoElegido);
    return;
  }

  const lineas = [];
  for (const linea of carrito.values()) {
    lineas.push({ item_id: linea.item.item_id, cantidad: linea.cantidad });
  }

  try {
    pedidoActual = await api("/v1/pedidos", {
      method: "POST",
      body: JSON.stringify({ lineas }),
    });
    tokenDelPedido = pedidoActual.token_consulta;
  } catch (e) {
    const mensajes = {
      404: "Uno de los productos ya no existe en la carta.",
      409: e.message, // agotado, repetido o establecimiento cerrado: la API dice cuál
      422: "El pedido no es válido. Revisá las cantidades.",
    };
    fallar(mensajes[e.status] || "No se pudo crear el pedido: " + e.message);
    dibujarMetodos();
    return;
  }

  await pagar(metodoElegido);
}

/**
 * Resumen de un pedido **ya creado**, con una fila por línea.
 *
 * Devuelve el elemento en vez de escribir en uno fijo porque la pantalla de
 * resultado y la de confirmación son dos sitios distintos: atarlo a un `id`
 * obligaba a duplicar el marcado.
 *
 * Desde la versión 3.0.0 del contrato el pedido trae `lineas[]`, así que ya no
 * hay un producto que mostrar sino varios.
 */
function dibujarResumen(pedido) {
  const resumen = document.createElement("dl");
  resumen.className = "resumen";

  for (const linea of pedido.lineas) {
    const dt = document.createElement("dt");
    dt.textContent = linea.cantidad + " \u00d7 " + linea.nombre_item;
    const dd = document.createElement("dd");
    dd.textContent = pesos(linea.total_linea_centavos);
    resumen.append(dt, dd);
  }

  const dtTotal = document.createElement("dt");
  dtTotal.className = "total";
  dtTotal.textContent = "Total";
  const ddTotal = document.createElement("dd");
  ddTotal.className = "total";
  ddTotal.textContent = pesos(pedido.total_centavos);
  resumen.append(dtTotal, ddTotal);
  return resumen;
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
    referenciaDelCobro = intento.referencia_pago;

    mostrar("espera");
    ofrecerLaPasarela(intento.url_checkout);
    consultarEstadoPeriodicamente();
  } catch (e) {
    const mensajes = {
      404: "El pedido ya no existe.",
      409: "Este pedido ya no admite pago.",
      422: "El método de pago no es válido.",
    };
    fallar(mensajes[e.status] || `No se pudo iniciar el pago: ${e.message}`);
  }
}

/**
 * Pone a la vista el enlace al checkout, si el checkout es nuestro.
 *
 * Un despliegue con pasarela de verdad redirige: la persona sale del sitio,
 * paga en otro dominio y vuelve. Aquí no se redirige **porque la pasarela
 * simulada vive en este mismo sitio**, y salir de la página perdería el pedido
 * que se acaba de crear; se abre en otra pestaña y esta se queda sondeando.
 *
 * La distinción se hace por origen y no por una variable de configuración
 * aparte: la API ya decide a dónde mandar a pagar, y una segunda bandera en el
 * frontend podría contradecirla.
 */
function ofrecerLaPasarela(urlCheckout) {
  const enlace = $("ir-a-pasarela");

  let esNuestra = false;
  try {
    esNuestra = new URL(urlCheckout, location.href).origin === location.origin;
  } catch {
    // Una URL que no se puede analizar no es la nuestra.
  }

  enlace.classList.toggle("oculto", !esNuestra);

  if (!esNuestra) {
    // Contra una pasarela real, aquí iría la redirección.
    console.info("Checkout de la pasarela:", urlCheckout);
    return;
  }

  enlace.href = urlCheckout;
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
  lanzar(consultarEstado());
}

/**
 * Pregunta por el cobro y, si fue rechazado, lo cuenta.
 *
 * Solo se llama cuando el pedido sigue en `pendiente_pago`, que es el único
 * caso en que los dos estados son indistinguibles desde el pedido. Mientras
 * el cobro también esté pendiente no se hace nada: la pantalla de espera ya
 * dice lo correcto.
 *
 * Un fallo aquí **no se muestra**. Esta consulta es un extra sobre el sondeo
 * del pedido, y una pantalla de espera que empieza a enseñar errores de red
 * mientras espera es peor que una que espera.
 */
async function mirarSiElCobroFueRechazado() {
  if (referenciaDelCobro === null) return;

  let intento;
  try {
    intento = await api(`/v1/pagos/intentos/${referenciaDelCobro}`);
  } catch {
    return;
  }

  if (intento.estado_pago !== "rechazado") return;

  detenerConsultas();
  mostrarCobroRechazado();
}

function mostrarCobroRechazado() {
  $("titulo-resultado").textContent = "El pago fue rechazado";

  const cuerpo = $("cuerpo-resultado");
  cuerpo.replaceChildren();

  const linea = document.createElement("div");
  linea.className = "estado-linea";
  const punto = document.createElement("span");
  punto.className = "punto mal";
  const texto = document.createElement("span");
  // No se afirma por qué: la pasarela no nos lo dice, e inventar un motivo
  // —«fondos insuficientes»— sería peor que no darlo.
  texto.textContent =
    "Tu pedido sigue guardado y no se te cobró nada. Podés intentarlo otra " +
    "vez, con el mismo método o con otro.";
  linea.append(punto, texto);
  cuerpo.append(linea);

  cuerpo.append(dibujarResumen(pedidoActual));

  // Vuelve a la pantalla del pedido, donde están los métodos y «Pagar». El
  // pedido ya existe, así que ese botón abre **otro cobro del mismo pedido**.
  const reintentar = document.createElement("button");
  reintentar.id = "reintentar-pago";
  reintentar.textContent = "Intentar el pago otra vez";
  reintentar.addEventListener("click", () => {
    limpiarError();
    metodoElegido = null;
    dibujarLineasDelCarrito();
    dibujarResumenDelCarrito();
    dibujarMetodos();
    mostrar("pedido");
  });
  cuerpo.append(reintentar);

  mostrar("resultado");
}

function detenerConsultas() {
  if (temporizadorConsulta !== null) {
    clearInterval(temporizadorConsulta);
    temporizadorConsulta = null;
  }
}

async function consultarEstado() {
  try {
    // El token va en una cabecera y no en la dirección: una URL acaba en los
    // registros del servidor y del proxy, y este token es lo que permite leer
    // el código de canje.
    const pedido = await api(`/v1/pedidos/${pedidoActual.pedido_id}`, {
      headers: { "X-Token-Pedido": tokenDelPedido },
    });
    pedidoActual = pedido;

    // El pedido sigue en `pendiente_pago`. Eso **no** quiere decir que no haya
    // pasado nada: un cobro rechazado deja el pedido exactamente igual que uno
    // que todavía no ha confirmado. Se pregunta por el cobro, que es quien lo
    // sabe.
    //
    // El orden importa y no es casual. El pedido se consulta **primero**
    // porque es quien tiene el código de canje: `procesar_evento` escribe el
    // pedido antes que el intento a propósito —«falla hacia el cliente»— y en
    // esa ventana el pedido ya está pagado mientras el cobro figura pendiente.
    // Preguntando antes por el cobro, quien ya tiene su código seguiría
    // esperando.
    if (pedido.estado === "pendiente_pago") {
      await mirarSiElCobroFueRechazado();
      return;
    }

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

  // El recibo: qué se compró y cuánto. Antes solo decía «Total pagado: …», que
  // además mentía en los estados donde no se pagó nada —un pedido cancelado, o
  // uno cuyo cobro todavía no ha confirmado la pasarela—. La fila «Total» del
  // resumen dice la cifra sin afirmar que haya cambiado de manos.
  cuerpo.append(dibujarResumen(pedido));
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

// Elegir un metodo ya no cobra: lo marca. El cobro lo dispara «Pagar».
//
// Se escucha `change` y no `click` porque con radios de verdad la selección
// también cambia con las flechas del teclado, y un `click` no se dispara
// entonces. Es justo lo que el `role="radio"` a mano no daba.
for (const radio of document.querySelectorAll('input[name="metodo-de-pago"]')) {
  radio.addEventListener("change", () => {
    if (!radio.checked) return;
    metodoElegido = radio.value;
    dibujarMetodos();
  });
}

$("pagar").addEventListener("click", () => lanzar(pagarCarrito()));

$("ver-pedido").addEventListener("click", verPedido);

$("volver-a-carta").addEventListener("click", volverALaCarta);

// Al volver a esta pestaña se consulta ya, sin esperar al siguiente sondeo.
//
// No sustituye al sondeo ni lo acelera: el intervalo sigue siendo el que es, y
// la confirmación llegaría igual sin esto. Lo que evita es la espera muerta de
// hasta un intervalo entero justo después de pagar en la otra pestaña, que es
// cuando más se mira la pantalla.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") return;
  if (temporizadorConsulta === null) return;
  lanzar(consultarEstado());
});

$("dejar-de-esperar").addEventListener("click", () => {
  detenerConsultas();
  mostrarResultado(pedidoActual);
});

$("nuevo-pedido").addEventListener("click", () => {
  pedidoActual = null;
  tokenDelPedido = null;
  referenciaDelCobro = null;
  // El carrito se vacia: sin esto el pedido siguiente empezaria con lo que la
  // persona acaba de pagar y recoger.
  carrito.clear();
  metodoElegido = null;
  dibujarBarraCarrito();
  limpiarError();
  lanzar(cargarCarta());
});

lanzar(comprobarSalud());
