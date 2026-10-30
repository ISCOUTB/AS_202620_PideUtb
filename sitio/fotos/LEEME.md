# Las fotos del sitio

| Archivo | Tamaño | Peso | Dónde se usa |
|---|---|---|---|
| `portada-movil.webp` | 640 × 514 | 34 KB | Fondo de la portada, por defecto |
| `portada.webp` | 1024 × 823 | 61 KB | Lo mismo, a partir de 768 px |

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

## Qué comprueba una prueba

`backend/tests/test_escenarios_de_calidad.py` comprueba dos cosas, porque las dos
fallan en silencio:

- que cada imagen que `estilos.css` pide **exista** en esta carpeta;
- que el `Dockerfile` lleve un `COPY` de esta carpeta.

Un fondo que no carga no da error de consola, no rompe la página y no se nota
hasta que alguien mira la pantalla.
