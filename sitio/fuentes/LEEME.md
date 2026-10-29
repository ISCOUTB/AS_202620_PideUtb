# Las dos tipografías

| Archivo | Familia | Versión | Licencia |
|---|---|---|---|
| `fraunces-latin.woff2` | [Fraunces](https://fonts.google.com/specimen/Fraunces) | v38 | SIL Open Font License 1.1 |
| `inter-latin.woff2` | [Inter](https://fonts.google.com/specimen/Inter) | v20 | SIL Open Font License 1.1 |

Las dos son **variables**: un solo archivo cubre todos los pesos, así que pedir
el 600 y el 700 no cuesta dos descargas. Y están recortadas al subconjunto
`latin`, que incluye `ñ`, las vocales acentuadas y la diéresis — el español
entero. 115 KB entre las dos.

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
curl "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400..700&display=swap" \
  -A "Mozilla/5.0" -o /tmp/gf.css
# y de ahí, las URL de los bloques marcados `/* latin */`
```

La licencia OFL permite redistribuir los archivos, incluso modificados, siempre
que no se vendan por separado y que se conserve el aviso de licencia. El texto
completo está en <https://openfontlicense.org>.
