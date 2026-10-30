# Las dos tipografías

| Archivo | Familia | Versión | Pesos | Peso | Licencia |
|---|---|---|---|---|---|
| `young-serif-latin.woff2` | [Young Serif](https://fonts.google.com/specimen/Young+Serif) | v2 | 400, único | 27,0 KB | SIL Open Font License 1.1 |
| `hanken-grotesk-latin.woff2` | [Hanken Grotesk](https://fonts.google.com/specimen/Hanken+Grotesk) | v12 | 300–900, variable | 34,7 KB | SIL Open Font License 1.1 |

Las dos están recortadas al subconjunto `latin`, que incluye `ñ`, las vocales
acentuadas y la diéresis — el español entero. **61,7 KB entre las dos.**

## Por qué estas dos, y qué sustituyeron

Antes eran Fraunces y Inter, 115,6 KB. Las dos salían marcadas como caras que
de tanto usarse han dejado de distinguir a nada, y el cambio costaba la mitad
del peso: en la red de un auditorio con doscientos teléfonos abriendo a la vez,
54 KB menos no es una cifra decorativa.

**Hanken Grotesk** es variable, así que un archivo cubre de 300 a 900 y pedir
el 500 y el 700 no son dos descargas. Trae además las cifras de ancho fijo de
serie: se comprobó midiendo el ancho de `111111` contra el de `000000`, que es
lo que decide si un total salta al pasar de 9 a 10.

**Young Serif tiene un solo peso, y es la decisión que hay que conocer.** Es
cara de titular, y su 400 pesa ya más que el 600 de la serif que sustituyó, así
que la jerarquía la llevan el tamaño y el aire. Lo que **no** se puede hacer es
pedirle un 600 o un 700: el navegador no se queda en el 400, inventa el grosor
engrosando el contorno. Medido en Chrome a 72 px, el ancho no se mueve y la
tinta sube un 31 %, y pedir 900 da la misma tinta que 700 porque la
falsificación se satura.

Eso no falla, no avisa y no sale en ninguna consola: solo se ve peor. Por eso
lo vigila `test_ningun_titulo_pide_un_peso_que_la_cara_no_tiene`, que lee los
`@font-face` de la hoja, mira qué pesos declara cada familia y comprueba que
ninguna regla pida uno fuera de ese rango.

## Por qué están acá y no se piden a Google

Porque el 3 de noviembre el público abre el sitio a la vez desde la red de un
auditorio. Una petición menos a `fonts.gstatic.com` es un punto menos donde la
demostración se queda sin tipografía delante de todo el mundo, y además el
navegador no tiene que resolver otro dominio antes de pintar.

El coste de hacerlo así es que una versión nueva de la fuente no llega sola.
Es el coste correcto: que una tipografía cambie sin que nadie lo decida es
exactamente lo que no se quiere la víspera de una charla.

`font-display: swap` en `estilos.css` hace que el texto aparezca de inmediato
con la fuente del sistema y cambie cuando la nuestra llegue. En una demostración
en vivo, texto feo al instante gana a texto bonito dentro de dos segundos.

## Cómo se volverían a bajar

```bash
curl "https://fonts.googleapis.com/css2?family=Young+Serif&family=Hanken+Grotesk:wght@300..900&display=swap" \
  -A "Mozilla/5.0" -o gf.css
# y de ahí, las URL de los bloques marcados `/* latin */`
```

Hace falta el `-A`: sin un agente de navegador, Google devuelve `ttf` en vez de
`woff2`, que pesa el triple.

La licencia OFL permite redistribuir los archivos, incluso modificados, siempre
que no se vendan por separado y que se conserve el aviso de licencia. El texto
completo está en <https://openfontlicense.org>.
