// Panel del mostrador.
//
// Consume cuatro operaciones declaradas en `contracts/consumidor-web.yaml`:
// `iniciarSesion`, `cerrarSesion`, `listarPedidosDeEstablecimiento` y
// `cambiarEstadoDePedido`. Si el proveedor deja de emitir un campo de los
// declarados, su pipeline falla.
//
// Cubre ESC-03 (gestionar el estado de un pedido en ≤10 s y ≤3 interacciones,
// sin recargar la página) y, desde la 2.0.0 del contrato, ESC-04: entregar
// exige el código de recogida.

const $ = (id) => document.getElementById(id);

// Cada cuánto se refresca la cola sola. En hora pico entran pedidos mientras
// se atiende, y obligar a pulsar «Refrescar» para verlos gastaría una de las
// tres interacciones que concede ESC-03.
const MS_ENTRE_REFRESCOS = 8000;

// Dónde vive el token mientras dura la pestaña.
//
// `sessionStorage` y no `localStorage`: el panel se usa en un equipo
// compartido del mostrador, y una sesión que sobrevive al cierre del navegador
// es una sesión que hereda el turno siguiente. Al cerrar la pestaña se va.
//
// Y no una cookie `HttpOnly`, que es la respuesta de manual: el sitio es
// estático y vive en otro origen que la API, así que la cookie necesitaría
// `SameSite=None`, CORS con credenciales y defensa contra CSRF. Con un token
// explícito nada se envía solo desde otro sitio y el CSRF deja de existir como
// clase de problema.
//
// El costo es real y está anotado como [V-12](../docs/violaciones.md): un fallo
// de XSS podría leer esto. Lo que lo acota es que esta pantalla **no renderiza
// HTML de nadie** —todo el texto entra por `textContent`, nunca por
// `innerHTML`— y eso es una propiedad de este archivo que hay que mantener, no
// una garantía del mecanismo. Un solo `innerHTML` futuro la elimina.
const CLAVE_TOKEN = "pideutb.sesion";

let temporizador = null;
let sesion = null;   // { token, usuario }

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
// llamar a la API sin pasar por esta página — con una sesión válida, que es lo
// que cambió en la semana 10.
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
  // `pideCodigo` es lo que distingue esta transición de las otras tres: el
  // servidor la rechaza sin el código de recogida (ESC-04).
  listo_para_recoger: [{ estado: "entregado", texto: "Entregado", pideCodigo: true }],
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
  // `...undefined` dentro de un objeto literal ya no hace nada, así que el
  // `|| {}` que había aquí era código muerto que parecía defensivo.
  const cabeceras = { "Content-Type": "application/json", ...opciones.headers };
  if (sesion) cabeceras.Authorization = `Bearer ${sesion.token}`;

  const respuesta = await fetch(`${CONFIG.API}${ruta}`, { ...opciones, headers: cabeceras });

  // 204 no trae cuerpo, y `respuesta.json()` sobre un cuerpo vacío lanza.
  if (respuesta.status === 204) return null;
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
// La sesión
// --------------------------------------------------------------------------

function leerSesionGuardada() {
  try {
    const crudo = sessionStorage.getItem(CLAVE_TOKEN);
    if (!crudo) return null;
    const guardada = JSON.parse(crudo);
    // Se comprueba la forma antes de confiar en ella: un valor a medio escribir
    // dejaría la pantalla pidiendo una cola con un token inservible, y el
    // usuario vería un error en vez del formulario de ingreso.
    return guardada?.token && guardada?.usuario ? guardada : null;
  } catch {
    // `sessionStorage` lanza en modo privado con el almacenamiento bloqueado, y
    // `JSON.parse` lanza con un valor corrupto. Ninguno de los dos casos debe
    // impedir ingresar: se trata como «no hay sesión».
    return null;
  }
}

function guardarSesion(nueva) {
  sesion = nueva;
  try {
    if (nueva) sessionStorage.setItem(CLAVE_TOKEN, JSON.stringify(nueva));
    else sessionStorage.removeItem(CLAVE_TOKEN);
  } catch {
    // Sin almacenamiento, la sesión vive solo en memoria: se pierde al
    // recargar, pero el turno funciona. Degradar es mejor que no entrar.
  }
}

function mostrarPantalla() {
  const dentro = Boolean(sesion);
  $("ingreso").classList.toggle("oculto", dentro);
  $("operacion").classList.toggle("oculto", !dentro);

  if (dentro) {
    $("quien").textContent =
      `${sesion.usuario.correo} · establecimiento ${sesion.usuario.establecimiento_id}`;
  } else {
    // Al salir se borra lo pintado. Dejar la cola visible detrás del
    // formulario mostraría pedidos de un turno que ya terminó.
    $("cola").innerHTML = "";
    $("cola-vacia").classList.add("oculto");
    $("ultima-carga").textContent = "";
    huellaPintada = null;
    clearInterval(temporizador);
  }
}

async function ingresar(evento) {
  evento.preventDefault();
  $("entrar").disabled = true;

  try {
    const abierta = await api("/v1/sesiones", {
      method: "POST",
      body: JSON.stringify({
        correo: $("correo").value.trim(),
        contrasena: $("contrasena").value,
      }),
    });

    // La contraseña se borra del formulario en cuanto deja de hacer falta.
    // Mientras esté en el campo, sigue estando en el DOM.
    $("contrasena").value = "";

    guardarSesion({ token: abierta.token, usuario: abierta.usuario });
    limpiarError();
    mostrarPantalla();
    await cargarCola();
    reiniciarRefresco();
  } catch (e) {
    // El `401` es el caso normal de quien escribe mal la contraseña, y el
    // mensaje del servidor **no distingue** entre correo desconocido y clave
    // incorrecta. Se muestra tal cual: inventar aquí un mensaje más útil
    // convertiría esta pantalla en el oráculo que la API evita ser.
    fallar(e.status === 401 ? e.message : `No se pudo entrar: ${e.message}`);
  } finally {
    $("entrar").disabled = false;
  }
}

async function salir() {
  $("salir").disabled = true;
  try {
    // Se avisa al servidor para que la sesión deje de valer de verdad. Borrar
    // solo el token local la dejaría viva ocho horas más en la tabla.
    await api("/v1/sesiones", { method: "DELETE" });
  } catch {
    // Si la llamada falla —red caída, sesión ya caducada— se sale igual: lo que
    // el usuario pidió es dejar de estar dentro en **este** equipo, y eso
    // depende de borrar el token de aquí.
  } finally {
    guardarSesion(null);
    limpiarError();
    mostrarPantalla();
    $("salir").disabled = false;
  }
}

function caducar() {
  guardarSesion(null);
  mostrarPantalla();
  fallar("La sesión caducó o se cerró en otro equipo. Volvé a entrar.");
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
    estado.appendChild(texto);
    datos.appendChild(estado);

    // El código **no** se muestra en el panel desde la 2.0.0.
    //
    // Antes se pintaba junto al estado, para que quien atiende lo viera. Eso
    // vacía ESC-04 de contenido: si el código está en la pantalla del
    // mostrador, pedirlo al cliente es un trámite que se puede saltar leyendo
    // la propia lista. Ahora hay que pedírselo, y el servidor lo compara.
    texto.textContent = `${ETIQUETA_ESTADO[pedido.estado] || pedido.estado} · ${pesos(pedido.total_centavos)}`;

    fila.appendChild(datos);

    const acciones = document.createElement("div");
    acciones.className = "acciones";
    for (const accion of ACCIONES_POR_ESTADO[pedido.estado] || []) {
      const boton = document.createElement("button");
      boton.textContent = accion.texto;
      if (accion.secundario) boton.className = "secundario";
      boton.addEventListener("click", () =>
        lanzar(cambiarEstado(pedido.pedido_id, accion, boton))
      );
      acciones.appendChild(boton);
    }
    fila.appendChild(acciones);

    cola.appendChild(fila);
  }
}

/**
 * Refresca la cola.
 *
 * `conservarError` existe por un fallo que solo se ve en un navegador: cuando
 * el código de recogida no coincide, el manejador escribe el mensaje y después
 * refresca la lista para mostrar la realidad. Ese refresco funcionaba, así que
 * limpiaba el error — y lo que veía quien atiende era **nada**. Tecleaba un
 * código equivocado, pulsaba «Entregar» y la pantalla se quedaba igual, que es
 * peor que un error: parece que el clic no se registró.
 *
 * Quien llama tras un fallo pide conservar el mensaje. Quien refresca por su
 * cuenta —el temporizador, el botón— sigue limpiándolo, porque ahí sí
 * significa que lo anterior ya se resolvió.
 */
async function cargarCola(conservarError = false) {
  if (!sesion) return;

  try {
    // Sin `establecimiento_id`: sale de la sesión. Mandarlo sería pedir
    // permiso para algo que ya está decidido, y pedir otro responde 403.
    const cola = await api("/v1/pedidos");
    if (!conservarError) limpiarError();
    pintar(cola.pedidos);
    $("ultima-carga").textContent =
      `Actualizado ${new Date().toLocaleTimeString("es-CO")}`;
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      caducar();
      return;
    }
    fallar(`No se pudo cargar la cola: ${e.message}`);
  }
}

// --------------------------------------------------------------------------
// El código de recogida
// --------------------------------------------------------------------------

/** Abre el diálogo y resuelve con el código, o con `null` si se cancela. */
function pedirCodigo(pedidoId) {
  const dialogo = $("dialogo-canje");
  const campo = $("codigo-canje");

  $("titulo-canje").textContent = `Código del pedido #${pedidoId}`;
  campo.value = "";

  // `<dialog>` sin `showModal` no atrapa el foco ni el Escape. Si el navegador
  // no lo soporta, se cae a `prompt`: peor, pero operable. Un mostrador sin
  // forma de entregar es peor que un cuadro de diálogo feo.
  if (typeof dialogo.showModal !== "function") {
    const escrito = prompt(`Código del pedido #${pedidoId}`);
    return Promise.resolve(escrito ? escrito.trim() : null);
  }

  return new Promise((resolver) => {
    const alCerrar = () => {
      dialogo.removeEventListener("close", alCerrar);
      resolver(dialogo.returnValue === "confirmar" && campo.value.trim()
        ? campo.value.trim()
        : null);
    };
    dialogo.addEventListener("close", alCerrar);
    dialogo.returnValue = "cancelar";
    dialogo.showModal();
    campo.focus();
  });
}

async function cambiarEstado(pedidoId, accion, boton) {
  let codigo = null;
  if (accion.pideCodigo) {
    codigo = await pedirCodigo(pedidoId);
    // Cancelar no es un error: no se avisa de nada y el pedido se queda donde
    // estaba. Quien abrió el diálogo sin tener el código delante solo cierra.
    if (!codigo) return;
  }

  // Se desactiva mientras vuela la petición: en hora pico, dos pulsaciones
  // rápidas enviarían la misma transición dos veces y la segunda respondería
  // 409, que asusta sin motivo.
  boton.disabled = true;

  try {
    const cuerpo = { estado: accion.estado };
    if (codigo) cuerpo.codigo_canje = codigo;

    await api(`/v1/pedidos/${pedidoId}/estado`, {
      method: "POST",
      body: JSON.stringify(cuerpo),
    });
    limpiarError();
    huellaPintada = null;   // el estado cambió: repintar sí o sí
    await cargarCola();
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      caducar();
      return;
    }
    if (e.status === 409) {
      // El 409 cubre dos causas que el panel trata igual: la transición ya no
      // corresponde porque otra persona movió el pedido, o el código no es el
      // de ese pedido. En los dos casos lo útil no es insistir sino mostrar la
      // realidad, así que se refresca la cola y se explica.
      fallar(`El pedido #${pedidoId} no se pudo mover: ${e.message} Se actualizó la cola.`);
      await refrescarTrasFallo();
      return;
    }
    if (e.status === 404) {
      // Un pedido de otro establecimiento responde 404 igual que uno
      // inexistente, a propósito (ADR-0007). Desde esta pantalla la causa real
      // es casi siempre que la cola estaba vieja.
      fallar(`El pedido #${pedidoId} ya no está en tu cola. Se actualizó la lista.`);
      await refrescarTrasFallo();
      return;
    }
    fallar(`No se pudo actualizar el pedido #${pedidoId}: ${e.message}`);
    boton.disabled = false;
  }
}

/**
 * Vuelve a cargar la cola después de un intento fallido, sin borrar el aviso.
 *
 * Fuerza el repintado. Sin eso, el otro fallo que apareció en el navegador:
 * cuando el código no coincide, la cola no ha cambiado, así que `pintar`
 * cortaba por la huella y el botón que se había desactivado antes de llamar
 * **no se volvía a crear**. Quedaba gris para siempre, y la única salida era
 * recargar la página en mitad de la entrega.
 */
async function refrescarTrasFallo() {
  huellaPintada = null;
  await cargarCola(true);
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
  if (sesion) temporizador = setInterval(() => lanzar(cargarCola()), MS_ENTRE_REFRESCOS);
}

$("formulario-ingreso").addEventListener("submit", (e) => lanzar(ingresar(e)));
$("salir").addEventListener("click", () => lanzar(salir()));
$("refrescar").addEventListener("click", () => lanzar(cargarCola()));
$("cancelar-canje").addEventListener("click", () => $("dialogo-canje").close("cancelar"));

// No se refresca mientras la pestaña está oculta: con el plan gratuito, cada
// petición evitada es tráfico que no consume la cuota, y un panel en segundo
// plano no lo está mirando nadie.
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    clearInterval(temporizador);
  } else if (sesion) {
    lanzar(cargarCola());
    reiniciarRefresco();
  }
});

sesion = leerSesionGuardada();
mostrarPantalla();
if (sesion) {
  // No se comprueba el token contra la API antes de pintar: si ya no vale, la
  // primera carga responde 401 y `caducar()` devuelve al formulario. Validarlo
  // antes sería una petición más antes de que aparezca nada.
  lanzar(cargarCola());
  reiniciarRefresco();
} else {
  $("correo").focus();
}
