// Dónde vive la API.
//
// Es el único archivo que hay que tocar al desplegar. Se separa del resto del
// código a propósito: un sitio estático no recibe variables de entorno en
// tiempo de ejecución —no hay proceso que las lea—, así que la configuración
// tiene que viajar en un archivo.

const CONFIG = {
  // **Un host aparte, no una ruta**, y no por gusto.
  //
  // La primera versión publicaba la API bajo `/api` del mismo dominio, para que
  // sitio y API compartieran origen y CORS dejara de existir como clase de
  // problema. En el servidor del laboratorio eso **no funciona**: dos dominios
  // con el mismo Host colisionan al crear el router de Traefik y solo sobrevive
  // uno. Comprobado contra el despliegue, y confirmado por la app de referencia
  // del propio laboratorio, que separa igual (`api-capstonehub.iscoutb.dev`).
  //
  // El costo es que CORS vuelve a importar. Ya está implementado y probado
  // (`test_cors.py`), así que no es trabajo nuevo — pero sí una superficie de
  // error que el origen único habría eliminado. Ver ADR-0008.
  API_PRODUCCION: "https://api-pideutb.iscoutb.dev",

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
