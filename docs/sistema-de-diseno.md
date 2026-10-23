# Sistema de diseño de PideUTB

1. [Principios](#principios)
2. [Anatomía de la aplicación](#anatomia)
3. [Identidad visual](#identidad)
4. [Colores](#colores)
5. [Tipografía y cuadrícula](#tipografia)
6. [Componentes](#componentes)
7. [Patrones de interacción](#patrones)
8. [Pantallas de referencia](#pantallas)
9. [La carta](#p-carta)
10. [Tu pedido](#p-pedido)
11. [Esperando el pago](#p-espera)
12. [El código de canje](#p-codigo)
13. [Panel del mostrador](#p-panel)
14. [Ingreso al panel](#p-ingreso)
15. [Implementación](#implementacion)
16. [Definición de «terminado»](#terminado)
17. [Decisiones confirmadas](#decisiones)

Universidad Tecnológica de Bolívar · Pedidos en el campus

Esta guía fija la apariencia y el comportamiento de las dos superficies de
PideUTB: la del cliente y la del mostrador. Cada pantalla que se desarrolle debe
ajustarse a ella.

**Versión** 1.0 · 22/10/2026 · **Fundamentos** colores extraídos del sitio de la
UTB decodificando una captura, con su contraste WCAG medido · tokens vigentes en
[`sitio/estilos.css`](../sitio/estilos.css) · **Alcance** las seis pantallas que
hoy existen

> **Esta guía describe lo que hay, no lo que se querría tener.** Cada token que
> nombra existe en `sitio/estilos.css` y cada ratio de contraste está medido. Si
> alguna vez las dos cosas dejan de coincidir, la hoja gana y esta guía está
> desactualizada — que es el defecto que este proyecto ha encontrado tres veces y
> que [arc42 §7.6](arc42/arc42.md#despliegue-deuda) documenta.

<a id="principios"></a>

## Principios

Seis reglas resuelven los casos que esta guía no prevé. Ante la duda, gana la que
protege a quien usa la aplicación con prisa.

#### Pertenecer a la UTB

Los colores son los del sitio de la universidad. Alguien que llega desde
`utb.edu.co` no debe sentir que salió de la institución. El filete de tres
colores de la cabecera es la seña, y es lo único decorativo de la hoja.

#### Una mano, de pie, con prisa

Las dos superficies se usan igual: el cliente pide de pie entre clases, el
mostrador atiende con una mano mientras cocina con la otra. De ahí salen los
objetivos táctiles de 48 px, el apilado en una sola columna y la ausencia de
gestos de precisión. **Ninguna acción importante exige puntería.**

#### El color nunca informa solo

Dos de los tres colores de la marca no pueden llevar texto, y hay quien no
distingue tonos. Todo estado lleva **rótulo**; el color refuerza y no sustituye.
El punto de «esperando» además late, para que el movimiento diga lo que el tono
no puede.

#### Una sola acción principal

Cada pantalla tiene como máximo un botón sólido azul. Lo demás es secundario, con
contorno. Si dos acciones parecen principales, la pantalla hace dos cosas.

#### El pedido siempre dice en qué va

Un pedido nunca queda en un estado desconocido. Si el aviso de pago no llega, se
queda en «pendiente de pago», que es honesto y consultable
([ADR-0003](adr/0003-estrategia-integracion.md)). La interfaz nunca afirma un
estado que el servidor no confirmó.

#### Accesible por defecto

WCAG 2.1 nivel AA como mínimo, recorrido completo con teclado, foco siempre
visible, y `prefers-reduced-motion` respetado. La accesibilidad es parte de
«terminado», no una fase posterior.

<a id="anatomia"></a>

## Anatomía de la aplicación

**PideUTB no tiene una estructura de aplicación con menús, y decirlo es parte de
la guía.** Inventar una barra de espacios o un menú lateral añadiría navegación a
dos superficies que no la necesitan: la del cliente es un flujo lineal de cinco
pasos, y la del mostrador es una sola pantalla.

```
┌──────────────────────────────────────────┐
│  Cabecera                                │   Título + lema
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │   Filete de marca, 4 px
├──────────────────────────────────────────┤
│                                          │
│  Contenido                               │   Una sola columna
│  (una pantalla visible a la vez)         │   máx. 720 px
│                                          │
├──────────────────────────────────────────┤
│  Pie                                     │   Atribución
└──────────────────────────────────────────┘
```

| Zona | Regla | Dimensiones |
|---|---|---|
| **Cabecera** | Título en `--azul`, lema en `--tinta-media`, y debajo el filete de tres colores. Nunca lleva acciones. | Título `clamp(1.9rem … 2.6rem)` · filete de 4 px |
| **Contenido** | Una columna. En el cliente, una sola pantalla visible: `.pantalla.activa`. En el mostrador, la cola. | Máx. 720 px, centrada · márgenes laterales de 16 px |
| **Pie** | Atribución y enlaces. Separado por una línea. | `--tinta-tenue`, 0,9rem |

El ancho máximo de 720 px es deliberado: aunque el mostrador use una pantalla
grande, la cola se lee mejor en una columna estrecha que en líneas de 1 400 px de
ancho. Es lo contrario del criterio de una aplicación de datos, y el motivo es
que aquí **no se comparan filas: se atiende la de arriba.**

### Las dos superficies

| Superficie | Archivo | Quién | Forma |
|---|---|---|---|
| **Cliente** | `index.html` · `app.js` | Cualquiera, sin cuenta | Flujo lineal: carta → pedido → espera → resultado |
| **Mostrador** | `panel.html` · `panel.js` | Personal, con sesión | Una cola que se refresca sola cada 5 s |

Las dos comparten `estilos.css` **a propósito**: son la misma aplicación
desplegada, y dos hojas separadas harían que los colores se separaran al primer
cambio.

<a id="identidad"></a>

## Identidad visual

No hay logotipo. La marca es **el nombre en azul más el filete de tres colores**,
y con eso basta: no hay archivo que mantener, ni versión invertida que aprobar,
ni un peso más en la imagen.

```
PideUTB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  azul 42 %      cian 32 %       verde 26 %
```

**Hacer.** Usar el filete solo bajo la cabecera, a todo el ancho de la columna.
Dejar el título en `--azul` y el lema en `--tinta-media`.

**Evitar.** Repetir el filete dentro del contenido; usar los tres colores juntos
en cualquier otro sitio; poner el título sobre una foto; recolorearlo.

El día que la universidad entregue un logotipo, entra en la cabecera a la
izquierda del título sin ningún otro cambio.

<a id="colores"></a>

## Colores

Tres familias, tres funciones: la marca (azul, cian, verde), la estructura
(tintas y papeles) y los estados (ámbar y rojo).

### La regla que gobierna la paleta, y por qué no es negociable

Los tres colores salen del sitio de la UTB. Pero **dos de los tres no pueden
llevar texto**, y eso no es una opinión de diseño: es su contraste medido contra
blanco, según WCAG 2.1.

| Color | Token | Sobre blanco | Veredicto |
|---|---|---|---|
| Azul | `--azul` `#093AD8` | **8,05:1** | AAA · texto, botones, enlaces |
| Cian | `--cian` `#0FC5EF` | **2,05:1** | ✗ insuficiente incluso para texto grande |
| Verde | `--verde` `#71EC37` | **1,53:1** | ✗ insuficiente |

Sobre tinta oscura la relación se invierte y los dos pasan con holgura:

| | Sobre `--tinta` `#0B1020` |
|---|---|
| Cian | **9,24:1** · AAA |
| Verde | **12,40:1** · AAA |

De ahí la regla:

> **El cian y el verde son colores de SUPERFICIE, nunca de TINTA.**

Se usan como fondo de algo que lleva texto oscuro encima —el filete de marca, el
recuadro del código de canje, el punto de un estado— y **jamás** como color de
letra sobre blanco.

Para los casos en que hace falta *letra* de esos tonos existen las variantes
oscurecidas, que son la única forma de usarlos legiblemente:

| Token | Valor | Sobre blanco |
|---|---|---|
| `--cian-tinta` | `#086C83` | **6,03:1** · AA |
| `--verde-tinta` | `#3E811E` | **4,81:1** · AA |

Aplicar la marca sin medir habría producido una página correcta en la captura e
**ilegible en el mostrador**, que es donde se usa con prisa y a contraluz.

### Marca

| Token | Valor | Uso |
|---|---|---|
| `--azul` | `#093AD8` | Botones sólidos, enlaces, título, filete de fila activa |
| `--azul-hundido` | `#0730AB` | Hover y pulsado: el mismo tono, más grave |
| `--azul-niebla` | `#E8EDFD` | Fondo de apoyo del botón secundario en hover |
| `--cian` | `#0FC5EF` | Filete de acento de las tarjetas, punto de «esperando» |
| `--verde` | `#71EC37` | **Solo** el fondo del código de canje |
| `--cian-tinta` | `#086C83` | Letra cian, cuando hace falta |
| `--verde-tinta` | `#3E811E` | Letra verde · punto de «confirmado» |

### Estructura

| Token | Valor | Contraste sobre blanco | Uso |
|---|---|---|---|
| `--tinta` | `#0B1020` | **18,93:1** | Cuerpo de texto |
| `--tinta-media` | `#4A5365` | **7,73:1** | Texto secundario: precios, rótulos, lema |
| `--tinta-tenue` | `#6B7486` | **4,70:1** | **Solo metadatos.** Nunca información esencial |
| `--papel` | `#FFFFFF` | — | Tarjetas, campos, diálogos |
| `--fondo` | `#F5F5F5` | — | Fondo de página. Es el gris del sitio de la UTB |
| `--linea` | `#E3E6EC` | — | Separadores |
| `--linea-fuerte` | `#CFD4DE` | — | Borde de campos y de botones secundarios |

`--tinta-tenue` pasa AA con 4,70:1 pero no AAA. De ahí la restricción: sirve para
la hora de última carga o una nota de ayuda, **nunca** para un precio, un estado
o un mensaje de error.

### Estados

Reservados para los estados y siempre con rótulo. **El rojo nunca es un color de
acción**: solo señala que algo salió mal.

| Token | Valor | Fondo | Contraste sobre su fondo | Uso |
|---|---|---|---|---|
| `--aviso` | `#9A5B00` | `--aviso-fondo` `#FFF4E0` | **4,98:1** | Agotado, esperando, en el límite |
| `--error` | `#B3261E` | `--error-fondo` `#FDECEA` | **5,72:1** | Pago rechazado, fallo de red |

El ámbar de marca habitual (`#FFB020`) no aparece: con 1,9:1 sobre blanco no
puede llevar texto. `--aviso` es ese ámbar oscurecido hasta ser legible, que es
el mismo criterio que se aplicó al cian y al verde.

### Tema oscuro

Se conserva para quien lo tenga puesto en su sistema, con una regla: **el azul se
aclara**, porque `#093AD8` sobre fondo oscuro cae por debajo del mínimo legible.
El verde del código de canje **no** cambia: sigue siendo la seña del momento de
recoger, y con tinta encima mantiene sus 12,40:1.

La marca es luminosa, así que el claro es el principal y el oscuro la cortesía.

<a id="tipografia"></a>

## Tipografía y cuadrícula

**Fuente del sistema, y ninguna cargada desde un CDN.**

```css
system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif
```

Es una decisión y no una carencia. Una fuente externa añade una petición a un
tercero, latencia en una red de campus y un dato que sale del navegador de quien
pide. Si alguna vez se quiere una tipografía propia, se **autohospeda** en el
contenedor; no se enlaza.

| Función | Tamaño / interlineado | Grosor | Uso |
|---|---|---|---|
| Título de marca | `clamp(1.9rem, 1.4rem + 2.2vw, 2.6rem)` / 1,05 · espaciado −0,035 em | 800 | Uno por página |
| Título de sección | 1,5rem / 1,3 · espaciado −0,02 em | 750 | Secciones |
| Título de bloque | 1,08rem / 1,4 | 700 | Diálogos, paneles |
| Nombre de ítem | 1,05rem · espaciado −0,01 em | 650 | Tarjetas |
| Cuerpo | 1rem / 1,6 | 400 | Textos y campos |
| Total | 1,25rem · cifras tabulares · espaciado −0,02 em | 800 | La cifra que se mira antes de pagar |
| Código de canje | `clamp(2rem, 1.2rem + 3.6vw, 2.9rem)` · monoespaciada · espaciado 0,22 em | 700 | Solo el código |
| Metadatos | 0,9rem · `--tinta-tenue` | 400 | Hora de última carga, notas |

El interlineado del cuerpo es 1,6, más holgado que el de una aplicación de datos:
aquí no hay tablas densas que comprimir, y el texto se lee en un teléfono a la
intemperie.

#### El dinero y los códigos

| Regla | Por qué |
|---|---|
| Precios y totales en **cifras tabulares** (`font-variant-numeric: tabular-nums`) | Una columna de precios con cifras de ancho distinto no se puede comparar de un vistazo |
| El total, separado por una línea y más grande | Es la cifra que se mira antes de pagar, y debe encontrarse sin leer las demás |
| **El precio que se ve es el que se cobra** | El pedido guarda su propia instantánea del precio ([V-06](violaciones.md#v-06)): una subida posterior no reescribe lo ya pedido |
| El código de canje, monoespaciado y espaciado | Se dicta en voz alta en el mostrador, y a esa letra se la confunde menos |

#### Espaciado, formas, elevación

| Token | Valores | Regla |
|---|---|---|
| `--e1` … `--e8` | 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 px | **Todo margen y todo espaciado sale de esta escala.** Entre hermanos, con `gap` |
| `--radio` | 12 px | Tarjetas, diálogos, código de canje |
| `--radio-chico` | 8 px | Botones, campos, líneas de estado |
| `--radio-pildora` | 999 px | Etiquetas, el filete de marca |
| `--sombra` | `0 1px 2px / 6%`, `0 2px 8px / 4%` | Tarjetas en reposo |
| `--sombra-alta` | `0 4px 12px / 8%`, `0 12px 32px / 8%` | Hover de tarjeta y diálogos |
| `--foco` | `0 0 0 3px rgb(9 58 216 / 35%)` | **Todo** elemento enfocable |

Dos niveles de elevación y nada más. Una sombra por componente convierte la
jerarquía en ruido.

<a id="componentes"></a>

## Componentes

Cada uno con los tokens reales. La estructura de clases es la que `app.js` y
`panel.js` ya manipulan: **cambiar un nombre de clase rompe el comportamiento**,
así que el rediseño se hace sobre ellas, no contra ellas.

### Botones

```
┌─────────────────┐   ┌─────────────────┐
│     Pedir       │   │  Volver a la    │   48 px de alto mínimo
└─────────────────┘   │     carta       │
   sólido, --azul     └─────────────────┘
                       contorno, .secundario
```

| Variante | Clase | Uso |
|---|---|---|
| Principal | *(ninguna)* | Una por pantalla. Fondo `--azul`, letra blanca · 8,05:1 |
| Secundaria | `.secundario` | Fondo transparente, letra `--azul`, borde `--linea-fuerte` |

**Regla.** El rótulo dice lo que ocurre: «Pagar con PSE», «Confirmar entrega»,
nunca «OK» ni «Enviar».

**Regla.** 48 px de alto mínimo, que es la medida táctil cómoda y no la mínima de
44. En las acciones de la cola del mostrador baja a 44, porque son varias por
tarjeta y el personal ya tiene el dedo encima.

**Regla.** En pantallas estrechas, los botones de pago se apilan a ancho
completo. Dos botones de pago en una fila de 375 px parten el rótulo en dos
líneas, y «Pagar con Nequi» junto a uno de una sola línea se ve roto.

**Evitar.** Dos botones sólidos lado a lado. Un botón desactivado sin explicar
qué falta.

### Campos y formularios

```
Correo
┌────────────────────────────────┐
│ mostrador@utb.edu.co           │   borde --linea-fuerte
└────────────────────────────────┘   foco: borde --azul + halo de 3 px
```

| Regla | Detalle |
|---|---|
| Rótulo **encima** del campo | En móvil, rótulo al lado se amontona en una sola línea |
| 48 px de alto mínimo | Mismo criterio que los botones |
| Foco visible siempre | Borde `--azul` más `--foco`. Nunca `outline: none` sin reemplazo |
| El error dice qué hacer | «La contraseña debe tener al menos 8 caracteres», no «Entrada inválida» |

#### Sobre los registros

**PideUTB no tiene registro de clientes, y es una decisión de arquitectura, no un
pendiente.** Un cliente pide sin cuenta: es quien tiene el código de canje
([arc42 §8.8](arc42/arc42.md#datos-personales)). La tabla `pedidos` no guarda
nombre, teléfono ni correo.

El efecto es que **el dato que no se recoge no se puede filtrar**, y por eso el
único formulario de la aplicación es el ingreso del mostrador.

Si algún día se añade un registro —de personal, no de clientes— sigue estas
reglas: rótulo encima, validación al salir del campo y otra vez al enviar,
contraseña con requisito visible antes de escribir, y nunca más de seis campos en
un diálogo. Lo que **no** se añade es un registro de clientes sin un requisito
que lo pida: hoy su ausencia es una propiedad del sistema.

### Tarjeta

Es el componente más repetido: un ítem de la carta y un pedido de la cola son la
misma forma, y conviene que se parezcan — el cliente y el mostrador miran el
mismo objeto.

```
┃┌──────────────────────────────────────┐
┃│  Arepa de huevo                      │   filete de acento, 4 px
┃│  $ 4.000              ┌──────────┐   │   --cian en la carta
┃│                       │  Pedir   │   │   --azul en la cola
┃└───────────────────────└──────────┘───┘
```

| Estado | Apariencia |
|---|---|
| Normal | `--papel`, `--sombra`, filete `--cian` |
| Hover | `--sombra-alta` y 1 px de elevación |
| En la cola del mostrador (`.pedido`) | Filete `--azul` |
| Agotado (`.agotado`) | Sin sombra, borde `--linea`, filete `--linea-fuerte`, nombre en `--tinta-tenue` |

**El agotado conserva la tarjeta.** Quitarle el fondo lo convertía en un hueco en
la lista en vez de en un plato que hoy no hay.

### Código de canje

El momento alto de la aplicación: lo que el cliente enseña para recoger. Se trata
como un **billete**, y es el único sitio donde el verde de la marca se usa entero
—porque ahí es fondo y no letra.

```
    ╭──────────────────────────────────╮
   ◖│          K 7 M 2 Q 9             │◗   fondo --verde
    ╰──────────────────────────────────╯    tinta --tinta · 12,40:1
```

| Variante | Uso |
|---|---|
| `.codigo-canje` en bloque | La pantalla de resultado del cliente |
| `input.codigo-canje` | El diálogo de entrega del mostrador: mismo tratamiento, fondo `--papel`, sin muescas, `text-transform: uppercase` |

La conversión a mayúsculas del campo es **visual**: el servidor compara sin
distinguir la caja, así que no cambia lo que se envía.

### Estados y etiquetas

```
●  Pago confirmado          --verde-tinta
◉  Esperando confirmación   --cian, late
●  El pago fue rechazado    --error
```

| Clase | Color | Significado |
|---|---|---|
| `.punto.ok` | `--verde-tinta` | Confirmado |
| `.punto.espera` | `--cian`, con latido | Esperando |
| `.punto.mal` | `--error` | Rechazado |
| `.etiqueta-agotado` | `--aviso` sobre `--aviso-fondo` | Agotado |

**El punto nunca va solo**: siempre lleva su rótulo al lado. Y el de «esperando»
late, para distinguir esperando de terminado sin depender del tono — que es lo
que no ve quien no distingue colores. El latido se desactiva con
`prefers-reduced-motion`.

### Aviso, error, vacío y carga

| Situación | Tratamiento |
|---|---|
| **Error** | `.error`: fondo `--error-fondo`, borde izquierdo de 4 px en `--error`. Dice qué pasó y cómo seguir |
| **Carga** | Rueda de 38 px más un texto que dice qué se está comprobando. Nunca una pantalla en blanco |
| **Tarda más de lo normal** | Nota adicional a los 2,5 s. **No afirma la causa**: desde el navegador no se distingue un reinicio de una red lenta |
| **Vacío** | Dice por qué está vacío y qué hacer. «No hay pedidos en la cola» más la hora de la última carga |

El aviso de lentitud merece su regla propia, y viene de un defecto real: durante
cinco días dijo «es el arranque en frío del plan gratuito» después de que esa
plataforma dejara de usarse. Una causa falsa delante de una persona es peor que
no dar ninguna.

### Diálogo

| Regla | Detalle |
|---|---|
| Máximo 26 rem de ancho | Más de seis campos van en página, no en diálogo |
| `::backdrop` propio | Sin él, el fondo queda blanco en el tema oscuro: no hereda del documento |
| «Cancelar» a la derecha de la acción | En el mostrador el pulgar llega antes al borde derecho |
| Cierre con `Esc` | Nativo de `<dialog>`; no se desactiva |

<a id="patrones"></a>

## Patrones de interacción

Las mismas situaciones se resuelven siempre igual.

| Situación | Patrón | Ejemplo |
|---|---|---|
| **Avanzar en el flujo del cliente** | Una pantalla visible a la vez, `.pantalla.activa`, con una entrada de 0,22 s | Carta → pedido → espera → resultado |
| **Esperar algo que no depende de nosotros** | Estado consultable más sondeo. Nunca una pantalla bloqueada | Esperando la confirmación del pago, cada 3 s |
| **Enterarse de un cambio ajeno** | Sondeo con intervalo atado a su umbral | La cola del mostrador, cada 5 s |
| **Acción que compromete dinero** | Resumen de lo que se va a cobrar **antes** del botón | «Tu pedido» antes de «Pagar con…» |
| **Acción irreversible del mostrador** | Diálogo que nombra el pedido y pide el código | Entregar un pedido |
| **Acción reversible** | Sin confirmación | Volver a la carta, refrescar |
| **Algo salió mal fuera de nuestro control** | Mensaje que distingue «el servicio respondió que no puede» de «no se pudo contactar» | `503` contra fallo de red |
| **Dato que tarda** | Rueda con texto, y a los 2,5 s una nota que **no inventa la causa** | Comprobación inicial del servicio |

### El sondeo es parte del diseño, no un detalle técnico

El intervalo de la cola del mostrador **sostiene un requisito de calidad**, y por
eso vive en esta guía y no solo en el código.

[ESC-03](arc42/arc42.md#esc-03) concede **10 segundos** desde que un pedido se
paga hasta que el encargado lo ha visto y cambiado de estado. El reloj arranca en
el pago, así que el intervalo cuenta dentro del plazo:

```
5 000 ms de sondeo + 302 de red + 19 de servidor = 5 320 ms
→ quedan 4,68 s para que una persona vea y pulse
```

Estuvo en 8 000 ms hasta que se midió: dejaba **1,68 s**, que no es una reserva
razonable para alguien que está cocinando.
`backend/tests/test_escenarios_de_calidad.py` rompe la construcción si ese número
sube, y también si baja sin motivo — porque sondear de más cuesta peticiones y no
mejora ningún umbral.

### Redacción

| Regla | Ejemplo |
|---|---|
| Español de Colombia, de tú | «Muéstralo en el mostrador para recoger tu pedido» |
| Dinero en pesos con separador de miles | `$ 11.000` |
| El error dice qué pasó y cómo seguir | «No se pudo contactar con el servicio. Revisa tu conexión e inténtalo de nuevo» |
| Sin disculpas ni jerga | «El pago fue rechazado», no «Error: transacción no exitosa» |
| Nunca afirmar lo que no se sabe | «Está tardando más de lo normal», no «el servidor está caído» |

<a id="pantallas"></a>

## Pantallas de referencia

Seis pantallas: cuatro del cliente y dos del mostrador. Son todas las que hoy
existen.

<a id="p-carta"></a>

### La carta

```
PideUTB
Pide desde el celular y recoge sin fila.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Carta

┃ Arepa de huevo                [ Pedir ]
┃ $ 4.000

┃ Jugo de mango natural         [ Pedir ]
┃ $ 3.000

│ Empanada de carne            ( Agotado )
│ $ 3.500
```

Una tarjeta por ítem, el precio bajo el nombre en `--tinta-media`, y la acción a
la derecha. Los agotados **no se ocultan**: saber que algo existe y hoy no hay es
información, y ocultarlo haría que el cliente lo busque.

<a id="p-pedido"></a>

### Tu pedido

```
Tu pedido

┌──────────────────────────────────┐
│  Arepa de huevo × 2    $ 8.000   │
│  Jugo de mango         $ 3.000   │
│  ──────────────────────────────  │
│  Total               $ 11.000    │
└──────────────────────────────────┘

[ Pagar con PSE    ]
[ Pagar con Nequi  ]

[ Volver a la carta ]
```

El resumen antes de la acción. El total separado por una línea y más grande: es
lo que se mira antes de pagar. Los métodos de pago apilados a ancho completo en
móvil.

<a id="p-espera"></a>

### Esperando el pago

```
            ◜◝
           ◟  ◞         rueda de 38 px

    Esperando la confirmación del pago…

    El pago se hace en la pasarela. Cuando
    termine, esta pantalla lo sabrá sola.
```

La espera **no bloquea**: el pedido ya existe y es consultable. Si el aviso nunca
llega, queda en «pendiente de pago», que es un estado honesto y no un error.

<a id="p-codigo"></a>

### El código de canje

```
¡Listo!

   ╭──────────────────────────────╮
  ◖│        K 7 M 2 Q 9           │◗
   ╰──────────────────────────────╯

Muéstralo en el mostrador para recoger tu pedido.

●  Pago confirmado
```

El billete es el protagonista. Debajo, el estado con su punto y su rótulo.

<a id="p-panel"></a>

### Panel del mostrador

```
Mostrador
Los pedidos que tenés que atender.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ Refrescar ]            Última carga: 17:42

┃ #128 · Arepa de huevo × 2
┃ Pagado · $ 8.000
┃ [ En preparación ] [ Cancelar ]

┃ #127 · Jugo de mango
┃ Listo para recoger · $ 3.000
┃ [ Entregar ]
```

Las acciones viven **dentro** de la tarjeta del pedido, no en un menú: el
mostrador no tiene tiempo de abrir nada. La hora de última carga va a la derecha
porque es contexto, no algo que haya que leer en cada vistazo.

En pantallas estrechas los botones pasan debajo y ocupan el ancho.

<a id="p-ingreso"></a>

### Ingreso al panel

```
Correo
┌────────────────────────────────┐
│                                │
└────────────────────────────────┘

Contraseña
┌────────────────────────────────┐
│                                │
└────────────────────────────────┘

[ Entrar ]
```

Es la primera pantalla de un turno y se escribe con una mano, así que en móvil
cada campo ocupa el ancho y «Entrar» queda debajo.

La cola **no existe hasta que hay sesión**: `panel.js` decide cuál de las dos
secciones se muestra, y nunca las dos. Hasta la semana 10 esta pantalla no pedía
nada y cualquiera con el enlace movía pedidos de cualquier establecimiento
([V-10](violaciones.md#v-10)).

<a id="implementacion"></a>

## Implementación

**Sin framework y sin paso de construcción.** El contenedor de nginx sirve la
carpeta `sitio/` tal cual, y añadir un compilador obligaría a un build que no
aporta nada a tres archivos.

```
sitio/
  index.html      ← cliente
  panel.html      ← mostrador
  estilos.css     ← esta guía, hecha código
  app.js          ← flujo del cliente
  panel.js        ← cola del mostrador
  config.js       ← dónde vive la API
```

### Reglas técnicas

| Regla | Detalle |
|---|---|
| **Solo tokens** | Ningún color, radio o espaciado fijo fuera de `:root`. Todo es `var(--…)` |
| **Ninguna fuente externa** | Ni CDN ni `@import`. Si se quiere una propia, se autohospeda |
| **Las clases son un contrato** | El JavaScript **escribe** estas, así que renombrar una rompe el comportamiento en silencio: `.activa`, `.oculto`, `.item`, `.item-datos`, `.item-nombre`, `.item-precio`, `.etiqueta-agotado`, `.pedido`, `.acciones`, `.secundario`, `.codigo-canje`, `.estado-linea`, `.punto` *(con `.ok` · `.espera` · `.mal`)*, `.nota`, `.total` |
| **Y los identificadores también** | `app.js` busca las pantallas por el prefijo `pantalla-*` (`pantalla-carta`, `pantalla-pedido`…) y los dos archivos buscan por id cada control. `.pantalla` en cambio solo vive en el marcado y la hoja: cambiarla no rompe nada mientras las dos cambien a la vez |
| **Sin `innerHTML`** | El marcado se construye con `createElement`. Es una propiedad de los archivos actuales que hay que mantener, no una garantía del mecanismo |
| **Movimiento opcional** | Toda animación tiene su caso en `prefers-reduced-motion` |
| **`theme-color`** | Declarado en par claro/oscuro en las dos páginas |
| **Orden de la cascada** | Las reglas de `@media (max-width: 520px)` van **al final** del archivo: tienen la misma especificidad que las de arriba, y antes perdían por orden aunque la consulta coincidiera |

<a id="terminado"></a>

## Definición de «terminado» para una pantalla

Una pantalla no se entrega hasta que estos diez puntos sean ciertos.

| Punto | Verificación |
|---|---|
| **Una acción principal** | Como máximo un botón sólido azul |
| **Solo tokens** | Ningún color, radio o espaciado fijo en el componente |
| **Contraste** | Todo texto pasa AA como mínimo. El cian y el verde no llevan letra |
| **El color no informa solo** | Todo estado tiene rótulo además de color |
| **Objetivos táctiles** | 48 px de alto, 44 en las acciones de la cola |
| **Estados diseñados** | Carga, vacío y error están dibujados y renderizados, no improvisados |
| **Teclado** | Recorrido completo, foco visible con `--foco`, `Esc` cierra los diálogos |
| **Movimiento** | Toda animación tiene su caso en `prefers-reduced-motion` |
| **375 px** | Correcta a 375 px de ancho sin desplazamiento horizontal, y en escritorio |
| **Los dos temas** | Revisada en claro y en oscuro |

Los dos últimos se comprueban mirando, no deduciendo. Los dos defectos que esta
guía corrigió en su primera versión —un rótulo partido en dos líneas y una
tarjeta que perdía su forma— solo se vieron abriendo el navegador.

<a id="decisiones"></a>

## Decisiones confirmadas

Cinco posturas de esta guía, con su motivo.

#### El cian y el verde son superficie, nunca tinta

Medido: 2,05:1 y 1,53:1 sobre blanco, insuficientes incluso para texto grande.
Sobre tinta oscura, 9,24:1 y 12,40:1. Para letra de esos tonos existen
`--cian-tinta` y `--verde-tinta`.

#### El claro es el tema principal

La marca de la universidad es luminosa. El oscuro se conserva para quien lo tenga
puesto, con el azul aclarado porque `#093AD8` sobre fondo oscuro no llega al
mínimo.

#### Ninguna fuente desde un CDN

Añade una petición a un tercero, latencia en la red del campus y un dato que sale
del navegador de quien pide. La del sistema cuesta cero y se renderiza bien en
todo.

#### Sin logotipo, por ahora

La marca es el nombre en azul más el filete de tres colores. No hay archivo que
mantener ni versión invertida que aprobar. Cuando la universidad entregue uno,
entra en la cabecera sin ningún otro cambio.

#### El intervalo de sondeo es un número de diseño

5 000 ms, que es el más largo que cabe en el presupuesto de ESC-03 reservando 4 s
para la persona. Protegido por los dos lados en
`backend/tests/test_escenarios_de_calidad.py`.

---

## Trazabilidad

| Elemento | Dónde |
|---|---|
| Los tokens, vigentes | [`sitio/estilos.css`](../sitio/estilos.css) |
| Umbral de ESC-03 y su medición | [arc42 §10.4](arc42/arc42.md#esc-03) · [§10.7](arc42/arc42.md#evaluacion) · `backend/scripts/medir_esc03.py` |
| Datos personales y la ausencia de registro | [arc42 §8.8](arc42/arc42.md#datos-personales) |
| El precio congelado en el pedido | [V-06](violaciones.md#v-06) |
| La autenticación del panel | [V-10](violaciones.md#v-10) · [ADR-0007](adr/0007-autenticacion-del-panel.md) |
| El estado honesto de un pedido sin confirmar | [ADR-0003](adr/0003-estrategia-integracion.md) |
| El intervalo, protegido | `backend/tests/test_escenarios_de_calidad.py` |
