from pathlib import Path
from PIL import Image, ImageDraw
from rembg import new_session, remove

SOURCE = Path("outputs/images/luma_prueba_01.png")

OUTPUT_DIR = Path("outputs/assets/characters")

OUTPUT_IMAGE = OUTPUT_DIR / "luma_reference_rgba.png"
OUTPUT_PREVIEW = OUTPUT_DIR / "luma_reference_preview.png"
OUTPUT_MASK = OUTPUT_DIR / "luma_reference_mask.png"


def crear_fondo_cuadriculado(tamano):

    fondo = Image.new("RGB", tamano, "white")
    dibujo = ImageDraw.Draw(fondo)

    bloque = 32

    for y in range(0, tamano[1], bloque):
        for x in range(0, tamano[0], bloque):

            if (x // bloque + y // bloque) % 2 == 0:
                dibujo.rectangle(
                    (x, y, x + bloque, y + bloque),
                    fill=(215, 215, 215)
                )

    return fondo


def main():

    if not SOURCE.exists():
        raise FileNotFoundError(
            f"No se encontro la imagen original: {SOURCE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("FIFTHPLOT - SEPARACION DE PERSONAJES")
    print("Imagen original:", SOURCE)

    # Utilizamos U2Net ejecutado en CPU.
    print("\nCargando modelo U2Net...")
    sesion = new_session(
        "u2net",
        providers=["CPUExecutionProvider"]
    )

    imagen = Image.open(SOURCE).convert("RGB")

    print("Eliminando el fondo...")
    resultado = remove(
        imagen,
        session=sesion,
        alpha_matting=False,
        post_process_mask=True
    )

    resultado = resultado.convert("RGBA")

    # Guardamos la imagen con transparencia real.
    resultado.save(OUTPUT_IMAGE)

    # Guardamos la mascara para revisar la segmentacion.
    mascara = resultado.getchannel("A")
    mascara.save(OUTPUT_MASK)

    # Creamos una vista previa con fondo cuadriculado.
    fondo = crear_fondo_cuadriculado(resultado.size).convert("RGBA")

    preview = Image.alpha_composite(
        fondo,
        resultado
    ).convert("RGB")

    preview.save(OUTPUT_PREVIEW)

    # Calculamos cuanto fondo quedo transparente.
    pixeles = list(mascara.getdata())

    transparentes = sum(
        1 for valor in pixeles if valor < 128
    )

    porcentaje = transparentes / len(pixeles) * 100

    print("\nProceso terminado.")
    print("PNG transparente:", OUTPUT_IMAGE)
    print("Vista previa:", OUTPUT_PREVIEW)
    print("Mascara:", OUTPUT_MASK)
    print(f"Area transparente: {porcentaje:.2f}%")

    imagen.close()
    resultado.close()
    mascara.close()
    fondo.close()
    preview.close()

    print("\nPersonaje procesado correctamente.")


if __name__ == "__main__":
    main()
