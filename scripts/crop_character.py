from pathlib import Path
from PIL import Image, ImageDraw

CARPETA = Path("outputs/assets/characters")

ORIGINAL = CARPETA / "luma_reference_rgba.png"

RECORTADA = CARPETA / "luma_reference_cropped.png"
VISTA = CARPETA / "luma_reference_cropped_preview.png"

def main():

    imagen = Image.open(ORIGINAL).convert("RGBA")

    # Buscamos los limites de la silueta.
    mascara = imagen.getchannel("A")
    caja = mascara.getbbox()

    if caja is None:
        raise ValueError("No se encontro ningun personaje.")

    # Dejamos un pequeÃ±o margen alrededor.
    margen = 14

    izquierda = max(0, caja[0] - margen)
    superior = max(0, caja[1] - margen)
    derecha = min(imagen.width, caja[2] + margen)
    inferior = min(imagen.height, caja[3] + margen)

    recorte = imagen.crop(
        (izquierda, superior, derecha, inferior)
    )

    recorte.save(RECORTADA)

    # Creamos una vista ampliada sobre cuadricula.
    escala = min(
        440 / recorte.width,
        440 / recorte.height
    )

    ancho = int(recorte.width * escala)
    alto = int(recorte.height * escala)

    personaje = recorte.resize(
        (ancho, alto),
        Image.Resampling.LANCZOS
    )

    fondo = Image.new("RGBA", (512, 512), "white")
    dibujo = ImageDraw.Draw(fondo)

    bloque = 32

    for y in range(0, 512, bloque):
        for x in range(0, 512, bloque):
            if (x // bloque + y // bloque) % 2 == 0:
                dibujo.rectangle(
                    (x, y, x + bloque, y + bloque),
                    fill=(215, 215, 215, 255)
                )

    x = (512 - ancho) // 2
    y = (512 - alto) // 2

    fondo.alpha_composite(personaje, (x, y))

    fondo.convert("RGB").save(VISTA)

    print("Recorte completado.")
    print("Dimensiones originales:", imagen.size)
    print("Dimensiones del personaje:", recorte.size)
    print("Archivo:", RECORTADA)
    print("Vista previa:", VISTA)

    imagen.close()
    mascara.close()
    recorte.close()
    personaje.close()
    fondo.close()

if __name__ == "__main__":
    main()
