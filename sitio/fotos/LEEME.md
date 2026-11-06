# Las fotos del sitio

| Archivo | Tamaño | Peso | Dónde se usa |
|---|---|---|---|
| `portada-movil.webp` | 640 × 514 | 34 KB | Fondo de la portada, por defecto |
| `portada.webp` | 1024 × 823 | 61 KB | Lo mismo, a partir de 768 px |
| `platos/` (25 archivos) | 144 × 144 | 71 KB | Las miniaturas del catálogo |

Las dos salen del **mismo original** y no son recortes distintos: la pequeña es
la grande reescalada. El teléfono se lleva la pequeña, y eso importa más de lo
que parece — el 3 de noviembre el sitio se abre a la vez desde la red de un
auditorio.

## Qué se le hizo al original, y por qué

El original llega casi cuadrado (1024 × 1004) y oscuro: media 125/69/38 sobre
255. La portada es una franja ancha y clara, así que hacen falta tres cosas.

| Paso | Valor | Por qué |
|---|---|---|
| Recorte vertical | de 17 % a 99 % de la altura | Arriba sobra humo y fondo negro; abajo, el borde de la parrilla. Recortando aquí la composición se **decide** —las carnes al centro, las llamas a la izquierda— en vez de dejársela a `background-size: cover`, que recorta por geometría y no por lo que hay dentro |
| Gamma | 1,26 | Levanta sombras y medios tonos dejando los altos en paz. Subir el brillo entero habría quemado las llamas, que es lo único que ya estaba bien expuesto |
| Contraste | ×1,06 | Compensa el aplanado que deja la gamma |
| Saturación | ×1,08 | Lo mismo, en color |
| WebP | calidad 74, `method=6` | 61 KB para 1024 px de fotografía |

Después del recorte y la luz, la media queda en 164/95/50: sigue siendo una foto
de brasas, ya no es una foto a oscuras.

Se reproduce con Pillow en cuatro líneas, y **a propósito no hay un guion en el
repositorio**: Pillow no está en `requirements.in` —la aplicación no procesa
imágenes— y meterlo para un retoque que se hace una vez le costaría un paquete a
la imagen de producción por nada.

```python
from PIL import Image, ImageEnhance

curva = [round(255 * (i / 255) ** (1 / 1.26)) for i in range(256)] * 3
foto = Image.open(ORIGEN).convert("RGB")
foto = foto.crop((0, int(foto.height * 0.17), foto.width, int(foto.height * 0.99)))
foto = ImageEnhance.Color(ImageEnhance.Contrast(foto.point(curva)).enhance(1.06)).enhance(1.08)

for ancho in (1024, 640):
    copia = foto.resize((ancho, round(foto.height * ancho / foto.width)), Image.LANCZOS)
    copia.save(..., "webp", quality=74, method=6)
```

## Reemplazar una foto es cambiarle el nombre

La referencia vive dentro de `estilos.css`, que lleva su huella en la URL, así
que **cambiar la hoja cambia la dirección desde la que se pide el fondo**. Lo que
eso no cubre es sustituir el archivo dejándole el mismo nombre: ahí Cloudflare
seguiría sirviendo la vieja hasta cuatro horas, que es el problema que el sellado
del `Dockerfile` existe para evitar.

Es la misma regla que las tipografías: un archivo nuevo es un nombre nuevo. Y es
la clase de cosa que no se quiere descubrir con el público delante.

## Las miniaturas del catálogo

Viven en `platos/` y las pide la **base de datos**, no la hoja de estilos:
`menu_items.imagen` guarda la ruta relativa y `app.js` la mete en un `<img>`.
Son 25 para 47 productos; los 22 que no tienen foto dibujan el marcador con la
inicial, que está diseñado para eso.

### Por qué 144 × 144

El hueco mide **72 × 72** con `object-fit: cover`, así que 144 es exactamente
el doble: la densidad de la mayoría de los teléfonos. Un teléfono de densidad 3
las escala un 50 %, y a ese tamaño físico no se distingue.

Lo que sí se nota es el otro lado de la cuenta. A 216 px pesarían 128 KB en vez
de 71, y la categoría más grande —Asados, 12 productos— pediría 12 de ellas a la
vez. En la red de un auditorio con doscientos teléfonos, esos 57 KB valen más
que una nitidez que nadie va a ver. Van con `loading="lazy"`, así que solo se
pide la categoría que se está mirando.

### Qué se les hizo a los originales

Llegaron dentro de un documento de la cafetería, 22 fotos para 25 productos.
Tres traen **dos productos en la misma foto** —suero y salsa de tomate,
vinagreta y chimichurri, papa francesa y papa cocida—, y se partieron: una
miniatura donde la mitad es otro producto no es la foto de ese producto. El
corte no va por la mitad exacta sino por la columna con menos contenido del
tercio central, que es donde está el hueco de verdad; en dos de las tres es un
corte limpio de cero píxeles.

Además hubo que quitarles dos cosas que traían de fábrica:

| Qué | Dónde | Cómo se detecta |
|---|---|---|
| Reglas de la tabla del documento | 12 fotos | Una tira oscura que **arranca en el borde** y cae de golpe. No vale el grosor —las hay de 2 px y de 8— ni exigir que lo siguiente sea blanco: en las butifarras lo que sigue es el plato |
| El damero de transparencia, quemado en el JPEG | 3 fotos | Alguien guardó un PNG con alfa como JPEG. El tono gris cambia en cada una (227, 202 y 186), así que se mide la **forma**: un damero empareja ese gris con el blanco a partes casi iguales y cubre el marco de la foto |

Ese segundo detector se mide en el marco y no en el centro a propósito. Con un
umbral de tono a secas, las sombras grises del bol de la papa francesa se
habrían ido a blanco con él.

El guion que las procesa **no está en el repositorio**, por el mismo motivo que
el de la portada: Pillow no está en `requirements.in` porque la aplicación no
procesa imágenes, y meterlo por un retoque que se hace una vez le costaría un
paquete a la imagen de producción por nada. Lo que sí queda escrito es el
criterio, que es lo que haría falta para repetirlo.

### Reemplazar una, aquí, es pasar por una migración

Vale la regla de la portada y las tipografías —un archivo nuevo es un nombre
nuevo—, y aquí es más fácil de cumplir porque el nombre vive en
`menu_items.imagen`: cambiarlo obliga a escribir una migración, que es
exactamente donde se quiere que pase. Dejarle el mismo nombre a una foto nueva
dejaría a Cloudflare sirviendo la vieja durante cuatro horas.

## Qué comprueba una prueba

`backend/tests/test_escenarios_de_calidad.py` comprueba cuatro cosas, porque las
cuatro fallan en silencio:

- que cada imagen que `estilos.css` pide **exista** en esta carpeta;
- que el `Dockerfile` lleve un `COPY` de esta carpeta;
- que cada foto que una migración le asigna a un producto **exista** también;
- que cada una de esas filas apunte a un producto que alguna migración inserta
  de verdad.

Las dos primeras protegen la portada; un fondo que no carga no da error de
consola, no rompe la página y no se nota hasta que alguien mira la pantalla.

Las dos últimas protegen el catálogo, y la cuarta merece explicación: un
`UPDATE ... WHERE id = 105` sobre un identificador que nadie insertó es SQL
válido que actualiza **cero filas**. No falla, no avisa, y el archivo sí está
en esta carpeta —así que la tercera prueba pasa—. Lo único que se ve es un
plato sin foto entre otros que sí la tienen.

El `alt` de estas imágenes va vacío a propósito, porque el nombre del producto
está al lado: son decorativas. La consecuencia es que una ruta rota no deja
ni un texto alternativo a la vista, solo un hueco.
