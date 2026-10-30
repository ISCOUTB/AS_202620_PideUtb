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

**Versión** 2.4 · 30/10/2026 · **Fundamentos** fondo cálido, marca azul de la
UTB y portada fotográfica, con cada contraste medido y **verificado en cada
construcción** por [`test_contraste.py`](../backend/tests/test_contraste.py) ·
tokens vigentes en [`sitio/estilos.css`](../sitio/estilos.css) · **Alcance** las
seis pantallas que hoy existen

> **Qué cambió, en dos pasos.** La 1.0 usaba los tres colores de la Universidad
> Tecnológica de Bolívar y declaraba esa paleta «no negociable». La 2.0 la
> cambió entera por una cálida —fondo crema, ladrillo de asadero— para la
> charla del 3 de noviembre, y perdía algo real: quien abriera el sitio ya no
> veía a la universidad en la pantalla.
>
> La **2.1** separa las dos cosas que la 2.0 había juntado. El fondo crema era
> lo que hacía que esto dejara de parecer una intranet, y se queda. La marca
> vuelve a ser el azul `#093AD8` de la UTB, que además mide mejor: **7,49:1**
> sobre el crema frente a los 6,43 del ladrillo, y **8,05:1** con blanco encima
> frente a 6,92. Era un cambio de identidad disfrazado de cambio de fondo.
>
> La **2.2** añade la portada fotográfica y, con ella, el primer sitio de la
> guía donde el texto no cae sobre un color sino sobre una **imagen**. Eso
> obliga a una regla nueva, porque la de medir no se puede aplicar tal cual: una
> foto tiene un píxel distinto en cada punto y no hay un contraste que escribir.
> Lo que se hace en su lugar está en [Portada](#c-portada), y se resume en una
> frase: se impone un suelo de negro y se mide **el suelo** contra el peor píxel
> que la foto podría traer.
>
> La 2.2 corrige además dos cosas que esta guía venía afirmando y no eran
> ciertas: el punto de estado verde (`.punto.ok`) no existía en la hoja —se
> llamaba `.punto.bien` y ningún guion lo escribía así, de modo que **el punto
> verde nunca fue verde**—, y el punto de «esperando» no late, ni ha latido
> nunca. Ver [Estados y etiquetas](#c-estados).
>
> Lo que **no** ha cambiado en ninguno de los tres pasos es la regla de medir, y
> ahora además se comprueba sola.

> **Esta guía describe lo que hay, no lo que se querría tener.** Cada token que
> nombra existe en `sitio/estilos.css` y cada ratio de contraste está medido. Si
> alguna vez las dos cosas dejan de coincidir, la hoja gana y esta guía está
> desactualizada — que es el defecto que este proyecto ha encontrado tres veces y
> que [arc42 §7.6](arc42/arc42.md#despliegue-deuda) documenta.

<a id="principios"></a>

## Principios

Seis reglas resuelven los casos que esta guía no prevé. Ante la duda, gana la que
protege a quien usa la aplicación con prisa.

#### Parecer comida, no un trámite

La carta se abre con hambre y con el teléfono en la mano. El fondo crema es el
de un asadero, que es lo que El Asao es; el blanco de pantalla con rejilla es el
color de un formulario. Lo que hace que una tarjeta blanca se lea como tarjeta
es que el papel de debajo no sea blanco, y eso no depende de qué color tenga la
marca encima.

Este principio **sustituyó** a «Pertenecer a la UTB», que pedía exactamente lo
contrario: usar los colores del sitio de la universidad para que quien llegara
desde `utb.edu.co` no sintiera que salió de la institución. Era un principio
razonable y se descartó a conciencia, no por descuido. Queda escrito acá para
que el día que alguien quiera volver sepa que hubo una decisión y no un olvido.

#### Una mano, de pie, con prisa

Las dos superficies se usan igual: el cliente pide de pie entre clases, el
mostrador atiende con una mano mientras cocina con la otra. De ahí salen los
objetivos táctiles de 48 px, el apilado en una sola columna y la ausencia de
gestos de precisión. **Ninguna acción importante exige puntería.**

#### El color nunca informa solo

Un color puede pasar sobre una superficie y fallar sobre otra, y hay quien no
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
| **Cabecera** | Título en `--azul`, lema en `--carbon-medio`, y debajo el filete de tres colores. Nunca lleva acciones. | Título `clamp(1.9rem … 2.6rem)` · filete de 4 px |
| **Contenido** | Una columna. En el cliente, una sola pantalla visible: `.pantalla.activa`. En el mostrador, la cola. | Máx. 720 px, centrada · márgenes laterales de 16 px |
| **Pie** | Atribución y enlaces. Separado por una línea. | `--carbon-tenue`, 0,9rem |

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

No hay logotipo. La marca es **el nombre en Fraunces sobre crema**, y con eso
basta: no hay archivo que mantener, ni versión invertida que aprobar, ni un peso
más en la imagen.

```
PideUTB            ← Fraunces 600, --azul, sobre --crema
Pedí sin hacer fila. Recogé con un código.
```

El filete de tres colores desapareció con la paleta de la 1.0. Era lo único
decorativo de la hoja y su función —decir «esto es de la UTB»— dejó de aplicar.
No se sustituyó por otro adorno: la tipografía ya hace ese trabajo.

**Hacer.** En cualquier superficie de color, el título en `--azul` y el lema en
`--carbon-medio`. Sobre la portada fotográfica, los dos en blanco puro.

**Evitar.** Recolorear el título fuera de esos dos casos.

**Sobre una foto, solo con el velo medido.** Hasta la 2.2 esta guía lo prohibía
sin matices, y el motivo era bueno: sobre una fotografía el contraste no se
puede escribir, porque depende del píxel. La prohibición se levanta únicamente
donde hay un suelo de negro medido debajo —ver [Portada](#c-portada)—. Sin ese
suelo la regla vieja sigue en pie: el título no va sobre una imagen.

El día que la universidad entregue un logotipo, entra en la cabecera a la
izquierda del título sin ningún otro cambio.

<a id="colores"></a>

## Colores

Tres familias, tres funciones: la marca (azul y ámbar), la estructura (cremas y
carbones) y los estados (verde de canje y rojo de error).

### La regla que gobierna la paleta, y por qué sobrevive a cualquier paleta

> **Ningún color se usa como tinta sin haber medido su contraste contra la
> superficie concreta donde cae.**

No contra blanco «porque sí»: contra la que tiene debajo. Y desde la 2.0 eso no
es una promesa, es una prueba:
[`backend/tests/test_contraste.py`](../backend/tests/test_contraste.py) vuelve a
calcular cada par en cada construcción, **y además comprueba que los números
escritos en los comentarios de la hoja sean esos números**.

Esa prueba nació de un susto concreto. Al pasar el fondo de blanco a crema,
`--verde-tinta` —documentado en 4,81:1 sobre blanco, y era cierto— quedaba en
**4,48:1** sobre el fondo nuevo, por debajo del mínimo AA. El comentario seguía
diciendo la verdad sobre una superficie que ya no existía.

**Cambiar un fondo invalida en silencio los contrastes de todo lo que va
encima.** Nadie lo nota mirando la pantalla, porque la diferencia entre 4,48 y
4,50 no se ve. Se ve el día que alguien no puede leer un precio al sol.

### Marca

Las dos relaciones de cada fila son las que importan: como tinta sobre el fondo
de la página, y con texto blanco encima cuando hace de botón.

| Token | Valor | Sobre `--crema` | Con blanco encima | Uso |
|---|---|---|---|---|
| `--azul` | `#093AD8` | **7,49:1** | **8,05:1** | Botones, enlaces, título, precio en promoción |
| `--azul-hundido` | `#0730AB` | 9,67:1 | **10,40:1** | Hover y pulsado: el mismo tono, más grave |
| `--azul-niebla` | `#E8EDFD` | — | — | Fondo del hueco de foto y del secundario en hover |
| `--ambar` | `#92400A` | 6,60:1 | **7,09:1** | La etiqueta de la franja de promoción |
| `--ambar-niebla` | `#FDF0DC` | — | — | Su fondo |

`--azul` es el único tono de la paleta que puede ser tinta **y** fondo de texto
blanco. Por eso es el primario: un color que solo sirve para una de las dos cosas
obliga a tener dos.

La 2.0 tenía una fila más, `--brasa-viva`, documentada con su contraste y su
regla de uso. Ninguna regla de la hoja la usaba. No se tradujo al azul: se
quitó. Una guía que describe un color que nadie aplica no describe el sistema,
lo adorna.

### Estructura

| Token | Valor | Sobre `--crema` | Uso |
|---|---|---|---|
| `--carbon` | `#1C1917` | **16,26:1** | Cuerpo de texto |
| `--carbon-medio` | `#57514C` | **7,27:1** | Texto secundario: precios, rótulos, lema |
| `--carbon-tenue` | `#6E6660` | **5,23:1** | **Solo metadatos.** Nunca información esencial |
| `--papel` | `#FFFFFF` | — | Tarjetas, campos, diálogos |
| `--crema` | `#FBF6EF` | — | Fondo de página |
| `--crema-hundido` | `#F3EBE0` | — | Separadores y fondos de apoyo |
| `--linea` | `#E9DED0` | — | Separadores |
| `--linea-fuerte` | `#D6C6B2` | — | Borde de campos y de botones secundarios |

**Que el fondo no sea blanco es lo que hace que una tarjeta blanca se lea como
tarjeta** sin necesitar un borde. Es la razón de que haya dos superficies y no
una.

`--carbon-tenue` pasa AA con 5,23:1 pero no AAA. De ahí la restricción: sirve
para la hora de última carga o una nota de ayuda, **nunca** para un precio, un
estado o un mensaje de error.

### Estados

Reservados para los estados y siempre con rótulo. **El rojo nunca es un color de
acción**: solo señala que algo salió mal.

| Token | Valor | Fondo | Contraste sobre su fondo | Uso |
|---|---|---|---|---|
| `--ambar` | `#92400A` | `--ambar-niebla` `#FDF0DC` | **6,31:1** | Franja de promoción, esperando |
| `--verde-canje` | `#356F1A` | `--crema` | **5,68:1** | «Listo para recoger» · el billete del código |
| `--error` | `#B3261E` | `--error-fondo` `#FDECEA` | **5,72:1** | Pago rechazado, fallo de red |

El ámbar de marca habitual (`#FFB020`) no aparece: con 1,9:1 sobre blanco no
puede llevar texto. `--ambar` es ese ámbar oscurecido hasta ser legible.

**El verde sobrevivió al cambio de paleta porque es semántica, no decoración**:
es el color del momento en que la comida está lista. Lo que cambió es su valor —
de `#3E811E` a `#356F1A`— por el motivo de arriba: sobre crema, el anterior se
quedaba en 4,48:1.

<a id="un-solo-tema"></a>

### Un solo tema, y es el claro

**No hay tema oscuro.** Lo hubo —seguía al del sistema, con el azul aclarado
para no caer por debajo del mínimo legible— y se quitó.

El motivo es que nadie lo elegía. Se heredaba del sistema, así que la misma
página se veía de dos maneras según el aparato con que se abriera, y una de las
dos no se miraba con cuidado: los defectos de contraste y de jerarquía que esta
guía fue corrigiendo se revisaron casi siempre en claro. Un tema que no se mira
es un tema que miente.

Y el claro es el que corresponde: la marca de la universidad es luminosa, y la
carta se abre con el teléfono en la mano, a menudo al sol.

**Lo que cuesta:** quien tiene el sistema en oscuro ve una página clara. Es
consciente. El historial de git conserva la paleta completa con sus contrastes
medidos, por si se decide volver — y volver significaría revisarla pantalla por
pantalla, no solo reactivarla.

<a id="tipografia"></a>

## Tipografía y cuadrícula

**Dos familias, autohospedadas, ninguna cargada desde un CDN.**

```css
--fuente-titulo: "Young Serif", Georgia, "Times New Roman", serif;
--fuente:        "Hanken Grotesk", system-ui, -apple-system, "Segoe UI", sans-serif;
```

> **La serif titula, la de palo informa.** Un precio en serif se lee más despacio,
> y un precio hay que leerlo rápido.

La 1.0 usaba solo la fuente del sistema y escribió la condición para cambiarlo:
«si alguna vez se quiere una tipografía propia, se **autohospeda** en el
contenedor; no se enlaza». Eso es exactamente lo que se hizo, y no por purismo:
el 3 de noviembre el público abre el sitio a la vez desde la red de un
auditorio, y una petición menos a `fonts.gstatic.com` es un punto menos donde la
demostración se queda sin tipografía delante de todos.

Las dos están recortadas al subconjunto latino, que cubre el español entero:
**61,7 KB entre las dos**, con `font-display: swap` para que el texto aparezca de
inmediato con la fuente del sistema y cambie cuando la nuestra llegue. En una
demostración en vivo, texto feo al instante gana a texto bonito dentro de dos
segundos.

**La 2.3 cambió las dos caras.** Eran Fraunces e Inter, 115,6 KB, y las dos
salían marcadas como caras que de tanto usarse han dejado de distinguir a nada.
El cambio cuesta la mitad del peso, y en la red de un auditorio con doscientos
teléfonos abriendo a la vez, 54 KB menos no es una cifra decorativa.

**Young Serif tiene un solo peso, y eso manda sobre toda la escala de abajo.**
Es cara de titular y su 400 pesa ya más que el 600 de la serif que sustituyó,
así que la jerarquía la llevan el tamaño y el aire, no el grosor. Pedirle un 600
no da nada más grueso: el navegador inventa el peso engrosando el contorno en el
sitio. Medido en Chrome a 72 px, el ancho no se mueve y la tinta sube un 31 %, y
pedir 900 da la misma tinta que 700 porque la falsificación se satura. No falla,
no avisa, solo se ve peor — por eso lo vigila
`test_ningun_titulo_pide_un_peso_que_la_cara_no_tiene`.

Hanken Grotesk sí es variable, de 300 a 900, y trae las cifras de ancho fijo de
serie: se comprobó midiendo el ancho de `111111` contra el de `000000`, que es
lo que decide si un total salta al pasar de 9 a 10.

Licencia y procedencia en [`sitio/fuentes/LEEME.md`](../sitio/fuentes/LEEME.md).

Esta tabla venía describiendo una escala que la hoja no tenía: pesos de 800,
750 y 650, y un código de canje «monoespaciada · espaciado 0,22 em» que nunca
lo fue. Son los valores reales, leídos de `sitio/estilos.css`.

| Función | Cara | Tamaño / interlineado | Grosor | Uso |
|---|---|---|---|---|
| Título de marca (`h1`) | Titular | `clamp(1.75rem, 6vw, 2.25rem)` / 1,15 · espaciado −0,015 em | 400 | Uno por página |
| Título de sección (`h2`) | Titular | `clamp(1.35rem, 4.5vw, 1.6rem)` / 1,15 | 400 | Secciones |
| Título de bloque (`h3`) | Titular | 1,1rem / 1,15 | 400 | Diálogos, paneles |
| Nombre de ítem | Cuerpo | 1rem / 1,3 | 600 | Tarjetas |
| Cuerpo | Cuerpo | 16px / 1,55 · cifras tabulares | 400 | Textos y campos |
| Descripción de ítem | Cuerpo | 0,875rem · `--carbon-tenue` | 400 | Debajo del nombre |
| Rótulo del billete | Cuerpo | 0,78rem · versalitas · espaciado 0,08 em | 600 | «Tu código de recogida» |
| Código de canje | Titular | `clamp(2.25rem, 13vw, 3.5rem)` · espaciado 0,14 em | 400 | Solo el código |

Los tres títulos comparten grosor **a propósito**: con una cara de un solo peso,
pedir otro no da otro. Lo que los separa es el tamaño, y eso basta porque nunca
aparecen dos del mismo nivel juntos.

El interlineado del cuerpo es 1,55, más holgado que el de una aplicación de datos:
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
| `--radio` | 18 px | Tarjetas, diálogos, el billete del código |
| `--radio-chico` | 12 px | Campos, destinos de la barra, esqueletos |
| `--radio-pildora` | 999 px | Botones, etiquetas, pastillas de estado |
| `--radio-hoja` | 26 px | **Una sola cosa:** la esquina con la que la carta se monta sobre la portada. A todo el ancho de la pantalla, 18 px se leen como un recorte |
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

<a id="c-portada"></a>

### Portada

La franja de arriba de la carta lleva una fotografía de la parrilla. No es
decoración: lo que se vende es comida, y una carta que alguien abre con hambre
no empieza bien por el nombre del servicio sobre un fondo plano.

```
┌──────────────────────────────────────┐
│                                      │  velo 14 %   ← se ve la carne
│          (la parrilla)               │
│                                      │  velo 34 %
│ ····································· │
│  PideUTB                             │  velo 72 %   ← el suelo medido
│  Pedí sin hacer fila.                │
└──────────────────────────────────────┘
 ╭────────────────────────────────────╮   --radio-hoja, el crema encima
 │  Carta                             │
```

**Qué se queda fuera.** La portada es la franja y nada más. Debajo de la esquina
redondeada empieza el crema y todo sigue igual: las tarjetas, los precios, el
carrito, la paleta entera. Un encabezado oscuro no es un tema oscuro, y esta
guía sigue teniendo [un solo tema, y es el claro](#un-solo-tema).

#### El velo, que es lo único medible

| Token | Valor | Para qué |
|---|---|---|
| `--velo-portada` | `72%` | El mínimo de negro que hay entre la foto y el texto |
| `--negro-velo` | `14 9 6` | Con qué negro. Cálido, no neutro: un gris sobre una foto de fuego la apaga y la vuelve ceniza |

Sobre un color, el contraste se calcula. Sobre una foto no: hay uno distinto en
cada píxel. Así que en vez de medir el contraste se **impone un suelo** y se mide
el suelo contra el peor caso que la fotografía podría ofrecer, que es un píxel
blanco puro:

```
blanco (255 255 255) con 72 % de #0E0906 encima → #514E4C
texto blanco sobre #514E4C                      → 8,38:1
```

Ese 8,38:1 es el **peor** caso, no el habitual: con la foto real el texto se
apoya en algo bastante más oscuro. `test_contraste.py` rehace la cuenta en cada
construcción, y es la prueba que va a saltar el día que alguien mire la portada,
le parezca apagada y aclare el velo para que la carne luzca — que es una reacción
razonable, y por eso conviene que haya un número que diga hasta dónde.

#### Y por qué el suelo es una regla, no un cálculo

El número de arriba solo vale si **todo** el texto cae sobre el velo plano. Eso
no se consigue calculando dónde acaba cayendo —cambia con el ancho, con el
tamaño de letra del sistema y con lo que mida la frase— sino con la estructura:

- la portada es una rejilla de dos filas;
- la de arriba lleva el degradado, que sube de `--velo-portada` a 14 %;
- la de abajo lleva el velo **plano**, y el texto vive dentro de ella.

Las dos capas se encuentran en el mismo valor, así que no hay costura: lo que se
ve es una sola foto que se oscurece hacia abajo. Hay una prueba para cada mitad
de esa frase.

#### La foto

| Archivo | Tamaño | Dónde |
|---|---|---|
| `fotos/portada-movil.webp` | 640 px · 34 KB | Por defecto |
| `fotos/portada.webp` | 1024 px · 61 KB | A partir de 768 px |

El teléfono se lleva el pequeño, y eso importa más de lo que parece: el 3 de
noviembre el sitio se abre a la vez desde la red de un auditorio.

**Debajo de la foto hay un color opaco** (`#241711`), y no es un adorno de
reserva: hasta que la imagen llega —o si no llega, que en esa red es un caso
real— el texto blanco caería sobre crema y no se leería. Con el color debajo, lo
peor que pasa es una franja oscura sin foto.

**Sustituir la foto es cambiarle el nombre.** Va dentro de `estilos.css`, que
lleva huella en la URL, así que cambiar la hoja cambia su dirección; lo que eso
no cubre es reemplazar el archivo dejándole el mismo nombre, y entonces
Cloudflare serviría la vieja durante cuatro horas. Misma regla que las
tipografías.

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
┃│  ┌────┐  Punta de anca               │   filete de acento, 4 px
┃│  │foto│  Término medio, 250 g   ┌──┐ │   --cian en la carta
┃│  └────┘  $ 26.000               │+ │ │   --azul en la cola
┃└─────────────────────────────────└──┘─┘
   64 px
```

| Estado | Apariencia |
|---|---|
| Normal | `--papel`, `--sombra`, borde `--linea` |
| Hover | `--sombra-alta` y 2 px de elevación — **solo con puntero fino**, ver [Pasar por encima y tocar](#c-tacto) |
| En la cola del mostrador (`.pedido`) | Filete `--azul` |
| Agotado (`.agotado`) | Fondo `--crema-hundido`, sin sombra, no se levanta. Foto al 45 %; nombre y precio en `--carbon-medio`, descripción en `--carbon-tenue`; etiqueta `--papel` sobre `--carbon-medio` |

**El agotado conserva la tarjeta.** Quitarle el fondo lo convertía en un hueco en
la lista en vez de en un plato que hoy no hay.

**Y conserva su texto legible, que es el arreglo de la 2.3.** Esto se atenuaba
con `opacity: 0.6` sobre la tarjeta entera, y era un fallo de accesibilidad
medido: la descripción caía a **2,50:1** y la etiqueta «Agotado» a **2,79:1**,
las dos por debajo de 4,5:1. La excepción de la norma para controles inactivos
no cubría nada de esto, porque esta tarjeta **no tiene ni un botón**: es texto
informativo, y el texto informativo no tiene excepción.

Lo que más dolía era lo único que hay que leer ahí. La palabra que te dice que
no hay era la menos legible de la tarjeta.

| | Antes | Ahora |
|---|---|---|
| Nombre y precio | 4,58:1 | **6,61:1** |
| Descripción | 2,50:1 | **4,76:1** |
| Etiqueta «Agotado» | 2,79:1 | **7,82:1** |

La no disponibilidad se dice ahora con lo que puede apagarse sin dejar de
leerse: el fondo se hunde, la sombra desaparece, la tarjeta no se levanta al
pasar por encima, y la foto —que es una imagen, no texto— sí baja de opacidad.
Los textos bajan de jerarquía **cambiando de token**, que es lo que
`test_contraste.py` sabe medir; la opacidad compone el color después, en el
navegador, y por eso una prueba de tokens no la ve. Eso lo vigila ahora
`test_un_producto_agotado_no_apaga_su_texto`.

**La foto va a la izquierda, no arriba.** En una lista vertical, una imagen a
todo lo ancho empuja el precio fuera de la pantalla y obliga a desplazarse para
comparar dos cosas.

**Sin foto se dibuja la inicial, no un hueco.** `imagen` es nulo mientras el
archivo no exista, y ese estado es el normal al cargar una carta nueva. El
marcador va sobre `--azul-niebla` con la inicial en `--azul` para que se lea
como una pieza del sistema y no como una imagen rota.

### Filtro por categoría

```
( Todas )( Adiciones )( Asados )( Bebid…
└── elegida: --azul macizo        └── se corta a propósito
```

Pastillas en una fila que se desplaza. En móvil son más anchas que la pantalla a
propósito: **el corte en el borde derecho es lo que dice que hay más**.
Envolverlas en dos filas gasta alto y pierde esa señal.

Las categorías salen de los datos, no de una lista fija: añadir una en la base la
hace aparecer sin tocar el marcado. Un producto sin categoría no inventa una,
aparece solo en «Todas». **Con una sola categoría el filtro no se dibuja**, porque
un control que no filtra nada ocupa sitio sin hacer nada.

| Estado | Apariencia |
|---|---|
| Normal | `--papel`, borde `--linea-fuerte`, texto `--carbon-medio` |
| Elegida (`aria-pressed="true"`) | `--azul` macizo, texto blanco |

### Control de cantidad

```
sin nada en el carrito          con cantidad
┌────┐                      ┌────┐ 2 ┌────┐
│ +  │                      │ −  │   │ +  │
└────┘                      └────┘   └────┘
 44 px                         118 px en total
```

Los dos ocupan el mismo sitio: **la acción siguiente está siempre donde estaba la
anterior**, así que el dedo no tiene que buscar.

Dice `+` y no «Agregar» por una medida, no por estética: con la palabra el botón
ocupaba 111 px de los 343 de una pantalla de 375, dejaba 97 px para el nombre, y
nueve de los diez productos de una carta real partían en dos líneas. El signo
deja 171 px y los acepta todos. La palabra no se pierde, va en `aria-label`.

El grupo `−/n/+` vuelve a dejar 97 px, así que **por debajo de 520 px baja a su
propia fila**, alineado a la derecha. Por encima cabe al lado. El corte es el
mismo 520 px que ya usa el resto de la hoja: las cuentas dan 443, pero un segundo
punto de ruptura a 77 px del primero cuesta más de mantener de lo que ahorra.

El `+` se apaga en 50, que es el tope que el contrato declara por línea: el botón
se apaga antes en vez de dejar pedir algo que la API va a rechazar con `422`.

### Barra de navegación

```
móvil                               escritorio
┌─────────────────────────────┐    ┌──────────────────────────────────┐
│  ╭───────────╮              │    │ Carta  Mi código    [3 productos]│
│  │3 productos│③            │    └──────────────────────────────────┘
│  ╰───────────╯              │       pegajosa arriba
│ Carta             Mi código │
└─────────────────────────────┘
      fija abajo, siempre
```

Sustituye a la barra del carrito de la 1.0, que flotaba sobre la carta y
desaparecía fuera de ella.

**Tres destinos, y los tres llevan a algún sitio.** Las referencias de las que
sale este rediseño llevan cinco pestañas —inicio, menú, ofertas, perfil, pedido—
porque son aplicaciones con cinco secciones. Esta tiene una carta, un carrito y
un código. Poner dos pestañas más sería prometer una aplicación que no existe, y
en este proyecto ya pasó: unos botones con `role="radio"` anunciaban un grupo de
radios cuyas flechas no funcionaban.

**Se deshabilita, no se esconde.** Un control que aparece y desaparece mueve el
contenido de sitio y obliga a reaprender dónde estaba; uno apagado dice «esto
existe y todavía no». Con el pulgar sobre una lista que se desplaza, lo segundo
se agradece.

| Destino | Cuándo se puede pulsar |
|---|---|
| **Carta** | Cuando la carta ya llegó. Antes llevaría a una pantalla en blanco |
| **Carrito** (central, elevado) | Con algo dentro. Lleva la cuenta y el total encima |
| **Mi código** | Cuando hay un pedido que mirar |

El botón central va elevado porque **es la acción, no un destino**, y lleva una
chapa con la cantidad que da un salto al cambiar: confirma que el toque hizo algo
sin necesidad de un mensaje.

En escritorio la barra deja de estar abajo y se pega arriba: pegada al borde
inferior de un monitor de 27", una barra de navegación queda a medio metro del
contenido que acompaña. Eso obliga a que el `<nav>` vaya **antes** del encabezado
en el documento —`position: sticky` respeta el orden del documento, y al final
del `<body>` la barra se quedaba debajo del pie—.

El fondo llega de borde a borde —una barra fija recortada se lee como un error—
pero su contenido se alinea con la columna del resto de la página.

### Esqueletos

```
┌──────────────────────────────┐
│ ▓▓▓▓  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓         │   × 3
│ ▓▓▓▓  ▓▓▓▓▓▓▓▓               │
└──────────────────────────────┘
```

Lo que se ve mientras la carta viaja. **No es decoración: ocupan el mismo sitio
que van a ocupar los productos**, así que cuando llegan los datos la página no da
el salto que da cuando algo aparece de la nada.

Y la pantalla de la carta se enseña **antes** de pedirla, con lo cual el
encabezado y el filtro ya están en su sitio desde el primer fotograma.

Tres y no diez. Con el teléfono en la mano se ven tres tarjetas; fingir diez para
rellenar la pantalla le dice a quien espera que falta más de lo que falta.

### Código de canje

El momento alto de la aplicación: lo que el cliente enseña para recoger. Se trata
como un **billete**, y es el único sitio donde el verde se usa entero —porque ahí
es fondo y no letra—.

```
┌──────────────────────────────────────┐
│       TU CÓDIGO DE RECOGIDA          │  --carbon-tenue, versalitas
│  ╭────────────────────────────────╮  │
│  │        K 7 M 2 Q 9             │  │  fondo --verde-canje
│  ╰────────────────────────────────╯  │  blanco encima · 6,10:1
│          ( ● En preparación )        │  pastilla --crema-hundido
└──────────────────────────────────────┘
```

Los tres datos van en la misma tarjeta porque son la respuesta a una sola
pregunta —«¿y el mío?»— y se miran juntos: qué es, cuál es, y qué está pasando
con él. Repartirlos por la pantalla obliga a buscar dos de los tres.

| Parte | Clase | Nota |
|---|---|---|
| La tarjeta | `.billete` | Fondo `--papel` sobre el crema de la pantalla |
| El rótulo | `.billete-rotulo` | Dice qué es el número. Sin él, un código de seis caracteres puede ser cualquier cosa |
| El código | `.codigo-canje` | `clamp(2.25rem, 13vw, 3.5rem)`: en la charla esto se proyecta y tiene que leerse desde la última fila |
| El estado | `.billete-estado` | Pastilla con punto y rótulo. **La palabra es la del mostrador**, no una traducción |

**El estado dice la palabra del mostrador, y eso es el punto.** El título de la
pantalla ya cuenta lo que el estado significa para quien pidió —«Lo están
preparando»—; la pastilla dice cómo lo llama la otra pantalla —«En
preparación»—. Son lo mismo y no se parecen, y la conversación que ocurre en una
barra con ruido es «a mí me dice tal» / «a mí me sale tal».
`test_escenarios_de_calidad.py` falla si las dos tablas de etiquetas se
desvían.

| Variante | Uso |
|---|---|
| `.billete` | La pantalla de resultado del cliente |
| `input.codigo-canje` | El diálogo de entrega del mostrador: mismo tratamiento, fondo `--papel`, sin muescas, `text-transform: uppercase` |

La conversión a mayúsculas del campo es **visual**: el servidor compara sin
distinguir la caja, así que no cambia lo que se envía.

<a id="c-advertencia"></a>

### Advertencia antes de perder un código

```
┌──────────────────────────────────────┐
│ Guardá tu código antes de seguir     │  --ambar, Fraunces
│ Ya pagaste este pedido y su código   │
│ es K7M2Q9. Si empezás otro, esta     │  fondo --ambar-niebla
│ pantalla deja de mostrarlo…          │  borde --ambar
│                                      │
│ [ Seguir viendo mi código ]          │  primario: el que no destruye
│ [ Ya lo anoté, hacer otro pedido ]   │  secundario
└──────────────────────────────────────┘
```

**Ámbar y no rojo.** El rojo es el color de lo que ya salió mal, y aquí no ha
salido nada mal: el pedido está pagado y el código es bueno. Lo que hay es una
decisión con consecuencia, que es para lo que `--ambar` existe.

| Regla | Por qué |
|---|---|
| Ocupa el sitio del botón que la abrió | El código sigue a la vista mientras se lee la advertencia, que es de lo que trata la advertencia |
| El primario es el que **conserva** | El botón grande y lleno nunca es el que destruye |
| El foco entra en el primario | Quien llegue con el teclado y pulse Intro sin leer se queda donde estaba |
| **Solo cuando hay algo que perder** | Con el pedido entregado, cancelado o sin pagar no aparece. Una confirmación que sale siempre se aprende a despachar sin leerla, y deja de proteger de nada |
| No se cierra sola | Vive fuera del cuerpo de la pantalla, que se repinta cuando el mostrador mueve el pedido. Si viviera dentro, desaparecería bajo el dedo de quien la está leyendo |

<a id="c-estados"></a>

### Estados y etiquetas

```
●  Pagado · Listo para recoger · Entregado   --verde-canje
●  Esperando pago · En preparación           --ambar
●  Cancelado · El pago fue rechazado         --error
```

| Clase | Color | Significado |
|---|---|---|
| `.punto.ok` | `--verde-canje` | Confirmado, listo, entregado |
| `.punto.espera` | `--ambar` | Esperando algo |
| `.punto.mal` | `--error` | Rechazado o cancelado |
| `.etiqueta-agotado` | `--papel` sobre `--carbon-medio` · 7,82:1 | Agotado |

**El punto nunca va solo**: siempre lleva su rótulo al lado, y esa es la razón
por la que el color no es información única. Quien no distingue verde de ámbar
lee «En preparación» igual que todo el mundo.

**Las dos correcciones de la 2.2, porque las dos venían de aquí.**

La primera: esta tabla decía `.punto.ok` y la hoja declaraba `.punto.bien`. Los
tres guiones que pintan puntos escriben `ok`, así que durante todo el proyecto
**el punto verde cayó en el gris por defecto de `.punto`** —el mismo que
significa «estado que no reconozco»—. Nadie lo vio, porque un punto gris parece
un punto; no hay consola que se queje de una clase que no existe, y el ojo no
echa de menos un verde que no ha visto nunca. Lo destapó necesitarlo: el estado
pasó a ir junto al código, donde el color hace trabajo.

La segunda: esta guía decía que el punto de «esperando» **late**, y presentaba
ese latido como la mitigación para quien no distingue colores. No late. No ha
latido nunca: no hay animación en la hoja ni la ha habido. Se ha quitado la
frase en vez de escribir la animación, porque la mitigación que sí existe —el
rótulo siempre al lado— ya cubre lo que el latido iba a cubrir, y una animación
que nadie necesita es una animación que hay que mantener.

Desde la 2.2, `test_escenarios_de_calidad.py` comprueba que toda clase de punto
que un guion escriba exista en la hoja, y que ninguna regla sobre. Es la prueba
que habría encontrado lo primero el día que se escribió.

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
| `::backdrop` propio | No hereda del documento, así que el velo hay que declararlo aunque haya un solo tema |
| «Cancelar» a la derecha de la acción | En el mostrador el pulgar llega antes al borde derecho |
| Cierre con `Esc` | Nativo de `<dialog>`; no se desactiva |

<a id="patrones"></a>

<a id="c-tacto"></a>

### Pasar por encima, y tocar

El táctil **no tiene hover**, así que el navegador se lo inventa: el primer
toque aplica `:hover` y lo deja puesto hasta que la persona toque otra cosa.
Las nueve reglas de `:hover` de la hoja estaban sueltas y sin compuerta, y en
un teléfono eso se veía — tocar una tarjeta la dejaba levantada dos píxeles,
tocar «Agregar» lo dejaba azul oscuro como si siguiera pulsado. Todo el
recorrido del público es en teléfono.

Van las nueve juntas detrás de `@media (hover: hover) and (pointer: fine)`.
Hacen falta las dos condiciones: la primera dice que el puntero principal
puede posarse, la segunda que además es preciso, y eso descarta los lápices y
los Android que declaran hover sin tenerlo. Lo vigila
`test_ningun_hover_queda_suelto_fuera_de_su_compuerta`.

Y están al final del archivo por cascada, no por orden estético: una consulta
de medios **no sube la especificidad**, solo decide si la regla participa.
Antes ganaban por orden de aparición; metidas en una compuerta a mitad del
archivo habrían perdido contra las reglas en reposo de más abajo.

| Lo que toca el dedo | Lo que devuelve |
|---|---|
| Destino de la barra, categoría | Fondo `--crema-hundido` y `scale(0.97)` |
| Tarjeta de producto | `scale(0.99)` |
| Botón | `scale(0.985)` |
| Botón central del carrito | `scale(0.96)` |
| Método de pago | Borde `--azul` |

**Quitar el resaltado del navegador obliga a poner uno propio.** El recuadro
translúcido que iOS y Android pintan sobre lo que se toca es la señal más
ruidosa de «esto es una página web», y pelea con la respuesta que sí está
diseñada. Se quita en la raíz con `-webkit-tap-highlight-color: transparent`,
y a cambio todo lo tocable lleva su `:active` — 120 ms, salida suave. Quitar
la única respuesta que daba el navegador sin poner otra sería cambiar un
defecto por otro peor.

**`touch-action: manipulation`** en los controles renuncia al doble toque para
ampliar *sobre ellos*, y con eso el navegador deja de esperar por si llega un
segundo toque. No se renuncia a ampliar la página: pellizcar sigue intacto, y
`user-scalable=no` no está en ningún sitio porque es un fallo de
accesibilidad.

**`user-select: none` va solo en controles.** Mantener el dedo sobre un botón
no debe seleccionar su etiqueta: eso delata a un control que no es nativo.
Pero el código de recogida, los totales y los mensajes de error son
**contenido**, y ahí poder copiar es justo lo que se quiere — el código lleva
`user-select: all`, así que un toque lo selecciona entero.

**La selección y el cursor también son del sistema de diseño.** Venían con el
azul del sistema operativo, que no pertenece a ninguna paleta. `::selection`
usa `--azul-niebla` sobre `--carbon`, que son dos tokens ya medidos, y el
cursor de texto usa `--azul`. Son dos líneas y de lo poco que distingue una
página construida de una ensamblada.

## Patrones de interacción

Las mismas situaciones se resuelven siempre igual.

| Situación | Patrón | Ejemplo |
|---|---|---|
| **Avanzar en el flujo del cliente** | Una pantalla visible a la vez, `.pantalla.activa`, con una entrada de 0,22 s | Carta → pedido → espera → resultado |
| **Esperar algo que no depende de nosotros** | Estado consultable más sondeo. Nunca una pantalla bloqueada | Esperando la confirmación del pago, cada 3 s |
| **Enterarse de un cambio ajeno** | Sondeo con intervalo atado a su umbral | La cola del mostrador, cada 5 s; el estado del pedido en el teléfono de quien pidió, también cada 5 s |
| **Decisión que destruye algo que no se puede recuperar** | Advertencia en el sitio del botón, con lo que se va a perder a la vista, y confirmación explícita | [Hacer otro pedido con un código sin recoger](#c-advertencia) |
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

#### Dos esperas, dos cadencias

La pantalla del cliente sondea a dos ritmos distintos, y la diferencia no es de
ahorro:

| Qué se espera | Cada | Por qué |
|---|---|---|
| La confirmación del pago | 3 s | Llega de un sistema externo en cualquier instante, y quien espera está mirando la pantalla con el teléfono en la mano |
| Que el mostrador avance el pedido | 5 s | Lo mueve una persona con una plancha delante, y el panel refresca su propia cola cada 5 s: preguntar más rápido no puede enterarse de nada antes de que exista |

**Y el sondeo no se para al confirmarse el pago.** Se paraba, y era un defecto:
la pantalla se quedaba congelada en «Pago confirmado» mientras el mostrador
movía el pedido a «En preparación» y a «Listo para recoger». Las dos pantallas
decían cosas distintas del mismo pedido, y la que se equivocaba era la de quien
había pagado. Ahora se sigue preguntando hasta que el pedido llega a un estado
del que no se mueve —entregado o cancelado—, y ahí sí se para.

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

Ocho pantallas: cinco del cliente, dos del mostrador y una que no es de
PideUTB. Son todas las que hoy existen.

<a id="p-carta"></a>

### La carta

```
┌──────────────────────────────────────┐
│          (la parrilla)               │
│  PideUTB                             │  ← portada, velo 72 % bajo el texto
│  Pedí sin hacer fila. Recogé con…    │
└──────────────────────────────────────┘
 ╭────────────────────────────────────╮   el crema se monta encima
 │                                     │
   Carta

   ( Todas )( Adiciones )( Asados )( Bebid…

┃ ┌──┐ Pechuga asada              ┌──┐
┃ │  │ Con papa criolla y ensalada│+ │
┃ └──┘ $ 18.000                   └──┘

┃ ┌──┐ Punta de anca
┃ │ P│ Término medio, 250 g
┃ └──┘ $ 26.000
┃                       ┌──┐ 2 ┌──┐
┃                       │− │   │+ │
┃                       └──┘   └──┘

│ ┌──┐ Costilla BBQ
│ │ C│ Media libra en salsa  ( Agotado )
│ └──┘ $ 24.000

┌──────────────────────────────────────┐
│ 3 productos          [ Ver mi pedido ]│
│ $ 60.000                              │
└──────────────────────────────────────┘
```

Una tarjeta por ítem: foto a la izquierda, nombre, descripción en `--carbon-tenue`
y precio, y el control a la derecha. Los agotados **no se ocultan**: saber que
algo existe y hoy no hay es información, y ocultarlo haría que el cliente lo
busque.

La segunda tarjeta muestra el estado con cantidad en móvil, con el control en su
fila. La barra de abajo aparece con el primer producto.

Arriba, la [portada](#c-portada): la foto llega hasta los dos bordes y se corta
donde empieza la esquina redondeada del crema. Lo que hay debajo de esa esquina
—las tarjetas, los precios, el filtro, el carrito— no cambió con ella.

<a id="p-pedido"></a>

### Tu pedido

```
Tu pedido

┃ Punta de anca        ┌──┐ 2 ┌──┐
┃ 2 × $ 26.000         │− │   │+ │
┃                      └──┘   └──┘

┃ Limonada de coco     ┌──┐ 1 ┌──┐
┃ 1 × $ 8.000          │− │   │+ │
┃                      └──┘   └──┘

┌──────────────────────────────────┐
│  Total               $ 60.000    │
└──────────────────────────────────┘

¿Cómo querés pagar?

( Tarjeta           )
(✓ Nequi            )   ← elegido
( PSE               )

[ Pagar $ 60.000    ]   ← macizo, ancho completo

[ Seguir pidiendo   ]
```

El resumen antes de la acción, con una línea por producto y la cantidad
editable: **es donde la gente se arrepiente**, y obligar a navegar hacia atrás
para quitar algo es la forma más fácil de perder una venta. Quitar el último
producto devuelve a la carta.

**Elegir un método no cobra.** Son opciones que se marcan; el cobro lo dispara
«Pagar», que además dice cuánto. Antes el método y la confirmación eran el mismo
gesto y un toque accidental cobraba.

Los métodos no van en azul macizo: así parecían tres formas de pagar ya y pesaban
más que la acción de verdad. **El único botón macizo de la pantalla es el que
cobra.** El elegido se distingue por relleno, por borde y por el `✓` —no solo por
color—.

**Son `<input type="radio">` de verdad, no botones con `role="radio"`.** Y la
distinción no es de pureza: con el rol puesto a mano, un lector de pantalla
anuncia un grupo de radios y **las flechas no mueven la selección**, porque eso
hay que implementarlo aparte —*roving tabindex*— y no estaba. Prometía un
comportamiento que no existía. Con inputs reales, las flechas, el anuncio «1 de
3» y el agrupamiento salen del navegador y no hay nada que mantener.

De ahí salen dos reglas que valen para cualquier control que se añada:

- **El estado lo tiene el control, no una clase.** La pastilla se marca con
  `:checked` en CSS y no con una clase que ponga JavaScript, que es lo que se
  puede quedar desincronizado con lo que el navegador cree.
- **El `<input>` se esconde a la vista, nunca al teclado.** `display: none` lo
  saca del orden de tabulación y del árbol de accesibilidad a la vez, que es la
  forma habitual de romper esto sin notarlo. Se oculta recortándolo
  (`clip-path`), y el anillo de foco se pinta en la etiqueta, porque el input no
  se ve.

El `<legend>` del `<fieldset>` sustituye al `<h3>` que había: es el mismo texto,
y en un fieldset el legend **es** la etiqueta del grupo. Con los dos, quien usa
lector de pantalla lo oiría dos veces.

<a id="p-espera"></a>

### Esperando el pago

```
            ◜◝
           ◟  ◞         rueda de 38 px

    Esperando la confirmación del pago…

    La pasarela confirma por su cuenta. Si
    tarda, tu pedido sigue guardado.

[ Ir a la pasarela y pagar ]   ← solo con pasarela simulada

[ Consultar más tarde      ]
```

La espera **no bloquea**: el pedido ya existe y es consultable. Si el aviso nunca
llega, queda en «pendiente de pago», que es un estado honesto y no un error.

El enlace a la pasarela aparece **solo cuando el checkout vive en este mismo
sitio**, es decir cuando el despliegue tiene
[pasarela simulada](#p-pasarela). Contra una de verdad, un despliegue redirige:
la persona sale del sitio y vuelve. Aquí no se redirige porque salir perdería el
pedido recién creado, así que se abre en otra pestaña y esta se queda
sondeando. La distinción la hace el origen de la URL que devuelve la API, no una
segunda bandera en el frontend que pudiera contradecirla.

**Un rechazo sale de esta pantalla.** Un pago rechazado deja el pedido en
«pendiente de pago», igual que uno que aún no ha confirmado, así que esta
pantalla no puede distinguirlos mirando el pedido: pregunta además por el cobro,
que es quien lo sabe, y solo cuando el pedido no se ha movido.

El resultado es la [pantalla de rechazo](#p-rechazo). Lo que **no** se hace es
sondear el cobro en vez del pedido: hay una ventana en la que el pedido ya está
pagado y el cobro todavía figura pendiente —está puesta así a propósito, para
fallar hacia el cliente— y preguntando primero por el cobro, quien ya tiene su
código seguiría esperando.

<a id="p-rechazo"></a>

### El pago rechazado

```
El pago fue rechazado

●  Tu pedido sigue guardado y no se te
   cobró nada. Podés intentarlo otra vez,
   con el mismo método o con otro.

┌──────────────────────────────────┐
│  1 × Salchipapas      $ 17.300   │
│  ──────────────────────────────  │
│  Total               $ 17.300    │
└──────────────────────────────────┘

[ Intentar el pago otra vez ]

[ Hacer otro pedido         ]
```

Tres cosas que esta pantalla dice y que no son adorno:

- **«no se te cobró nada».** Es la primera pregunta de quien ve un rechazo, y
  no responderla deja a alguien revisando su cuenta en vez de volver a
  intentarlo.
- **«sigue guardado».** El pedido existe y es el mismo: reintentar abre otro
  cobro del pedido que ya está, no uno nuevo. Es también lo que impide que un
  doble toque en «Pagar» cueste dos veces.
- **No dice por qué.** La pasarela no nos lo dice. Un motivo inventado
  —«fondos insuficientes»— sería peor que no darlo.

«Intentar otra vez» devuelve a [Tu pedido](#p-pedido) con los métodos sin
marcar: tras un rechazo, reintentar con la misma tarjeta suele no servir de
nada, así que la elección se vuelve a abrir en vez de repetirse sola.

<a id="p-codigo"></a>

### El código de canje

```
Lo están preparando

●  El establecimiento ya recibió tu pedido.

┌──────────────────────────────────┐
│      TU CÓDIGO DE RECOGIDA       │
│  ╭────────────────────────────╮  │
│  │      K 7 M 2 Q 9           │  │
│  ╰────────────────────────────╯  │
│      ( ● En preparación )        │  ← la palabra del mostrador
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  1 × Pechuga asada    $ 18.000   │
│  2 × Chorizo          $ 14.000   │
│  1 × Gaseosa 400 ml    $ 4.500   │
│  ──────────────────────────────  │
│  Total               $ 36.500    │
└──────────────────────────────────┘

[ Hacer otro pedido ]
```

El billete es el protagonista. Encima, la frase que cuenta lo que el estado
significa para quien pidió; dentro, la pastilla que dice cómo lo llama el
mostrador.

**Esta pantalla se mueve sola.** Es la misma a lo largo de todo el pedido: el
título, la frase y la pastilla cambian cuando el mostrador avanza, sin recargar
y sin tocar nada, hasta que el pedido se entrega o se cancela. Y se repinta
**solo cuando algo cambia**, no en cada vuelta del sondeo, porque reconstruirla
cada cinco segundos cancelaría la selección de quien está copiando su código.

**Y no se pierde.** El pedido y su token viven en `localStorage`, así que
recargar, bloquear el teléfono o volver desde la pasarela vuelven a esta
pantalla y no a la portada. Caduca a las seis horas, y se borra solo cuando el
pedido llega a entregado o cancelado: a partir de ahí el código no le sirve a
nadie, y guardarlo solo serviría para enseñárselo a quien abra la carta después
en ese mismo teléfono.

Pulsar «Hacer otro pedido» con un código todavía sin recoger abre la
[advertencia](#c-advertencia) en vez de tirarlo.

**Debajo va el recibo: qué se compró, no solo cuánto.** Antes esta pantalla
decía únicamente «Total pagado: …», que además mentía en los estados donde no se
pagó nada —un pedido cancelado, o uno cuyo cobro la pasarela todavía no ha
confirmado—. La fila «Total» del resumen da la cifra sin afirmar que haya
cambiado de manos, así que el mismo bloque sirve para los seis estados.

<a id="p-panel"></a>

### Panel del mostrador

```
Mostrador
Los pedidos que tenés que atender.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ Refrescar ]            Última carga: 17:42

┃ #128
┃ 1 × Pechuga asada · 2 × Chorizo · 1 × Gaseosa
┃ Pagado · $ 36.500
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

<a id="p-pasarela"></a>

### La pasarela de pruebas

```
PASARELA DE PRUEBAS
Confirmá tu pago
                                ← sin el filete de tres colores
┌──────────────────────────────────┐
│  Comercio              PideUTB   │
│  Método                  Nequi   │
│  Referencia      pago-4-c49f83   │
│  ──────────────────────────────  │
│  Total               $ 26.000    │
└──────────────────────────────────┘

[ Pagar              ]   ← gris, no azul
[ Rechazar el pago   ]
```

**No es una pantalla de PideUTB.** Representa al sistema que cobra, y por eso
es la única que rompe la identidad: hereda `estilos.css` entero y solo cambia
el acento, de `--azul` a un gris de 11,2:1, y le quita a la cabecera el filete
de tres colores. Vestida de azul, una demostración enseñaría a PideUTB
cobrándose a sí mismo, que es justo lo que no ocurre.

Existe para poder recorrer el flujo completo sin una cuenta de comercio, y solo
aparece donde el despliegue define `PIDEUTB_URL_PASARELA_SIMULADA`.

**Lo que no hace es lo que la justifica.** Pulsar «Pagar» no devuelve el pedido
pagado: avisa a PideUTB y nada más. Quien pagó se entera por su propia consulta
desde la [pantalla de espera](#p-espera), igual que con una pasarela real. Si la
respuesta del botón trajera el código de canje, la demostración enseñaría una
arquitectura distinta de la que
[ADR-0003](adr/0003-estrategia-integracion.md) describe —el sondeo y la
idempotencia dejarían de ejercitarse justo en la pantalla donde se mira—, y por
eso hay una prueba que falla si alguien «simplifica» el simulador en esa
dirección.

Los dos botones van apilados y a ancho completo: «Pagar» y «Rechazar» no deben
quedar al alcance del mismo pulgar.

---

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
| **`theme-color`** | Uno solo, el azul de marca: el sitio no sigue al tema del sistema |
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
| **Un solo tema** | Revisada en claro, que es el único que hay. Si vuelve el oscuro, esta fila vuelve a decir «los dos» |

Los dos últimos se comprueban mirando, no deduciendo. Los dos defectos que esta
guía corrigió en su primera versión —un rótulo partido en dos líneas y una
tarjeta que perdía su forma— solo se vieron abriendo el navegador.

<a id="decisiones"></a>

## Decisiones confirmadas

Seis posturas de esta guía, con su motivo.

#### El cian y el verde son superficie, nunca tinta

Medido: 2,05:1 y 1,53:1 sobre blanco, insuficientes incluso para texto grande.
Sobre tinta oscura, 9,24:1 y 12,40:1. Para letra de esos tonos existen
`--cian-tinta` y `--verde-tinta`.

#### El claro es el único tema

La marca de la universidad es luminosa y la carta se mira al sol. Hubo un oscuro
que seguía al del sistema; se quitó porque **nadie lo elegía y casi nadie lo
revisaba**: la misma página se veía de dos maneras y solo una se miraba con
cuidado.

#### Ninguna fuente desde un CDN

Añade una petición a un tercero, latencia en la red del campus y un dato que sale
del navegador de quien pide. La del sistema cuesta cero y se renderiza bien en
todo.

#### Sin logotipo, por ahora

La marca es el nombre en azul más el filete de tres colores. No hay archivo que
mantener ni versión invertida que aprobar. Cuando la universidad entregue uno,
entra en la cabecera sin ningún otro cambio.

#### Las medidas se toman en 375 px, no se eligen

Cada número de esta guía que afecta a cuánto cabe en una fila sale de medir el
texto real contra el ancho real, no de un valor redondo. Es lo que decidió que
el botón diga `+` y no «Agregar» (111 px frente a 44), que el control de cantidad
baje a su fila por debajo de 520 px (deja 97 px para el nombre y los nombres
miden entre 95 y 165), y que la barra del carrito alinee su contenido con la
columna de 720 px.

La regla práctica: antes de defender una medida, medirla en el navegador a 375 px
con los productos que de verdad hay en la carta.

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
