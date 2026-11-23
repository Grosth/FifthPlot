import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
import json
import re
import time

from pathlib import Path

import torch
from diffusers import DiffusionPipeline
from transformers import CLIPTokenizer


MODEL_DIR = Path("models/dreamshaper-8")
REFERENCE_JSON = Path("outputs/images/luma_prueba_01.json")

OUTPUT_DIR = Path("outputs/images/model_test")
OUTPUT_IMAGE = OUTPUT_DIR / "dreamshaper_luma_test.png"
OUTPUT_JSON = OUTPUT_DIR / "dreamshaper_luma_test.json"

FALLBACK_PROMPT = (
    "Storybook illustration of Luma, a small red-orange fox "
    "with golden eyes, fluffy fur and a large curled tail, "
    "standing in an enchanted teal forest at night, looking "
    "at a dark sky where the stars have disappeared, soft "
    "moonlight, magical watercolor children's fantasy art."
)

FALLBACK_NEGATIVE = (
    "blurry, low quality, deformed body, extra legs, "
    "extra ears, duplicate character, text, watermark, "
    "photorealistic, 3d render."
)


def cargar_parametros():

    datos = {}

    if REFERENCE_JSON.exists():

        with open(REFERENCE_JSON, "r", encoding="utf-8") as f:
            datos = json.load(f)

        print("Parametros recuperados de Luma 01.")

    else:
        print("No se encontro el JSON original. Usaremos valores base.")

    prompt = datos.get("prompt") or FALLBACK_PROMPT
    negativo = datos.get("negative_prompt") or FALLBACK_NEGATIVE

    semilla = datos.get("seed")
    if semilla is None:
        semilla = datos.get("semilla", 42)

    pasos = int(datos.get("pasos", 15))
    guidance = float(datos.get("guidance_scale", 7.0))

    resolucion = datos.get("resolucion", "512x512")
    coincidencia = re.fullmatch(r"(\d+)[xX](\d+)", resolucion)

    if coincidencia:
        ancho, alto = map(int, coincidencia.groups())
    else:
        ancho, alto = 512, 512

    if ancho != 512 or alto != 512:
        print("Ajustando resolucion de prueba a 512x512.")
        ancho, alto = 512, 512

    return {
        "prompt_original": prompt,
        "negative_original": negativo,
        "seed": int(semilla),
        "steps": pasos,
        "guidance": guidance,
        "width": ancho,
        "height": alto
    }


def ajustar_tokens(texto, tokenizer):

    ids = tokenizer(
        texto,
        truncation=False
    )["input_ids"]

    if len(ids) <= 77:
        return texto

    print(f"Prompt original: {len(ids)}/77 tokens.")
    print("Ajustando al limite de CLIP...")

    ids = tokenizer(
        texto,
        truncation=True,
        max_length=77
    )["input_ids"]

    texto = tokenizer.decode(
        ids,
        skip_special_tokens=True
    )

    while len(tokenizer(texto)["input_ids"]) > 77:

        ids = tokenizer(
            texto,
            add_special_tokens=False
        )["input_ids"]

        texto = tokenizer.decode(
            ids[:-1],
            skip_special_tokens=True
        )

    return texto


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no esta disponible.")

    # Comprobamos que los componentes descargados existan.
    obligatorios = [
        "model_index.json",
        "unet/config.json",
        "unet/diffusion_pytorch_model.fp16.safetensors",
        "text_encoder/model.fp16.safetensors",
        "vae/diffusion_pytorch_model.fp16.safetensors",
        "safety_checker/model.fp16.safetensors"
    ]

    faltantes = [
        archivo for archivo in obligatorios
        if not (MODEL_DIR / archivo).is_file()
    ]

    if faltantes:
        raise FileNotFoundError(
            f"Faltan componentes del modelo: {faltantes}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parametros = cargar_parametros()

    tokenizer = CLIPTokenizer.from_pretrained(
        str(MODEL_DIR / "tokenizer"),
        local_files_only=True
    )

    prompt = ajustar_tokens(
        parametros["prompt_original"],
        tokenizer
    )

    negativo = ajustar_tokens(
        parametros["negative_original"],
        tokenizer
    )

    print("\n" + "=" * 55)
    print("FIFTHPLOT - PRUEBA DREAMSHAPER 8")
    print("=" * 55)

    print("GPU:", torch.cuda.get_device_name(0))
    print("Modelo: DreamShaper 8")
    print("Precision: FP16")
    print("Resolucion: 512x512")
    print("Pasos:", parametros["steps"])
    print("Guidance:", parametros["guidance"])
    print("Semilla:", parametros["seed"])

    print(
        f"Prompt positivo: "
        f"{len(tokenizer(prompt)['input_ids'])}/77 tokens"
    )

    print(
        f"Prompt negativo: "
        f"{len(tokenizer(negativo)['input_ids'])}/77 tokens"
    )

    print("\nCargando modelo local...")

    inicio_carga = time.perf_counter()

    pipe = DiffusionPipeline.from_pretrained(
        str(MODEL_DIR),
        variant="fp16",
        dtype=torch.float16,
        use_safetensors=True,
        local_files_only=True
    )

    # Utilizamos descarga secuencial a CPU para cuidar los 4 GB de VRAM.
    # No debemos mover el pipeline a CUDA antes de activar este metodo.
    pipe.enable_sequential_cpu_offload(device="cuda")

    carga = time.perf_counter() - inicio_carga

    print(f"Modelo cargado en {carga:.2f} segundos.")

    pipe.set_progress_bar_config(
        desc="DreamShaper 8"
    )

    generador = torch.Generator(
        device="cpu"
    ).manual_seed(parametros["seed"])

    torch.cuda.reset_peak_memory_stats()

    print("\nGenerando ilustracion de Luma...")

    inicio = time.perf_counter()

    resultado = pipe(
        prompt=prompt,
        negative_prompt=negativo,
        width=parametros["width"],
        height=parametros["height"],
        num_inference_steps=parametros["steps"],
        guidance_scale=parametros["guidance"],
        generator=generador
    )

    torch.cuda.synchronize()

    tiempo = time.perf_counter() - inicio

    imagen = resultado.images[0]
    imagen.save(OUTPUT_IMAGE)

    memoria = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3),
        2
    )

    datos_finales = {
        "modelo": "DreamShaper 8",
        "base": "Stable Diffusion 1.5",
        "precision": "FP16",
        "dispositivo": torch.cuda.get_device_name(0),
        "resolucion": "512x512",
        "semilla": parametros["seed"],
        "pasos": parametros["steps"],
        "guidance_scale": parametros["guidance"],
        "prompt": prompt,
        "negative_prompt": negativo,
        "tiempo_carga_segundos": round(carga, 2),
        "tiempo_generacion_segundos": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria,
        "imagen": str(OUTPUT_IMAGE)
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            datos_finales,
            f,
            ensure_ascii=False,
            indent=4
        )

    print("\nGENERACION COMPLETADA")
    print("Imagen:", OUTPUT_IMAGE)
    print("Parametros:", OUTPUT_JSON)
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"VRAM pico: {memoria} GB")

    imagen.close()
    del resultado
    del pipe

    gc.collect()
    torch.cuda.empty_cache()

    print("\nMemoria GPU liberada.")
    print("Prueba finalizada correctamente.")


if __name__ == "__main__":
    main()
