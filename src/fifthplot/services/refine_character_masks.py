import json
import numpy as np
import cv2

from pathlib import Path
from PIL import Image, ImageDraw

SOURCE = Path("outputs/assets/characters/processed_v1")
OUTPUT = Path("outputs/assets/characters/processed_v2")

NAMES = ["luma", "guardian", "shadow_serpent"]
PADDING = 16


def create_checker(size):

    bg = Image.new("RGB", size, (245, 245, 245))
    draw = ImageDraw.Draw(bg)

    for y in range(0, size[1], 24):
        for x in range(0, size[0], 24):
            if (x // 24 + y // 24) % 2 == 0:
                draw.rectangle(
                    (x, y, x + 24, y + 24),
                    fill=(210, 210, 210)
                )

    return bg


def process(name):

    print("\nProcesando:", name)

    source = SOURCE / f"{name}_transparent.png"

    if not source.exists():
        raise FileNotFoundError(source)

    with Image.open(source) as im:
        original = im.convert("RGBA")

    rgba = original.copy()
    alpha = np.array(rgba.getchannel("A"))

    binary = (alpha >= 128).astype(np.uint8)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary,
        connectivity=8
    )

    areas = sorted(
        stats[1:, cv2.CC_STAT_AREA].tolist(),
        reverse=True
    )

    removed = []

    if name == "shadow_serpent":

        largest = int(
            np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1
        )

        # Conservamos exclusivamente el componente principal.
        keep = (labels == largest)

        cleaned_alpha = np.where(
            keep,
            alpha,
            0
        ).astype(np.uint8)

        removed = [
            int(area)
            for index, area in enumerate(areas)
            if index != 0
        ]

        print("Componentes originales:", count - 1)
        print("Area de componentes eliminados:", removed)

    else:

        cleaned_alpha = alpha.copy()

    rgba.putalpha(
        Image.fromarray(cleaned_alpha, mode="L")
    )

    # Guardamos la transparencia completa.
    OUTPUT.mkdir(parents=True, exist_ok=True)

    transparent_path = OUTPUT / f"{name}_transparent.png"
    rgba.save(transparent_path)

    mask = Image.fromarray(cleaned_alpha, mode="L")
    mask.save(OUTPUT / f"{name}_mask.png")

    # Detectamos los limites y conservamos un margen.
    bbox = mask.point(
        lambda v: 255 if v >= 128 else 0
    ).getbbox()

    if bbox is None:
        raise RuntimeError(f"Mascarilla vacia: {name}")

    left, top, right, bottom = bbox

    left = max(0, left - PADDING)
    top = max(0, top - PADDING)
    right = min(rgba.width, right + PADDING)
    bottom = min(rgba.height, bottom + PADDING)

    cropped = rgba.crop((left, top, right, bottom))

    cropped.save(OUTPUT / f"{name}_cropped.png")

    # Creamos la vista previa.
    checker = create_checker(cropped.size).convert("RGBA")

    preview = Image.alpha_composite(
        checker,
        cropped
    ).convert("RGB")

    preview.save(OUTPUT / f"{name}_preview.png")

    metadata_path = SOURCE / f"{name}_metadata.json"

    metadata = {}

    if metadata_path.exists():
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )

    metadata.update({
        "version": "processed_v2",
        "limpieza_componentes": removed,
        "bbox_final": [left, top, right, bottom],
        "imagen_transparente": str(transparent_path),
        "mascara": str(OUTPUT / f"{name}_mask.png"),
        "imagen_recortada": str(OUTPUT / f"{name}_cropped.png"),
        "vista_previa": str(OUTPUT / f"{name}_preview.png")
    })

    with open(
        OUTPUT / f"{name}_metadata.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)

    print("Imagen refinada:", transparent_path)
    print("Dimensiones:", cropped.size)
    print("Procesamiento terminado.")

    original.close()
    rgba.close()
    mask.close()
    cropped.close()
    checker.close()
    preview.close()


def contact_sheet():

    width = 360
    height = 430

    sheet = Image.new(
        "RGB",
        (width * 3, height),
        "white"
    )

    draw = ImageDraw.Draw(sheet)

    for index, name in enumerate(NAMES):

        path = OUTPUT / f"{name}_preview.png"

        with Image.open(path) as im:
            character = im.convert("RGB")

        character.thumbnail((320, 350))

        x = index * width
        y = 55

        draw.text(
            (x + 15, 20),
            name.upper(),
            fill="black"
        )

        sheet.paste(
            character,
            (
                x + (width - character.width) // 2,
                y + (350 - character.height) // 2
            )
        )

        character.close()

    sheet.save(OUTPUT / "characters_contact_sheet.png")
    sheet.close()


def main():

    print("=" * 50)
    print("FIFTHPLOT - REFINAMIENTO DE MASCARAS")
    print("=" * 50)

    for name in NAMES:
        process(name)

    contact_sheet()

    manifest = {
        "proyecto": "FifthPlot",
        "version": "processed_v2",
        "personajes": NAMES,
        "metodo": "Limpieza de componentes desconectados"
    }

    with open(OUTPUT / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)

    print("\nBIBLIOTECA REFINADA CORRECTAMENTE")
    print("Personajes:", len(NAMES), "de 3")
    print("Resultados:", OUTPUT)


if __name__ == "__main__":
    main()
