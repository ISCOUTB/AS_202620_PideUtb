// Panel del mostrador.
//
// Consume dos operaciones declaradas en `contracts/consumidor-web.yaml`:
// `listarPedidosDeEstablecimiento` y `cambiarEstadoDePedido`. Si el proveedor
// deja de emitir un campo de los declarados, su pipeline falla.
//
// Cubre ESC-03: gestionar el estado de un pedido en ≤10 s y ≤3 interacciones,
// sin recargar la página. De ahí vienen casi todas las decisiones de abajo.

const $ = (id) => document.getElementById(id);

// Cada cuánto se refresca la cola sola. En hora pico entran pedidos mientras
// se atiende, y obligar a pulsar «Refrescar» para verlos gastaría una de las
// tres interacciones que concede ESC-03.
const MS_ENTRE_REFRESCOS = 8000;

let temporizador = null;

// Huella de lo último que se pintó. Sirve para NO repintar cuando la cola no
// ha cambiado, que es lo habitual entre dos refrescos.
//
// No es una optimización: es corrección. Repintar destruye y recrea los
// botones, así que uno puede desaparecer bajo el dedo de quien atiende justo
// cuando lo va a pulsar. Con prisa y con la lista moviéndose, eso termina en
// un «Cancelar» pulsado por accidente.
let huellaPintada = null;

// --------------------------------------------------------------------------
// Qué botones ofrece cada estado.
//
// Es la misma máquina de estados que `service.TRANSICIONES_DEL_MOSTRADOR`,
// pero aquí sirve para otra cosa: **no mostrar botones que el servidor va a
// rechazar**. Un botón que siempre da error enseña a desconfiar de la
// pantalla.
//
// El servidor valida igual. Esto es comodidad, no seguridad: cualquiera puede
// llamar a la API sin pasar por esta página.
// --------------------------------------------------------------------------
const ACCIONES_POR_ESTADO = {
  pendiente_pago: [],
  pagado: [
    { estado: "en_preparacion", texto: "Empezar a preparar" },
    { estado: "cancelado", texto: "Cancelar", secundario: true },
  ],
  en_preparacion: [
    { estado: "listo_para_recoger", texto: "Listo para recoger" },
    { estado: "cancelado", texto: "Cancelar", secundario: true },
  ],
  listo_para_recoger: [{ estado: "entregado", texto: "Entregado" }],
  entregado: [],
  cancelado: [],
};

const ETIQUETA_ESTADO = {
  pendiente_pago: "Esperando pago",
  pagado: "Pagado",
  en_preparacion: "En preparación",
  listo_para_recoger: "Listo para recoger",
  entregado: "Entregado",
  cancelado: "Cancelado",
};

const PUNTO_ESTADO = {
  pendiente_pago: "espera",
  pagado: "ok",
  en_preparacion: "espera",
  listo_para_recoger: "ok",
  entregado: "ok",
  cancelado: "mal",
};

const pesos = (centavos) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 })
    .format(centavos / 100);

// --------------------------------------------------------------------------
// Llamadas a la API
// --------------------------------------------------------------------------

async function api(ruta, opciones = {}) {
  const respuesta = await fetch(`${CONFIG.API}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });

  if (respuesta.ok) return respuesta.json();

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

function fallar(mensaje) {
  $("error").textContent = mensaje;
  $("error").classList.remove("oculto");
}

function limpiarError() {
  $("error").classList.add("oculto");
}

// --------------------------------------------------------------------------
// Pintar la cola
// --------------------------------------------------------------------------

function pintar(pedidos) {
  // Solo lo que se muestra entra en la huella: si el servidor añadiera un
  // campo que esta pantalla no usa, no tiene por qué provocar un repintado.
  const huella = JSON.stringify(
    pedidos.map((p) => [p.pedido_id, p.estado, p.cantidad, p.nombre_item, p.total_centavos, p.codigo_canje])
  );
  if (huella === huellaPintada) return;
  huellaPintada = huella;

  const cola = $("cola");
  cola.innerHTML = "";
  $("cola-vacia").classList.toggle("oculto", pedidos.length > 0);

  for (const pedido of pedidos) {
    const fila = document.createElement("li");
    fila.className = "item pedido";

    const datos = document.createElement("div");
    datos.className = "item-datos";

    const titulo = document.createElement("div");
    titulo.className = "item-nombre";
    titulo.textContent = `#${pedido.pedido_id} · ${pedido.cantidad} × ${pedido.nombre_item}`;
    datos.appendChild(titulo);

    const estado = document.createElement("div");
    estado.className = "estado-linea";
    const punto = document.createElement("span");
    punto.className = `punto ${PUNTO_ESTADO[pedido.estado] || "espera"}`;
    estado.appendChild(punto);
    const texto = document.createElement("span");
    texto.className = "item-precio";
    // El código de canje se muestra junto al estado porque es lo que el
    // cliente va a decir en el mostrador para identificarse.
    texto.textContent = `${ETIQUETA_ESTADO[pedido.estado] || pedido.estado} · ${pesos(pedido.total_centavos)}`
      + (pedido.codigo_canje ? ` · código ${pedido.codigo_canje}` : "");
    estado.appendChild(texto);
    datos.appendChild(estado);

    fila.appendChild(datos);

    const acciones = document.createElement("div");
    acciones.className = "acciones";
    for (const accion of ACCIONES_POR_ESTADO[pedido.estado] || []) {
      const boton = document.createElement("button");
      boton.textContent = accion.texto;
      if (accion.secundario) boton.className = "secundario";
      boton.addEventListener("click", () => cambiarEstado(pedido.pedido_id, accion.estado, boton));
      acciones.appendChild(boton);
    }
    fila.appendChild(acciones);

    cola.appendChild(fila);
  }
}

async function cargarCola() {
  const establecimiento = Number($("establecimiento").value);
  if (!establecimiento || establecimiento < 1) {
    fallar("Indicá un número de establecimiento válido.");
    return;
  }

  try {
    const cola = await api(`/v1/pedidos?establecimiento_id=${establecimiento}`);
    limpiarError();
    pintar(cola.pedidos);
    $("ultima-carga").textContent =
      `Actualizado ${new Date().toLocaleTimeString("es-CO")}`;
  } catch (e) {
    fallar(`No se pudo cargar la cola: ${e.message}`);
  }
}

async function cambiarEstado(pedidoId, estado, boton) {
  // Se desactiva mientras vuela la petición: en hora pico, dos pulsaciones
  // rápidas enviarían la misma transición dos veces y la segunda respondería
  // 409, que asusta sin motivo.
  boton.disabled = true;

  try {
    await api(`/v1/pedidos/${pedidoId}/estado`, {
      method: "POST",
      body: JSON.stringify({ estado }),
    });
    limpiarError();
    huellaPintada = null;   // el estado cambió: repintar sí o sí
    await cargarCola();
  } catch (e) {
    if (e.status === 409) {
      // 409 casi siempre significa que otra persona ya movió el pedido desde
      // otra pantalla. Lo útil no es insistir, es mostrar la realidad: se
      // refresca la cola y se explica.
      fallar(`El pedido #${pedidoId} ya había cambiado: ${e.message}. Se actualizó la cola.`);
      await cargarCola();
    } else {
      fallar(`No se pudo actualizar el pedido #${pedidoId}: ${e.message}`);
      boton.disabled = false;
    }
  }
}

// --------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------


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

function reiniciarRefresco() {
  if (temporizador) clearInterval(temporizador);
  temporizador = setInterval(cargarCola, MS_ENTRE_REFRESCOS);
}

$("refrescar").addEventListener("click", cargarCola);
$("establecimiento").addEventListener("change", () => {
  huellaPintada = null;   // es otra cola: nada de lo pintado sirve
  lanzar(cargarCola());
  reiniciarRefresco();
});

// No se refresca mientras la pestaña está oculta: con el plan gratuito, cada
// petición evitada es tráfico que no consume la cuota, y un panel en segundo
// plano no lo está mirando nadie.
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    clearInterval(temporizador);
  } else {
    lanzar(cargarCola());
    reiniciarRefresco();
  }
});

lanzar(cargarCola());
reiniciarRefresco();
