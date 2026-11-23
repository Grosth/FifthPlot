import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
import json
import time

from pathlib import Path
from PIL import Image, ImageFilter

import torch
from diffusers import DiffusionPipeline


MODEL = Path("models/dreamshaper-8")

LUMA = Path(
    "outputs/assets/characters/processed_v2/luma_transparent.png"
)

OUTPUT = Path("outputs/images/composition_test")

PROMPT = (
    "An enchanted ancient forest at night, tall dark trees, "
    "teal blue green foliage, winding forest path, misty "
    "atmosphere, empty foreground with visible forest floor, "
    "dark starless sky, subtle warm amber moonlight, "
    "beautiful watercolor gouache children's storybook "
    "landscape, textured paper, soft hand painted brushstrokes."
)

NEGATIVE = (
    "fox, cat, dog, animal, person, human, character, creature, "
    "statue, portrait, face, extra objects, text, watermark, "
    "photorealistic, 3d render, blurry, low quality."
)

SEED = 7101
STEPS = 25
GUIDANCE = 7.0


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no disponible.")

    if not LUMA.exists():
        raise FileNotFoundError(
            f"No se encontro la referencia de Luma: {LUMA}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("FIFTHPLOT - PRUEBA DE COMPOSICION")
    print("=" * 55)

    print("GPU:", torch.cuda.get_device_name(0))
    print("Modelo: DreamShaper 8")
    print("Resolucion: 512x512")
    print("Precision: FP16")

    print("\nCargando modelo...")

    pipe = DiffusionPipeline.from_pretrained(
        str(MODEL),
        variant="fp16",
        dtype=torch.float16,
        use_safetensors=True,
        local_files_only=True
    )

    pipe.enable_sequential_cpu_offload(device="cuda")

    generator = torch.Generator(
        device="cpu"
    ).manual_seed(SEED)

    torch.cuda.reset_peak_memory_stats()

    print("\nGenerando fondo del bosque...")

    inicio = time.perf_counter()

    resultado = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE,
        width=512,
        height=512,
        num_inference_steps=STEPS,
        guidance_scale=GUIDANCE,
        generator=generator
    )

    torch.cuda.synchronize()

    tiempo = time.perf_counter() - inicio

    fondo = resultado.images[0].convert("RGBA")

    ruta_fondo = OUTPUT / "scene_01_background.png"
    fondo.save(ruta_fondo)

    print("Fondo guardado:", ruta_fondo)

    # Abrimos la referencia transparente de Luma.
    with Image.open(LUMA) as archivo:
        luma = archivo.convert("RGBA")

    # Eliminamos cualquier margen transparente sobrante.
    limites = luma.getchannel("A").getbbox()

    if limites is None:
        raise RuntimeError("La imagen de Luma esta vacia.")

    luma = luma.crop(limites)

    # Ajustamos el personaje al tamaño de la escena.
    factor = min(
        250 / luma.width,
        250 / luma.height,
        1.3
    )

    nuevo_tamano = (
        int(luma.width * factor),
        int(luma.height * factor)
    )

    luma = luma.resize(
        nuevo_tamano,
        Image.Resampling.LANCZOS
    )

    x = (512 - luma.width) // 2
    y = 512 - luma.height - 35

    # Creamos una sombra suave debajo del personaje.
    alpha = luma.getchannel("A")

    sombra_alpha = alpha.filter(
        ImageFilter.GaussianBlur(9)
    ).point(
        lambda valor: int(valor * 0.28)
    )

    sombra = Image.new(
        "RGBA",
        luma.size,
        (10, 20, 15, 0)
    )

    sombra.putalpha(sombra_alpha)

    # Componemos el escenario final.
    escena = fondo.copy()

    escena.alpha_composite(
        sombra,
        (x, y + 9)
    )

    escena.alpha_composite(
        luma,
        (x, y)
    )

    ruta_final = OUTPUT / "scene_01_luma_composed.png"

    escena.convert("RGB").save(ruta_final)

    memoria = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3),
        2
    )

    datos = {
        "proyecto": "FifthPlot",
        "prueba": "Composicion escena 1",
        "modelo_fondo": "DreamShaper 8",
        "personaje": "Luma",
        "referencia": str(LUMA),
        "resolucion": "512x512",
        "semilla": SEED,
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "tiempo_generacion": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria,
        "prompt_fondo": PROMPT,
        "prompt_negativo": NEGATIVE,
        "posicion_luma": [x, y],
        "tamanio_luma": list(nuevo_tamano),
        "resultado": str(ruta_final)
    }

    with open(
        OUTPUT / "scene_01_manifest.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            datos,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("\nCOMPOSICION COMPLETADA")
    print("Fondo:", ruta_fondo)
    print("Escena:", ruta_final)
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"VRAM pico: {memoria} GB")

    fondo.close()
    luma.close()
    alpha.close()
    sombra_alpha.close()
    sombra.close()
    escena.close()
    del resultado
    del pipe

    gc.collect()
    torch.cuda.empty_cache()

    print("\nMemoria GPU liberada.")


if __name__ == "__main__":
    main()
