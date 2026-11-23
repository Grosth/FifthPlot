import gc
import json
import time
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from transformers import CLIPTokenizer

from fifthplot.generators import ip_adapter_test as ip_test


# Configuracion general
MODEL_DIR = Path("models/stable-diffusion-v1-5")
TOKENIZER_DIR = MODEL_DIR / "tokenizer"

REFERENCE = Path("outputs/images/luma_prueba_01.png")
ORIGINAL_DIR = Path("outputs/images/final")
OUTPUT_DIR = Path("outputs/images/revised_v2")

SIZE = 512
STEPS = 20
GUIDANCE = 7.0
IP_SCALE = 0.35

NEGATIVE = (
    "two foxes, multiple foxes, duplicate fox, second fox, "
    "extra fox, cropped, hidden tail, extra limbs, extra ears, "
    "blurry, text, watermark, photorealistic, 3d render."
)

# Estilo y apariencia que deben conservarse.
STYLE = (
    "Watercolor children's storybook, soft gouache "
    "brushstrokes, teal forest, warm colors."
)

LUMA = (
    "Luma, small red-orange fox, golden eyes, "
    "tiny nose, fluffy fur, curled comet tail."
)

# Descripciones especificas para cada escena.
ESCENAS = {
    3: (
        "Tall mirrors reflect a white-haired guardian "
        "and a red-eyed shadow serpent."
    ),
    4: (
        "Luma faces a coiled black serpent with glowing "
        "red eyes and a sword-shaped tail."
    ),
    5: (
        "Stars return as the defeated shadow serpent "
        "dissolves into glowing light."
    )
}


def comprobar_archivos():

    if not REFERENCE.exists():
        raise FileNotFoundError(
            "No se encontro la referencia de Luma."
        )

    for numero in ESCENAS:
        original = ORIGINAL_DIR / f"scene_{numero:02d}.png"

        if not original.exists():
            raise FileNotFoundError(
                f"No se encontro la imagen original: {original}"
            )

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_DIR),
        local_files_only=True
    )

    print("\nComprobacion de prompts:")

    for numero, descripcion in ESCENAS.items():

        prompt = f"{STYLE} {LUMA} Scene: {descripcion}"

        tokens = len(
            tokenizer(prompt, truncation=False)["input_ids"]
        )

        print(f"Escena {numero}: {tokens}/77 tokens")

        if tokens > 70:
            raise ValueError(
                f"El prompt de la escena {numero} "
                "necesita reducirse."
            )

    tokens_negativos = len(
        tokenizer(NEGATIVE, truncation=False)["input_ids"]
    )

    print(f"Prompt negativo: {tokens_negativos}/77 tokens")

    if tokens_negativos > 77:
        raise ValueError("El prompt negativo supera el limite.")

    return tokenizer


def generar_escenas():

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto la GPU.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = comprobar_archivos()

    print("\nFIFTHPLOT - CORRECCION DE ILUSTRACIONES")
    print("Escenas: 3, 4 y 5")
    print("Modelo: Stable Diffusion 1.5")
    print("Adaptador: IP-Adapter Plus SD15")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Utilizamos la misma referencia del experimento B2.
    ip_test.REFERENCE = REFERENCE
    ip_test.ADAPTER_SCALE = IP_SCALE

    print("\nCargando modelos...")

    pipe = ip_test.cargar_pipeline(usando_referencia=True)

    referencia = Image.open(REFERENCE).convert("RGB")

    resultados = []

    for numero, descripcion in ESCENAS.items():

        print("\n" + "-" * 45)
        print(f"GENERANDO ESCENA {numero}/5")

        prompt = f"{STYLE} {LUMA} Scene: {descripcion}"

        semilla = 4200 + numero

        generador = torch.Generator(
            device="cpu"
        ).manual_seed(semilla)

        torch.cuda.reset_peak_memory_stats()

        inicio = time.perf_counter()

        resultado = pipe(
            prompt=prompt,
            negative_prompt=NEGATIVE,
            ip_adapter_image=referencia,
            height=SIZE,
            width=SIZE,
            num_inference_steps=STEPS,
            guidance_scale=GUIDANCE,
            generator=generador
        )

        tiempo = time.perf_counter() - inicio

        imagen = resultado.images[0]

        ruta_imagen = OUTPUT_DIR / f"scene_{numero:02d}_revised.png"

        imagen.save(ruta_imagen)

        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        )

        datos = {
            "escena": numero,
            "modelo": "Stable Diffusion 1.5",
            "adaptador": "IP-Adapter Plus SD15",
            "referencia": str(REFERENCE),
            "adapter_scale": IP_SCALE,
            "semilla": semilla,
            "resolucion": f"{SIZE}x{SIZE}",
            "pasos": STEPS,
            "guidance_scale": GUIDANCE,
            "precision": "FP16",
            "tiempo_segundos": round(tiempo, 2),
            "memoria_gpu_pico_gb": memoria,
            "prompt": prompt,
            "negative_prompt": NEGATIVE,
            "descripcion": descripcion,
            "imagen": str(ruta_imagen)
        }

        ruta_json = OUTPUT_DIR / f"scene_{numero:02d}_revised.json"

        with open(ruta_json, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=4)

        resultados.append(datos)

        print(f"Imagen guardada: {ruta_imagen}")
        print(f"Tiempo: {tiempo:.2f} segundos")
        print(f"VRAM pico: {memoria} GB")

        del resultado
        del imagen

        gc.collect()
        torch.cuda.empty_cache()

    referencia.close()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    # Guardamos los resultados de esta revision.
    resumen = {
        "experimento": "Revision narrativa de escenas",
        "modelo": "Stable Diffusion 1.5",
        "referencia": str(REFERENCE),
        "estrategia": "Prompt + IP-Adapter",
        "adapter_scale": IP_SCALE,
        "escenas_corregidas": resultados
    }

    with open(
        OUTPUT_DIR / "manifest_revised.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(resumen, archivo, ensure_ascii=False, indent=4)

    print("\nTres escenas corregidas correctamente.")


def crear_comparacion():

    lienzo = Image.new("RGB", (1040, 1100), "white")
    dibujo = ImageDraw.Draw(lienzo)

    for indice, numero in enumerate([3, 4, 5]):

        original = Image.open(
            ORIGINAL_DIR / f"scene_{numero:02d}.png"
        ).convert("RGB")

        revisada = Image.open(
            OUTPUT_DIR / f"scene_{numero:02d}_revised.png"
        ).convert("RGB")

        y = 35 + indice * 350

        dibujo.text((20, y), f"ESCENA {numero} - ORIGINAL", fill="black")
        dibujo.text((540, y), f"ESCENA {numero} - REVISADA", fill="black")

        lienzo.paste(
            original.resize((480, 320)),
            (20, y + 25)
        )

        lienzo.paste(
            revisada.resize((480, 320)),
            (540, y + 25)
        )

        original.close()
        revisada.close()

    ruta = OUTPUT_DIR / "comparacion_original_revisada.png"

    lienzo.save(ruta)
    lienzo.close()

    print(f"\nComparacion guardada: {ruta}")


def main():

    generar_escenas()
    crear_comparacion()

    print("\nPROCESO FINALIZADO")
    print("Escenas corregidas: 3 de 5")
    print(f"Resultados: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
