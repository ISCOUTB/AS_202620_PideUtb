// Dónde vive la API.
//
// Es el único archivo que hay que tocar al desplegar. Se separa del resto del
// código a propósito: un sitio estático no recibe variables de entorno en
// tiempo de ejecución —no hay proceso que las lea—, así que la configuración
// tiene que viajar en un archivo.

const CONFIG = {
  // **Una ruta, no un host.** El sitio y la API se publican bajo el mismo
  // dominio —`pideutb.iscoutb.dev`— y el proxy del laboratorio enruta `/api`
  // hacia el contenedor de la API.
  //
  // Que sean el mismo origen no es un detalle de despliegue: hace que las
  // peticiones del panel dejen de ser peticiones entre orígenes, y con ellas
  // desaparece toda una clase de fallo. Esta misma semana una configuración de
  // CORS incompleta dejó el panel roto en el navegador con 250 pruebas en
  // verde, porque el cliente de pruebas no hace *preflight*.
  //
  // La alternativa evaluada era un host aparte (`api-pideutb.iscoutb.dev`), que
  // mantendría la separación visual a cambio de conservar CORS. Ver ADR-0008.
  API_PRODUCCION: "/api",

  API_LOCAL: "http://127.0.0.1:8000",

  // Establecimiento que se muestra en la portada. Con un solo punto de venta
  // en el seed, no hace falta un selector todavía.
  ESTABLECIMIENTO_ID: 1,

  // A partir de cuántos milisegundos se avisa al usuario de que el servicio
  // está despertando.
  //
  // El plan gratuito de Render duerme el servicio tras 15 minutos sin tráfico
  // y tarda ~60 s en volver. Sin este aviso, el primer usuario de cada pico de
  // almuerzo vería una página congelada y asumiría que está rota.
  MS_ANTES_DE_AVISAR_ARRANQUE_EN_FRIO: 2500,

  // Cada cuánto se vuelve a preguntar por el estado del pedido mientras se
  // espera la confirmación del pago.
  MS_ENTRE_CONSULTAS_DE_ESTADO: 3000,
};

CONFIG.API = ["localhost", "127.0.0.1", ""].includes(location.hostname)
  ? CONFIG.API_LOCAL
  : CONFIG.API_PRODUCCION;
