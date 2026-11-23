import gc
import json
import time
from pathlib import Path

import torch
from PIL import Image
from diffusers import StableDiffusionPipeline
from transformers import CLIPTokenizer

# Rutas de los modelos y las imagenes.
BASE_DIR = Path("models/stable-diffusion-v1-5")
ADAPTER_DIR = Path("models/ip-adapter")
REFERENCE = Path("outputs/images/luma_referencia_v2.png")

OUTPUT_A = Path("experiments/configuration_a")
OUTPUT_B = Path("experiments/configuration_b")

# Parametros iguales para las dos pruebas.
SEED = 42
SIZE = 512
STEPS = 15
GUIDANCE = 7.0
ADAPTER_SCALE = 0.5

PROMPT = """Watercolor children's storybook illustration of Luma, the same small red-orange fox with golden eyes, tiny nose and fluffy fur, walking along a winding path in an enchanted teal forest at dusk. Full body, paws visible, large curled tail, soft gouache brushstrokes, warm fox against cool blue-green trees."""

NEGATIVE = """cropped, hidden tail, extra legs, extra ears, duplicate fox, blurry, text, watermark, photorealistic, 3d, plastic texture, multiple animals."""


def comprobar_archivos():

    archivos = [
        BASE_DIR / "model_index.json",
        ADAPTER_DIR / "models/ip-adapter-plus_sd15.safetensors",
        ADAPTER_DIR / "models/image_encoder/config.json",
        REFERENCE
    ]

    for archivo in archivos:
        if not archivo.exists():
            raise FileNotFoundError(f"No se encontro: {archivo}")

    # Revisamos que los prompts no superen el limite de CLIP.
    tokenizer = CLIPTokenizer.from_pretrained(
        str(BASE_DIR / "tokenizer"),
        local_files_only=True
    )

    for nombre, texto in [
        ("Positivo", PROMPT),
        ("Negativo", NEGATIVE)
    ]:
        cantidad = len(tokenizer(
            texto, truncation=False
        )["input_ids"])

        print(f"Prompt {nombre}: {cantidad}/77 tokens")

        if cantidad > 77:
            raise ValueError(f"El prompt {nombre} supera el limite.")


def cargar_pipeline(usando_referencia=False):

    print("\nCargando Stable Diffusion 1.5...")

    pipe = StableDiffusionPipeline.from_pretrained(
        str(BASE_DIR),
        dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
        local_files_only=True,
        low_cpu_mem_usage=True
    )

    pipe.vae.enable_slicing()

    if usando_referencia:

        print("Cargando IP-Adapter Plus...")

        pipe.load_ip_adapter(
            str(ADAPTER_DIR),
            subfolder="models",
            weight_name="ip-adapter-plus_sd15.safetensors",
            image_encoder_folder="image_encoder",
            local_files_only=True,
            low_cpu_mem_usage=True
        )

        pipe.set_ip_adapter_scale(ADAPTER_SCALE)

    # Movemos las capas a la GPU solo cuando se necesitan.
    pipe.enable_sequential_cpu_offload()

    return pipe


def generar_prueba(nombre, carpeta, usar_adapter=False):

    carpeta.mkdir(parents=True, exist_ok=True)

    pipe = cargar_pipeline(usar_adapter)

    referencia = None

    if usar_adapter:
        referencia = Image.open(REFERENCE).convert("RGB")

    generador = torch.Generator(device="cpu").manual_seed(SEED)

    torch.cuda.reset_peak_memory_stats()

    print(f"\nGenerando configuracion {nombre}...")
    inicio = time.perf_counter()

    parametros = {
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE,
        "height": SIZE,
        "width": SIZE,
        "num_inference_steps": STEPS,
        "guidance_scale": GUIDANCE,
        "generator": generador
    }

    if usar_adapter:
        parametros["ip_adapter_image"] = referencia

    resultado = pipe(**parametros)

    tiempo = time.perf_counter() - inicio

    imagen = resultado.images[0]

    ruta = carpeta / f"luma_configuracion_{nombre}.png"
    imagen.save(ruta)

    memoria = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3), 2
    )

    datos = {
        "configuracion": nombre,
        "modelo": "Stable Diffusion 1.5",
        "ip_adapter": usar_adapter,
        "referencia": str(REFERENCE) if usar_adapter else None,
        "adaptador": "IP-Adapter Plus SD15" if usar_adapter else None,
        "adapter_scale": ADAPTER_SCALE if usar_adapter else None,
        "seed": SEED,
        "resolucion": f"{SIZE}x{SIZE}",
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "tiempo_segundos": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria,
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE
    }

    with open(carpeta / f"resultados_{nombre}.json", "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=4)

    print(f"\nImagen guardada: {ruta}")
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"Memoria GPU pico: {memoria} GB")

    del resultado
    del pipe

    gc.collect()
    torch.cuda.empty_cache()

    if torch.cuda.is_available():
        torch.cuda.ipc_collect()

    if referencia is not None:
        referencia.close()


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto la GPU.")

    comprobar_archivos()

    print("=" * 55)
    print("FIFTHPLOT - EXPERIMENTO DE CONSISTENCIA")
    print("=" * 55)

    # A: generacion solamente con texto.
    generar_prueba("A", OUTPUT_A, usar_adapter=False)

    # B: generacion con texto e imagen de referencia.
    generar_prueba("B", OUTPUT_B, usar_adapter=True)

    print("\nExperimento A/B finalizado.")
    print("Revisa las carpetas configuration_a y configuration_b.")


if __name__ == "__main__":
    main()
