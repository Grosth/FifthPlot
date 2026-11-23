import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
import json
import time
from pathlib import Path

import torch
from diffusers import DiffusionPipeline
from transformers import CLIPTokenizer


MODEL = Path("models/dreamshaper-8")
OUTPUT = Path("outputs/assets/characters/dreamshaper_v2")

PROMPT = (
    "One black serpent with a narrow reptile head and "
    "glowing red eyes. Its long body coils in an S shape "
    "and ends in a sharp sword-like tail. Show the entire "
    "creature, centered with clear space around it."
)

STYLE = (
    "Watercolor gouache storybook illustration, "
    "textured paper, soft painterly brushstrokes."
)

NEGATIVE = (
    "wolf, fox, dog, canine, dragon, wings, legs, extra heads, "
    "multiple snakes, cropped, close-up, fur, ears, long muzzle, "
    "red scales, blue scales, text, watermark, 3d render, photorealistic."
)

SEED = 6202
STEPS = 25
GUIDANCE = 7.0


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no esta disponible.")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(MODEL / "tokenizer"),
        local_files_only=True
    )

    prompt = f"{STYLE} {PROMPT}"

    positivos = len(
        tokenizer(prompt, truncation=False)["input_ids"]
    )

    negativos = len(
        tokenizer(NEGATIVE, truncation=False)["input_ids"]
    )

    print("FIFTHPLOT - SERPIENTE DE SOMBRAS V2")
    print("Positivo:", positivos, "/77 tokens")
    print("Negativo:", negativos, "/77 tokens")

    if positivos > 70 or negativos > 70:
        raise ValueError("El prompt supera el limite preventivo.")

    print("\nCargando DreamShaper 8...")

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

    print("\nGenerando Serpiente de Sombras V2...")

    inicio = time.perf_counter()

    resultado = pipe(
        prompt=prompt,
        negative_prompt=NEGATIVE,
        width=512,
        height=512,
        num_inference_steps=STEPS,
        guidance_scale=GUIDANCE,
        generator=generator
    )

    torch.cuda.synchronize()

    tiempo = time.perf_counter() - inicio

    imagen = resultado.images[0]

    ruta = OUTPUT / "shadow_serpent_v2.png"
    imagen.save(ruta)

    memoria = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3),
        2
    )

    metadata = {
        "personaje": "Serpiente de Sombras",
        "modelo": "DreamShaper 8",
        "precision": "FP16",
        "resolucion": "512x512",
        "semilla": SEED,
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "tiempo_segundos": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria,
        "prompt": prompt,
        "negative_prompt": NEGATIVE
    }

    with open(
        OUTPUT / "shadow_serpent_v2.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            metadata,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("\nGENERACION COMPLETADA")
    print("Imagen:", ruta)
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"VRAM pico: {memoria} GB")

    imagen.close()
    del resultado
    del pipe

    gc.collect()
    torch.cuda.empty_cache()

    print("\nMemoria GPU liberada.")


if __name__ == "__main__":
    main()
