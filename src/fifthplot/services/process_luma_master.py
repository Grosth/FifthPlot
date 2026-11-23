import json

from pathlib import Path
from PIL import Image, ImageDraw
from rembg import new_session, remove


SOURCE = Path(
    "outputs/images/ip_adapter_test/dreamshaper_with_ip_adapter.png"
)

OUTPUT = Path(
    "outputs/assets/characters/processed_v3"
)

PADDING = 16


def crear_fondo(size):

    fondo = Image.new("RGB", size, (245, 245, 245))
    draw = ImageDraw.Draw(fondo)

    for y in range(0, size[1], 24):
        for x in range(0, size[0], 24):

            if (x // 24 + y // 24) % 2 == 0:
                draw.rectangle(
                    (x, y, x + 24, y + 24),
                    fill=(210, 210, 210)
                )

    return fondo


def main():

    if not SOURCE.exists():
        raise FileNotFoundError(
            f"No se encontro la referencia: {SOURCE}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("FIFTHPLOT - LUMA REFERENCIA MAESTRA")
    print("=" * 50)

    print("Referencia:", SOURCE)
    print("Modelo: U2Net")
    print("Procesamiento: CPU")

    print("\nCargando U2Net...")

    session = new_session(
        "u2net",
        providers=["CPUExecutionProvider"]
    )

    with Image.open(SOURCE) as original:
        original_rgba = original.convert("RGBA")
        rgb = original.convert("RGB")

    print("Eliminando fondo decorativo...")

    resultado = remove(
        rgb,
        session=session,
        alpha_matting=False,
        post_process_mask=True
    ).convert("RGBA")

    # Guardamos la imagen transparente completa.
    ruta_transparente = OUTPUT / "luma_transparent.png"
    resultado.save(ruta_transparente)

    alpha = resultado.getchannel("A")

    ruta_mascara = OUTPUT / "luma_mask.png"
    alpha.save(ruta_mascara)

    # Detectamos los limites del personaje.
    mascara_bbox = alpha.point(
        lambda valor: 255 if valor >= 16 else 0
    )

    bbox = mascara_bbox.getbbox()

    if bbox is None:
        raise RuntimeError("No se detecto la silueta de Luma.")

    izquierda, superior, derecha, inferior = bbox

    izquierda = max(0, izquierda - PADDING)
    superior = max(0, superior - PADDING)

    derecha = min(resultado.width, derecha + PADDING)
    inferior = min(resultado.height, inferior + PADDING)

    recorte = resultado.crop(
        (izquierda, superior, derecha, inferior)
    )

    ruta_recorte = OUTPUT / "luma_cropped.png"
    recorte.save(ruta_recorte)

    # Creamos una vista previa con transparencia visible.
    fondo = crear_fondo(recorte.size).convert("RGBA")

    vista = Image.alpha_composite(
        fondo,
        recorte
    ).convert("RGB")

    ruta_vista = OUTPUT / "luma_preview.png"
    vista.save(ruta_vista)

    histograma = alpha.histogram()

    pixeles = resultado.width * resultado.height

    transparentes = sum(histograma[:16])

    porcentaje = round(
        transparentes / pixeles * 100,
        2
    )

    metadata = {
        "personaje": "Luma",
        "version": "Referencia maestra V3",
        "modelo_visual": "DreamShaper 8",
        "adaptador": "IP-Adapter Plus SD15",
        "origen": str(SOURCE),
        "segmentacion": "U2Net",
        "dimensiones_originales": list(resultado.size),
        "dimensiones_recortadas": list(recorte.size),
        "bbox": [
            izquierda,
            superior,
            derecha,
            inferior
        ],
        "porcentaje_transparente": porcentaje,
        "imagen_transparente": str(ruta_transparente),
        "mascara": str(ruta_mascara),
        "recorte": str(ruta_recorte),
        "vista_previa": str(ruta_vista)
    }

    with open(
        OUTPUT / "luma_metadata.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            metadata,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("\nPROCESAMIENTO COMPLETADO")
    print("Imagen:", ruta_transparente)
    print("Mascara:", ruta_mascara)
    print("Recorte:", ruta_recorte)
    print("Vista previa:", ruta_vista)
    print("Transparencia:", porcentaje, "%")
    print("Dimensiones:", recorte.size)

    original_rgba.close()
    rgb.close()
    resultado.close()
    alpha.close()
    mascara_bbox.close()
    recorte.close()
    fondo.close()
    vista.close()

    print("\nReferencia maestra preparada.")


if __name__ == "__main__":
    main()
