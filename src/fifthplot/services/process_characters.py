import json
import gc

from pathlib import Path

from PIL import Image, ImageDraw
from rembg import new_session, remove


BASE = Path("outputs/assets/characters")

OUTPUT = BASE / "processed_v1"

INPUTS = {
    "luma": [
        BASE / "luma_reference_cropped.png"
    ],

    "guardian": [
        BASE / "dreamshaper_v1" / "guardian.png",
        BASE / "guardian.png"
    ],

    "shadow_serpent": [
        BASE / "dreamshaper_v2" / "shadow_serpent_v2.png",
        BASE / "shadow_serpent_v2.png"
    ]
}

PADDING = 16
MASK_THRESHOLD = 128


def buscar_imagen(candidatos):

    for ruta in candidatos:
        if ruta.is_file():
            return ruta

    raise FileNotFoundError(
        "No se encontro ninguna de estas imagenes:\n"
        + "\n".join(str(ruta) for ruta in candidatos)
    )


def crear_fondo(tamano):

    fondo = Image.new(
        "RGB",
        tamano,
        (245, 245, 245)
    )

    dibujo = ImageDraw.Draw(fondo)

    bloque = 24

    for y in range(0, tamano[1], bloque):
        for x in range(0, tamano[0], bloque):

            if (x // bloque + y // bloque) % 2 == 0:

                dibujo.rectangle(
                    (
                        x,
                        y,
                        x + bloque,
                        y + bloque
                    ),
                    fill=(210, 210, 210)
                )

    return fondo


def quitar_fondo(imagen, sesion):

    rgb = imagen.convert("RGB")

    resultado = remove(
        rgb,
        session=sesion,
        alpha_matting=False,
        post_process_mask=True
    )

    rgb.close()

    return resultado.convert("RGBA")


def guardar_personaje(nombre, origen, sesion=None):

    print("\n" + "-" * 45)
    print("PROCESANDO:", nombre)

    with Image.open(origen) as archivo:
        original = archivo.convert("RGBA")

    tamano_original = original.size

    # Luma ya tiene el fondo transparente.
    if nombre == "luma":

        alpha = original.getchannel("A")

        if alpha.getextrema()[0] < 255:

            resultado = original.copy()
            metodo = "Transparencia original conservada"

        else:

            resultado = quitar_fondo(original, sesion)
            metodo = "U2Net"

    else:

        resultado = quitar_fondo(original, sesion)
        metodo = "U2Net CPU"

    # Guardamos el personaje completo con transparencia.
    ruta_rgba = OUTPUT / f"{nombre}_transparent.png"

    resultado.save(ruta_rgba)

    # Extraemos la mascara.
    mascara = resultado.getchannel("A")

    ruta_mascara = OUTPUT / f"{nombre}_mask.png"

    mascara.save(ruta_mascara)

    # Buscamos los limites de la silueta.
    mascara_binaria = mascara.point(
        lambda valor: (
            255 if valor >= MASK_THRESHOLD else 0
        )
    )

    bbox = mascara_binaria.getbbox()

    if bbox is None:
        raise RuntimeError(
            f"No se detecto el personaje: {nombre}"
        )

    izquierda, superior, derecha, inferior = bbox

    # Agregamos un pequeño margen para no cortar detalles.
    izquierda = max(0, izquierda - PADDING)
    superior = max(0, superior - PADDING)

    derecha = min(
        resultado.width,
        derecha + PADDING
    )

    inferior = min(
        resultado.height,
        inferior + PADDING
    )

    recorte = resultado.crop(
        (izquierda, superior, derecha, inferior)
    )

    ruta_recorte = OUTPUT / f"{nombre}_cropped.png"

    recorte.save(ruta_recorte)

    # Vista previa con fondo cuadriculado.
    fondo = crear_fondo(recorte.size).convert("RGBA")

    vista = Image.alpha_composite(
        fondo,
        recorte
    ).convert("RGB")

    ruta_vista = OUTPUT / f"{nombre}_preview.png"

    vista.save(ruta_vista)

    # Estadisticas de la segmentacion.
    pixeles = list(mascara.getdata())

    total = len(pixeles)

    transparentes = sum(
        1 for valor in pixeles
        if valor < MASK_THRESHOLD
    )

    porcentaje = round(
        transparentes / total * 100,
        2
    )

    metadata = {
        "personaje": nombre,
        "origen": str(origen),
        "metodo": metodo,
        "dimensiones_originales": list(tamano_original),
        "dimensiones_recortadas": list(recorte.size),
        "bbox": [
            izquierda,
            superior,
            derecha,
            inferior
        ],
        "margen": PADDING,
        "porcentaje_transparente": porcentaje,
        "mascara": str(ruta_mascara),
        "imagen_transparente": str(ruta_rgba),
        "imagen_recortada": str(ruta_recorte),
        "vista_previa": str(ruta_vista)
    }

    ruta_json = OUTPUT / f"{nombre}_metadata.json"

    with open(
        ruta_json,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            metadata,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("Origen:", origen)
    print("Metodo:", metodo)
    print("Transparencia:", porcentaje, "%")
    print("Dimensiones originales:", tamano_original)
    print("Dimensiones recortadas:", recorte.size)
    print("PNG transparente:", ruta_rgba)
    print("Mascara:", ruta_mascara)
    print("Vista previa:", ruta_vista)

    if porcentaje < 15:
        print("ADVERTENCIA: poca area transparente.")

    elif porcentaje > 98:
        print("ADVERTENCIA: revisar posible perdida del personaje.")

    # Cerramos los recursos.
    original.close()
    resultado.close()
    mascara.close()
    mascara_binaria.close()
    recorte.close()
    fondo.close()
    vista.close()

    return metadata


def crear_hoja_contacto():

    nombres = [
        "luma",
        "guardian",
        "shadow_serpent"
    ]

    ancho = 350
    alto = 390

    lienzo = Image.new(
        "RGB",
        (ancho * 3, alto),
        "white"
    )

    dibujo = ImageDraw.Draw(lienzo)

    for indice, nombre in enumerate(nombres):

        ruta = OUTPUT / f"{nombre}_preview.png"

        with Image.open(ruta) as archivo:
            imagen = archivo.convert("RGB")

        imagen.thumbnail((320, 320))

        x = indice * ancho
        y = 45

        dibujo.text(
            (x + 15, 15),
            nombre.upper(),
            fill="black"
        )

        posicion = (
            x + (ancho - imagen.width) // 2,
            y + (320 - imagen.height) // 2
        )

        lienzo.paste(imagen, posicion)

        imagen.close()

    destino = OUTPUT / "characters_contact_sheet.png"

    lienzo.save(destino)
    lienzo.close()

    print("\nHoja de contacto guardada:", destino)


def main():

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("FIFTHPLOT - BIBLIOTECA DE PERSONAJES")
    print("=" * 55)

    # Primero verificamos que todas las imagenes existan.
    rutas = {
        nombre: buscar_imagen(candidatos)
        for nombre, candidatos in INPUTS.items()
    }

    for nombre, ruta in rutas.items():
        print(f"{nombre}: {ruta}")

    # U2Net se carga una sola vez para los dos personajes.
    print("\nCargando U2Net...")

    sesion = new_session(
        "u2net",
        providers=["CPUExecutionProvider"]
    )

    resultados = []

    for nombre, ruta in rutas.items():

        resultado = guardar_personaje(
            nombre,
            ruta,
            sesion
        )

        resultados.append(resultado)

        gc.collect()

    crear_hoja_contacto()

    manifiesto = {
        "proyecto": "FifthPlot",
        "procesador": "U2Net",
        "personajes": resultados
    }

    with open(
        OUTPUT / "manifest.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            manifiesto,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("\n" + "=" * 55)
    print("BIBLIOTECA DE PERSONAJES PROCESADA")
    print("Personajes: 3 de 3")
    print("Resultados:", OUTPUT)
    print("=" * 55)


if __name__ == "__main__":
    main()
