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

  // La barra de navegación no se esconde nunca: es el caparazón, no contenido.
  // Lo que cambia es qué destino está marcado y cuáles se pueden pulsar, y eso
  // depende de la pantalla activa, así que se recalcula acá.
  dibujarNavegacion();

  // La advertencia de «vas a perder el código» pertenece a la pantalla del
  // resultado. Irse a otra dejándola abierta y volver la encontraría a medias,
  // preguntando por una decisión que quien vuelve ya no recuerda haber
  // empezado a tomar.
  if (nombre !== "resultado") cerrarLaAdvertencia();
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
 *
 * **Quien arma la ruta codifica lo que meta dentro.** `ruta` llega ya armada y
 * desde aquí no se distingue qué parte es estructura y qué parte es un valor,
 * así que esta función no puede hacerlo por nadie. Y hace falta: interpolar un
 * valor sin codificar lo asciende a estructura —una barra o un `..` dentro del
 * valor dejan de ser texto y pasan a ser dirección, que es otra dirección—.
 * Vale tanto para lo que sale del almacenamiento, que cualquiera edita desde
 * la consola, como para lo que llega de la API, que es de fiar hasta el día
 * que deje de serlo. Cuesta una llamada a `encodeURIComponent`.
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
 * **Ya no vive solo en memoria.** Se guarda junto al pedido —más abajo— para
 * que recargar la página, o volver desde la pasarela, no borre el código de
 * recogida. Lo que sigue sin existir es «buscar mi pedido»: se recupera lo que
 * este navegador guardó, no una cuenta de cliente, porque no hay cuentas.
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

/**
 * A dónde manda la API a pagar este cobro.
 *
 * Se recuerda por lo mismo que la referencia: al recuperar un pedido que quedó
 * a medias hay que poder volver a ofrecer la pasarela, y la API dice esta
 * dirección **una sola vez**, al abrir el intento.
 */
let urlDelCheckout = null;

/** Categoría activa del filtro. `null` = todas. */
let categoriaActiva = null;

/** La carta completa, para filtrar sin volver a pedirla. */
let cartaCompleta = [];

// --------------------------------------------------------------------------
// El pedido en curso, fuera de la memoria de la pestaña
//
// Hasta acá el pedido vivía solo en las variables de arriba, y eso se leía como
// tres defectos distintos cuando en realidad era uno:
//
//   · recargar la página borraba el código de un pedido ya pagado;
//   · volver desde la pasarela aterrizaba en la portada, porque la pasarela
//     abre **otra pestaña**, y otra pestaña es otra memoria: no sabe que haya
//     un pedido en marcha;
//   · «Hacer otro pedido» lo tiraba sin preguntar.
//
// El defecto único: el único sitio donde vivía el código de recogida era una
// variable que cualquier navegación tiraba a la basura. Quien ya había pagado
// se quedaba sin lo que había comprado, y lo descubría en el mostrador.
//
// `localStorage` y no `sessionStorage`, que es el almacenamiento más corto y
// por tanto el que habría preferido: `sessionStorage` **no viaja** a la pestaña
// que abre `target="_blank"` con `rel="noopener"`, que es exactamente cómo se
// abre la pasarela. Elegirlo habría dejado el segundo defecto sin arreglar.
//
// Lo que se guarda son cuatro datos del pedido propio —ni sesión, ni cuenta, ni
// nada de otra persona—, y **caduca**. La caducidad no es ceremonia: en un
// teléfono prestado, un pedido pagado y nunca recogido dejaría el código de
// alguien en la pantalla del siguiente que abra la carta. Seis horas es más que
// una comida y menos que un día.
//
// Lo que esto **no** hace es permitir recuperar el pedido desde otro aparato:
// se lee lo que este navegador escribió. Sigue sin haber dónde buscarlo.
// --------------------------------------------------------------------------

const LLAVE_DEL_PEDIDO = "pideutb.pedido";
const HORAS_QUE_DURA_LO_GUARDADO = 6;

/**
 * Deja constancia del pedido en curso.
 *
 * Se llama en los dos momentos en que aparece algo que la API no vuelve a
 * decir: al crear el pedido —que es cuando entrega el token, una sola vez— y al
 * abrir el cobro —que es cuando entrega la referencia y la dirección del
 * checkout—.
 *
 * Un fallo al escribir **no se cuenta y no rompe nada**: en modo privado, con el
 * almacenamiento lleno o con el sitio sin permiso para guardar, `setItem` lanza.
 * El pedido sigue en memoria y la pestaña funciona como funcionaba antes de
 * este arreglo, que era peor pero no era inservible.
 */
function guardarElPedido() {
  if (pedidoActual === null || tokenDelPedido === null) return;

  try {
    localStorage.setItem(LLAVE_DEL_PEDIDO, JSON.stringify({
      pedido_id: pedidoActual.pedido_id,
      token_consulta: tokenDelPedido,
      referencia_pago: referenciaDelCobro,
      url_checkout: urlDelCheckout,
      guardado_en: Date.now(),
    }));
  } catch {
    // Ver arriba: se degrada a lo de antes, en silencio.
  }
}

/** Borra lo guardado. Se llama cuando el código ya no le sirve a nadie. */
function olvidarElPedido() {
  try {
    localStorage.removeItem(LLAVE_DEL_PEDIDO);
  } catch {
    // Ídem.
  }
}

/**
 * Lo guardado, si lo hay, si se entiende y si todavía vale.
 *
 * Cualquier cosa rara —otra versión del sitio que guardó otra forma, alguien
 * editando el almacenamiento a mano, un reloj que se movió hacia atrás— sale
 * por la misma puerta: se descarta y se olvida. Un pedido que no se puede
 * interpretar es un pedido que no existe.
 */
function leerElPedidoGuardado() {
  let guardado = null;
  try {
    guardado = JSON.parse(localStorage.getItem(LLAVE_DEL_PEDIDO) || "null");
  } catch {
    olvidarElPedido();
    return null;
  }

  // Sin nada guardado no hay nada que olvidar. A partir de acá sí: lo que haya
  // y no se entienda se tira, porque volver a leerlo en cada carga para volver
  // a rechazarlo no ayuda a nadie.
  if (guardado === null) return null;

  // El identificador vuelve **convertido a número**, no tal como se leyó.
  //
  // De acá sale hacia la ruta de una consulta —`/v1/pedidos/${pedido_id}`— y
  // lo que hay en el almacenamiento es texto que cualquiera edita desde la
  // consola del navegador en dos segundos. Sin convertirlo, un `pedido_id` de
  // `1/../../../v1/sesiones` armaba una dirección distinta de la que esta línea
  // aparenta, y el sitio la pedía sin rechistar.
  //
  // La API declara el identificador como entero, así que un entero es lo único
  // que se acepta. Con la conversión por delante, a la URL solo puede llegar
  // una cifra: deja de ser una cuestión de qué texto se filtra.
  const id = Number(guardado.pedido_id);

  if (!Number.isSafeInteger(id) || id <= 0 || !guardado.token_consulta) {
    olvidarElPedido();
    return null;
  }

  const horas = (Date.now() - guardado.guardado_en) / 3600000;

  // La condición va negada a propósito. Con un `guardado_en` ausente o absurdo
  // la resta da `NaN`, toda comparación con `NaN` es falsa, y así el pedido se
  // descarta. Escrito al derecho —`if (horas >= HORAS...) descartar`— el `NaN`
  // también daría falso y lo daría por bueno para siempre.
  if (!(horas >= 0 && horas < HORAS_QUE_DURA_LO_GUARDADO)) {
    olvidarElPedido();
    return null;
  }

  // Se devuelven los cuatro campos que alguien usa, uno por uno, y no lo leído
  // tal cual. Así lo que sale de esta función es lo que esta función promete,
  // y no cualquier cosa que apareciera escrita en el almacenamiento.
  return {
    pedido_id: id,
    token_consulta: guardado.token_consulta,
    referencia_pago: guardado.referencia_pago,
    url_checkout: guardado.url_checkout,
  };
}

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

    // Y, si esta persona dejó un pedido a medias, se retoma donde lo dejó.
    await retomarElPedidoGuardado();
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

/**
 * Tres tarjetas de mentira mientras la carta viaja.
 *
 * No es decoración: ocupan el mismo sitio que van a ocupar los productos, así
 * que cuando llegan los datos la página no da el salto que da cuando algo
 * aparece de la nada. Y se enseña la pantalla de la carta **antes** de pedirla,
 * con lo cual el encabezado y el filtro ya están en su sitio desde el primer
 * fotograma.
 *
 * Tres y no diez. Con el teléfono en la mano se ven tres tarjetas; fingir diez
 * para rellenar la pantalla le dice a quien espera que falta más de lo que
 * falta.
 */
function pintarEsqueletos() {
  const lista = $("lista-items");
  lista.replaceChildren();

  for (let i = 0; i < 3; i++) {
    const fila = document.createElement("li");
    fila.className = "esqueleto";
    fila.setAttribute("aria-hidden", "true");

    const foto = document.createElement("div");
    foto.className = "esqueleto-foto";

    const datos = document.createElement("div");
    datos.className = "esqueleto-datos";
    for (const ancho of ["media", "corta"]) {
      const linea = document.createElement("div");
      linea.className = `esqueleto-linea ${ancho}`;
      datos.append(linea);
    }

    fila.append(foto, datos);
    lista.append(fila);
  }
}

async function cargarCarta() {
  limpiarError();

  // El orden importa: primero la pantalla con los esqueletos, después la
  // petición. Al revés, la pantalla de arranque se queda girando hasta que
  // responde la API y el cambio llega de golpe.
  pintarEsqueletos();
  mostrar("carta");

  try {
    const carta = await api(
      `/v1/menu/establecimientos/${encodeURIComponent(CONFIG.ESTABLECIMIENTO_ID)}/items`
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
  dibujarNavegacion();
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

//: Cuántas unidades se pintaron la última vez. Solo sirve para no relanzar el
//: salto de la chapa en cada repintado: `dibujarNavegacion` se llama también
//: al cambiar de pantalla, y una chapa que brinca sin que nadie haya añadido
//: nada convierte una confirmación en un tic nervioso.
let unidadesPintadas = 0;

/**
 * Pone al día la barra de navegación: el carrito y los dos destinos.
 *
 * Antes esto era `dibujarBarraCarrito` y escondía una barra flotante cuando el
 * carrito estaba vacío. Ahora la barra es el caparazón de la aplicación y
 * siempre está; lo que cambia es si sus botones se pueden pulsar.
 *
 * **Deshabilitar en vez de esconder** es deliberado. Un control que aparece y
 * desaparece mueve el contenido de sitio y obliga a reaprender dónde estaba;
 * uno apagado dice «esto existe y todavía no» sin moverse. Con el pulgar sobre
 * una lista que se desplaza, lo segundo se agradece.
 */
function dibujarNavegacion() {
  const unidades = unidadesDelCarrito();
  const enPantalla = (p) => $(`pantalla-${p}`).classList.contains("activa");

  // --- El botón central: el carrito -----------------------------------
  const carrito = $("ver-pedido");
  carrito.disabled = unidades === 0;

  const cuenta =
    unidades === 0 ? "Carrito"
      : unidades === 1 ? "1 producto"
        : `${unidades} productos`;
  const total = unidades === 0 ? "" : pesos(totalDelCarrito());

  $("carrito-cuenta").textContent = cuenta;
  $("carrito-total").textContent = total;

  // El nombre accesible se declara en vez de dejarlo salir del contenido.
  // Saldría bien —el botón contiene su texto— pero depende de tres `<span>`
  // anidados, uno de ellos `aria-hidden`, y de que nadie reordene el marcado.
  // Declarado, dice lo mismo pase lo que pase.
  //
  // Contiene literalmente el texto visible, que es lo que exige el criterio
  // 2.5.3 de WCAG: quien dicta «dos productos» a un control por voz tiene que
  // poder activar este botón.
  carrito.setAttribute(
    "aria-label",
    unidades === 0 ? "Carrito vacío" : `Ver mi pedido: ${cuenta}, ${total}`
  );

  const chapa = $("carrito-chapa");
  chapa.textContent = String(unidades);
  chapa.classList.toggle("oculto", unidades === 0);

  if (unidades !== unidadesPintadas) {
    // Quitar la clase y volver a ponerla no basta: el navegador agrupa los dos
    // cambios en el mismo fotograma y la animación no se reinicia. Leer
    // `offsetWidth` lo obliga a recalcular el diseño en medio, que es la forma
    // estándar de forzar ese corte.
    chapa.classList.remove("salta");
    void chapa.offsetWidth;
    if (unidades > 0) chapa.classList.add("salta");
    unidadesPintadas = unidades;
  }

  // --- Los dos destinos -------------------------------------------------
  // La carta no se puede visitar antes de que exista: con `cartaCompleta`
  // vacía, pulsar «Carta» llevaría a una pantalla en blanco que parece rota.
  marcar($("nav-carta"), enPantalla("carta"), cartaCompleta.length === 0);

  // «Mi código» solo lleva a algún sitio cuando hay un pedido que mirar.
  marcar($("nav-codigo"), enPantalla("resultado"), pedidoActual === null);
}

/**
 * Marca un destino como el actual, y lo apaga si no lleva a ninguna parte.
 *
 * `aria-current` se **quita** cuando no aplica en vez de ponerse a "false":
 * los dos son válidos, pero algunos lectores de pantalla anuncian el atributo
 * por estar presente y leerían «página actual» en los dos botones.
 */
function marcar(boton, esElActual, apagado) {
  if (esElActual) {
    boton.setAttribute("aria-current", "page");
  } else {
    boton.removeAttribute("aria-current");
  }
  boton.disabled = apagado;
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
  dibujarNavegacion();
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

  // Un pedido nuevo todavía no tiene cobro. Si quedaran los del anterior, lo
  // que se guarde a continuación ataría este pedido a una referencia que no es
  // la suya.
  referenciaDelCobro = null;
  urlDelCheckout = null;

  try {
    pedidoActual = await api("/v1/pedidos", {
      method: "POST",
      body: JSON.stringify({ lineas }),
    });
    tokenDelPedido = pedidoActual.token_consulta;

    // Acá, y no después de pagar. El token se entrega **una sola vez**, en esta
    // respuesta: si la pestaña se cierra entre este instante y la confirmación,
    // sin esto el pedido quedaría pagado y sin nadie que pueda leer su código.
    guardarElPedido();
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
    urlDelCheckout = intento.url_checkout;
    guardarElPedido();

    mostrar("espera");
    ofrecerLaPasarela(urlDelCheckout);
    esperarLaConfirmacion();
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
    // El `Boolean` cubre el caso que apareció al poder recuperar un pedido:
    // de lo guardado puede salir un pedido sin cobro abierto, y `new URL(null)`
    // resuelve tan contento contra el origen propio y deja un enlace que
    // apunta a `null`.
    esNuestra =
      Boolean(urlCheckout) &&
      new URL(urlCheckout, location.href).origin === location.origin;
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

// Son dos esperas distintas y no merecen la misma cadencia:
//
//   · **La confirmación del pago** llega de un sistema externo en cualquier
//     momento, y quien espera está mirando la pantalla con el teléfono en la
//     mano. Ahí se pregunta seguido.
//   · **El avance en el mostrador** lo mueve una persona con una plancha
//     delante, y el propio panel se refresca cada cinco segundos: preguntar más
//     rápido que eso no puede enterarse de nada antes.
//
// Lo que comparten es que solo hay **un** temporizador, y que pedir una
// cadencia que ya está en marcha no lo reinicia. Sin esa comprobación,
// `mostrarResultado` —que se llama en cada vuelta— reiniciaría el intervalo en
// cada vuelta, y la consulta siguiente no llegaría nunca.

//: Cada cuántos ms pregunta el temporizador en marcha, o `null` si no hay.
let cadenciaDeConsulta = null;

function consultarCada(ms) {
  if (temporizadorConsulta !== null && cadenciaDeConsulta === ms) return;

  detenerConsultas();
  cadenciaDeConsulta = ms;
  // `lanzar` y no `consultarEstado` a secas: un intervalo no espera a una
  // función asíncrona, así que un fallo que ocurriera fuera de su `try` se
  // quedaría en la consola con la pantalla sin decir nada.
  temporizadorConsulta = setInterval(() => lanzar(consultarEstado()), ms);
}

/** Espera a que la pasarela confirme, preguntando ya y luego seguido. */
function esperarLaConfirmacion() {
  consultarCada(CONFIG.MS_ENTRE_CONSULTAS_DE_ESTADO);
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
    intento = await api(
      `/v1/pagos/intentos/${encodeURIComponent(referenciaDelCobro)}`
    );
  } catch {
    return;
  }

  if (intento.estado_pago !== "rechazado") return;

  detenerConsultas();
  mostrarCobroRechazado();
}

function mostrarCobroRechazado() {
  // Esta pantalla usa el mismo hueco que `mostrarResultado` pero no pasa por
  // ella, así que su huella deja de valer: sin esto, un estado que coincidiera
  // con el último pintado se daría por ya dibujado y el rechazo se quedaría en
  // pantalla encima de un pedido que ya avanzó.
  huellaDelResultado = null;

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
  if (temporizadorConsulta !== null) clearInterval(temporizadorConsulta);
  temporizadorConsulta = null;
  cadenciaDeConsulta = null;
}

async function consultarEstado() {
  try {
    // El token va en una cabecera y no en la dirección: una URL acaba en los
    // registros del servidor y del proxy, y este token es lo que permite leer
    // el código de canje.
    const pedido = await api(
      `/v1/pedidos/${encodeURIComponent(pedidoActual.pedido_id)}`,
      { headers: { "X-Token-Pedido": tokenDelPedido } }
    );
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

    // **Acá ya no se para el temporizador**, y ese era el tercer defecto.
    // Pagar no es el final del pedido: después viene el mostrador. Parando
    // aquí, la pantalla se quedaba congelada en «Pago confirmado» mientras la
    // de al lado decía «En preparación» y luego «Listo para recoger». Quien
    // había pagado era el único que no se enteraba de su propio pedido.
    //
    // Quien decide si queda algo que esperar es `mostrarResultado`, que es
    // quien sabe en qué estado está.
    mostrarResultado(pedido);
  } catch (e) {
    detenerConsultas();
    huellaDelResultado = null;

    // Un pedido que ya no existe tampoco tiene que seguir guardado: la demo se
    // reinicia entre una charla y la siguiente, y sin esto cada recarga
    // buscaría un pedido borrado para volver a enseñar el mismo error.
    if (e.status === 404) olvidarElPedido();

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

/**
 * Cómo llama el mostrador a cada estado.
 *
 * Es **literalmente** `ETIQUETA_ESTADO` de `panel.js`, y esa repetición es
 * deliberada: son dos páginas que no comparten código y que tienen que decir la
 * misma palabra, porque la conversación que ocurre en la barra es «mi pedido
 * dice tal» / «acá me sale tal». `test_escenarios_de_calidad.py` falla si una
 * de las dos se desvía de la otra.
 *
 * No sustituye a `RESPUESTA_POR_ESTADO.texto`, que cuenta lo que el estado
 * significa para quien pidió —«Lo están preparando»—. Esto es el nombre del
 * estado, que es otra cosa y hace otra falta.
 */
const ETIQUETA_ESTADO = {
  pendiente_pago: "Esperando pago",
  pagado: "Pagado",
  en_preparacion: "En preparación",
  listo_para_recoger: "Listo para recoger",
  entregado: "Entregado",
  cancelado: "Cancelado",
};

/**
 * Los estados en los que hay un código que alguien va a presentar.
 *
 * Sale de `RESPUESTA_POR_ESTADO` en vez de escribirse al lado: son exactamente
 * los estados que enseñan el código, y dos listas con la misma intención se
 * separan en cuanto alguien añade un estado y solo se acuerda de una.
 */
const ESTADOS_CON_CODIGO_VIVO = new Set(
  Object.entries(RESPUESTA_POR_ESTADO)
    .filter(([, respuesta]) => respuesta.mostrarCodigo)
    .map(([estado]) => estado)
);

/** Estados en los que el pedido ya no se mueve: no queda nada que esperar. */
const ESTADOS_FINALES = new Set(["entregado", "cancelado"]);

/**
 * Hay un código que alguien todavía tiene que presentar en el mostrador.
 *
 * Es la condición que convierte «Hacer otro pedido» en algo que hay que
 * confirmar. Un pedido sin pagar no tiene código; uno entregado o cancelado ya
 * gastó el suyo. Lo que no se puede perder está entre esos dos extremos.
 */
function hayUnCodigoEnJuego() {
  return (
    pedidoActual !== null &&
    Boolean(pedidoActual.codigo_canje) &&
    ESTADOS_CON_CODIGO_VIVO.has(pedidoActual.estado)
  );
}

//: La huella de lo último que se pintó en la pantalla del resultado.
//:
//: Mientras no cambie, no se repinta. **No es una optimización.** Desde que se
//: sigue al mostrador, esta pantalla se visita cada cinco segundos: reconstruir
//: el cuerpo en cada vuelta cancelaría la selección de quien está copiando su
//: código y cerraría la advertencia de «vas a perderlo» por debajo del dedo.
//: Es el mismo motivo por el que `panel.js` lleva su `huellaPintada`.
let huellaDelResultado = null;

function mostrarResultado(pedido) {
  const respuesta = RESPUESTA_POR_ESTADO[pedido.estado];

  // Cuando el pedido deja de estar pendiente, el carrito ya no representa
  // nada: su contenido se convirtió en este pedido.
  //
  // Esto lo destapó el rediseño. Antes la barra del carrito se escondía fuera
  // de la carta, así que nadie veía que seguía llena después de pagar; ahora la
  // barra es permanente y quedaba anunciando «1 producto · $ 29.800» al lado
  // del código de un pedido ya cobrado.
  //
  // **Se vacía acá y no al crear el pedido**, que era el sitio obvio: la
  // pantalla de reintento tras un cobro rechazado se repinta desde el carrito
  // (`dibujarLineasDelCarrito`), y vaciarlo antes la dejaría en blanco con el
  // pedido todavía por pagar.
  if (pedido.estado !== "pendiente_pago") carrito.clear();

  // --- ¿Queda algo que esperar? ---------------------------------------
  //
  // Antes no se preguntaba, porque antes se daba por hecho que confirmar el
  // pago era el final. No lo es: después viene el mostrador, y el mostrador
  // mueve el pedido dos veces más.
  if (ESTADOS_FINALES.has(pedido.estado)) {
    detenerConsultas();
    // El código ya se gastó. Guardarlo a partir de acá solo serviría para
    // enseñárselo a quien abra la carta después en este mismo teléfono.
    olvidarElPedido();
  } else if (ESTADOS_CON_CODIGO_VIVO.has(pedido.estado)) {
    consultarCada(CONFIG.MS_ENTRE_CONSULTAS_DE_SEGUIMIENTO);
  }
  // `pendiente_pago` no cae en ninguna de las dos a propósito: acá se llega con
  // ese estado cuando alguien pulsó «Consultar más tarde», y encender un
  // temporizador le quitaría a ese botón lo único que hace.

  // --- ¿Hace falta repintar? ------------------------------------------
  const huella = `${pedido.estado}|${pedido.codigo_canje || ""}`;
  const yaEstaEnPantalla =
    huella === huellaDelResultado &&
    $("pantalla-resultado").classList.contains("activa");
  if (yaEstaEnPantalla) return;
  huellaDelResultado = huella;

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
    cuerpo.append(dibujarElBillete(pedido, respuesta));
  }

  // El recibo: qué se compró y cuánto. Antes solo decía «Total pagado: …», que
  // además mentía en los estados donde no se pagó nada —un pedido cancelado, o
  // uno cuyo cobro todavía no ha confirmado la pasarela—. La fila «Total» del
  // resumen dice la cifra sin afirmar que haya cambiado de manos.
  cuerpo.append(dibujarResumen(pedido));
  mostrar("resultado");
}

/**
 * El código y, pegado debajo, en qué punto va el pedido.
 *
 * El estado ya estaba en esta pantalla —en el título y en la frase de arriba—,
 * pero contado como lo que significa para quien pidió: «Lo están preparando».
 * El mostrador lo llama «En preparación». Son lo mismo y no se parecen, y en
 * una barra con ruido las dos pantallas tienen que decir la misma palabra.
 *
 * Va **dentro** del billete y no en otro sitio de la pantalla porque la
 * pregunta es siempre la misma —«¿y el mío?»— y la respuesta son dos datos que
 * se miran juntos: el código que hay que enseñar y lo que está pasando con él.
 *
 * El color del punto sale de `RESPUESTA_POR_ESTADO`, que para estos tres
 * estados ya coincide con el `PUNTO_ESTADO` del panel; la prueba que ata las
 * etiquetas ata también los puntos.
 */
function dibujarElBillete(pedido, respuesta) {
  const billete = document.createElement("div");
  billete.className = "billete";

  const rotulo = document.createElement("p");
  rotulo.className = "billete-rotulo";
  rotulo.textContent = "Tu código de recogida";

  const codigo = document.createElement("div");
  codigo.className = "codigo-canje";
  codigo.textContent = pedido.codigo_canje;

  const estado = document.createElement("p");
  estado.className = "billete-estado";
  const punto = document.createElement("span");
  punto.className = `punto ${respuesta.punto}`;
  const texto = document.createElement("span");
  texto.textContent = ETIQUETA_ESTADO[pedido.estado] || pedido.estado;
  estado.append(punto, texto);

  billete.append(rotulo, codigo, estado);
  return billete;
}

function nota(texto) {
  const p = document.createElement("p");
  p.className = "nota";
  p.textContent = texto;
  return p;
}

// --------------------------------------------------------------------------
// Hacer otro pedido sin perder el anterior
//
// «Hacer otro pedido» borraba el pedido en curso, su token y su código sin
// preguntar nada. Para quien ya había pagado y no había copiado el código, eso
// era perder lo comprado de un toque — y el toque está justo debajo del
// código, que es donde la vista acaba de posarse.
//
// El botón no se quita: hacer otro pedido es lo normal cuando el anterior ya se
// recogió. Lo que se añade es un paso más, y **solo cuando hay algo que
// perder**. Una confirmación que aparece siempre se aprende a despachar sin
// leerla, y entonces deja de proteger de nada.
// --------------------------------------------------------------------------

function abrirLaAdvertencia() {
  const fuerte = document.createElement("strong");
  fuerte.textContent = pedidoActual.codigo_canje;

  $("advertencia-texto").replaceChildren(
    "Ya pagaste este pedido y su código es ",
    fuerte,
    ". Si empezás otro, esta pantalla deja de mostrarlo: desde el teléfono no " +
      "hay dónde volver a buscarlo, y habría que pedirlo en el mostrador."
  );

  $("advertencia-codigo").classList.remove("oculto");
  $("nuevo-pedido").classList.add("oculto");

  // El foco va al botón que **no** destruye nada. Quien llegue acá con el
  // teclado y pulse Intro sin leer se queda donde estaba, que es lo que
  // habría querido.
  $("seguir-viendo-el-codigo").focus();
}

function cerrarLaAdvertencia() {
  $("advertencia-codigo").classList.add("oculto");
  $("nuevo-pedido").classList.remove("oculto");
}

function empezarOtroPedido() {
  // El temporizador primero. Desde que se sigue al pedido después de pagar hay
  // uno en marcha casi siempre, y una vuelta suya con `pedidoActual` ya nulo
  // tira un error de lectura sobre la pantalla de la carta.
  detenerConsultas();
  olvidarElPedido();

  pedidoActual = null;
  tokenDelPedido = null;
  referenciaDelCobro = null;
  urlDelCheckout = null;
  huellaDelResultado = null;

  // El carrito se vacía: sin esto el pedido siguiente empezaría con lo que la
  // persona acaba de pagar y recoger.
  carrito.clear();
  metodoElegido = null;

  cerrarLaAdvertencia();
  dibujarNavegacion();
  limpiarError();
  lanzar(cargarCarta());
}

/**
 * Recupera el pedido que esta persona dejó a medias, si lo dejó.
 *
 * Es lo que hace que volver desde la pasarela aterrice en el código y no en la
 * portada: esa pestaña, al navegar a `index.html`, pasa por acá y encuentra el
 * pedido que escribió la otra.
 *
 * Se llama **después** de la carta y no antes. Así la pantalla del código se
 * abre sobre una carta ya cargada, y el destino «Carta» de la barra lleva a
 * algún sitio en cuanto alguien lo toca.
 *
 * Nada de lo que falle acá se cuenta: quien abre la carta no pidió recuperar
 * nada. Un `404` es lo normal entre una demostración y la siguiente —el
 * reinicio borra los pedidos—, y un fallo de red no impide pedir otra vez.
 */
async function retomarElPedidoGuardado() {
  const guardado = leerElPedidoGuardado();
  if (guardado === null) return;

  let pedido;
  try {
    pedido = await api(
      `/v1/pedidos/${encodeURIComponent(guardado.pedido_id)}`,
      { headers: { "X-Token-Pedido": guardado.token_consulta } }
    );
  } catch (e) {
    if (e.status === 404) olvidarElPedido();
    return;
  }

  pedidoActual = pedido;
  tokenDelPedido = guardado.token_consulta;
  referenciaDelCobro = guardado.referencia_pago || null;
  urlDelCheckout = guardado.url_checkout || null;

  if (pedido.estado !== "pendiente_pago") {
    mostrarResultado(pedido);
    return;
  }

  // Sigue sin pagarse. Con un cobro abierto se vuelve a la espera, que es de
  // donde se salió y donde la confirmación está por llegar. Sin él no hay nada
  // que esperar: se deja la carta y «Mi código» encendido, que lleva a la
  // pantalla donde se explica que el pedido está esperando el pago.
  if (referenciaDelCobro === null) {
    dibujarNavegacion();
    return;
  }

  mostrar("espera");
  ofrecerLaPasarela(urlDelCheckout);
  esperarLaConfirmacion();
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

// Los dos destinos de la barra. No hacen nada que no se pudiera hacer ya con
// los botones de cada pantalla: son el mismo viaje con el pulgar donde el
// pulgar está.
//
// `volverALaCarta` y no `mostrar("carta")`: esa además repinta la carta, que
// hace falta para que las cantidades de cada producto reflejen el carrito.
//
// **No detiene las consultas de estado, y es a propósito.** Quien está
// esperando la confirmación y se pone a mirar la carta sigue teniendo su cobro
// en marcha; cuando confirme, `consultarEstado` lo lleva a la pantalla del
// código. Interrumpe lo que esté haciendo, sí — y es justo lo que quiere, que
// es para lo que pagó.
$("nav-carta").addEventListener("click", volverALaCarta);

$("nav-codigo").addEventListener("click", () => {
  // El botón está apagado cuando no hay pedido, así que esto no debería poder
  // pasar; se comprueba igual porque `disabled` se puede quitar desde las
  // herramientas del navegador y una pantalla de resultado sin pedido tira un
  // error de lectura de `null`.
  if (pedidoActual === null) return;

  // **Ya no se detienen las consultas.** Antes sí, y era un castigo por mirar:
  // quien tocaba «Mi código» mientras esperaba la confirmación se quedaba sin
  // sondeo y con una pantalla que ya no se iba a mover sola. Ahora decide
  // `mostrarResultado`, que es quien sabe si queda algo por pasar.
  mostrarResultado(pedidoActual);
});

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
  if (hayUnCodigoEnJuego()) {
    abrirLaAdvertencia();
    return;
  }
  empezarOtroPedido();
});

$("confirmar-nuevo-pedido").addEventListener("click", empezarOtroPedido);

$("seguir-viendo-el-codigo").addEventListener("click", () => {
  cerrarLaAdvertencia();
  // El foco vuelve al botón desde el que se abrió. Sin esto se queda en un
  // botón que acaba de desaparecer, y el tabulador siguiente empieza desde
  // arriba del documento.
  $("nuevo-pedido").focus();
});

lanzar(comprobarSalud());
