import json
import gc
import time
from pathlib import Path

import torch
import diffusers
from diffusers import StableDiffusionPipeline

MODEL_DIR = Path("models/stable-diffusion-v1-5")
OUTPUT_DIR = Path("outputs/images")

# Configuracion de la primera prueba.
SEED = 42
IMAGE_SIZE = 512
STEPS = 15
GUIDANCE = 7.0

PROMPT = """Watercolor storybook art of Luma, a small red orange fox with golden eyes, tiny nose, fluffy messy fur and a large curled comet tail. Full body, all paws visible, standing in a teal enchanted forest. Soft moonlight, painterly gouache, visible brushstrokes, warm fur and cool blue green background."""

NEGATIVE_PROMPT = """cropped, hidden tail, extra limbs, extra ears, duplicate fox, other animals, blurry, text, watermark, photorealistic, 3d, plastic texture."""


def cargar_modelo():

    if not MODEL_DIR.exists():
        raise FileNotFoundError("No se encontro el modelo local.")

    print("\nCargando Stable Diffusion 1.5...")

    pipe = StableDiffusionPipeline.from_pretrained(
        str(MODEL_DIR),
        dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
        local_files_only=True,
        low_cpu_mem_usage=True
    )

    # Movemos las capas a GPU solamente cuando se necesitan.
    pipe.enable_sequential_cpu_offload()

    # Reducimos el consumo de memoria.
    # Usamos la atencion SDPA de PyTorch.
    pipe.vae.enable_slicing()

    pipe.set_progress_bar_config(desc="Generando imagen")

    return pipe


def generar_luma():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("FIFTHPLOT - GENERADOR DE IMAGENES")
    print("=" * 50)

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print("Precision: FP16")
    print(f"Resolucion: {IMAGE_SIZE}x{IMAGE_SIZE}")

    # Semilla fija para poder repetir el experimento.
    generador = torch.Generator(device="cpu").manual_seed(SEED)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    pipe = cargar_modelo()

    print("\nModelo cargado.")
    print("Generando ilustracion de Luma...")

    inicio = time.perf_counter()

    resultado = pipe(
        prompt=PROMPT,
        negative_prompt=NEGATIVE_PROMPT,
        height=IMAGE_SIZE,
        width=IMAGE_SIZE,
        num_inference_steps=STEPS,
        guidance_scale=GUIDANCE,
        generator=generador
    )

    tiempo = time.perf_counter() - inicio

    imagen = resultado.images[0]

    ruta_imagen = OUTPUT_DIR / "luma_referencia_v2.png"
    imagen.save(ruta_imagen)

    # Guardamos los parametros para documentar el experimento.
    memoria = 0

    if torch.cuda.is_available():
        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3), 2
        )

    datos = {
        "modelo": "Stable Diffusion 1.5",
        "tipo_pesos": "FP16 Safetensors",
        "dispositivo": torch.cuda.get_device_name(0),
        "precision": "float16",
        "resolucion": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "seed": SEED,
        "tiempo_segundos": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria,
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE_PROMPT
    }

    ruta_datos = OUTPUT_DIR / "luma_referencia_v2.json"

    with open(ruta_datos, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=4)

    print("\nGeneracion terminada.")
    print(f"Imagen guardada: {ruta_imagen}")
    print(f"Parametros guardados: {ruta_datos}")
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"Memoria GPU pico: {memoria} GB")

    # Liberamos la memoria para los siguientes modelos.
    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    print("\nMemoria de GPU liberada.")


if __name__ == "__main__":

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto una GPU compatible con CUDA.")

    generar_luma()
