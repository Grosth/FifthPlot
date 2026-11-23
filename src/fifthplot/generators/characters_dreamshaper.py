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
OUTPUT = Path("outputs/assets/characters/dreamshaper_v1")

SIZE = 512
STEPS = 20
GUIDANCE = 7.0

STYLE = (
    "Watercolor gouache children's storybook illustration, "
    "soft hand-painted brushstrokes, textured paper, "
    "beautiful warm colors, isolated full body character, "
    "centered on a plain warm ivory background."
)

CHARACTERS = {

    "guardian": {
        "seed": 6101,

        "prompt": (
            "Front-facing elderly human man with white hair, blue eyes, a wise wrinkled face and a long black cloak, standing alone, full body."
        ),

        "negative": (
            "back view, hidden face, blonde hair, white robe, "
            "angel, ghost, owl, bird, wings, extra people, "
            "cropped, watermark, text, 3d render."
        )
    },

    "shadow_serpent": {
        "seed": 6102,

        "prompt": (
            "One black shadow serpent, single head, glowing red eyes, continuous coiled body, full creature visible, sharp sword-shaped tail."
        ),

        "negative": (
            "multiple snakes, hydra, multiple heads, dragon, "
            "octopus, tentacles, red body, blue scales, wings, "
            "legs, plants, cropped, watermark, text, 3d render."
        )
    }
}


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no disponible.")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(MODEL / "tokenizer"),
        local_files_only=True
    )

    print("=" * 55)
    print("FIFTHPLOT - PERSONAJES DREAMSHAPER")
    print("=" * 55)

    # Comprobamos todos los prompts antes de cargar el modelo.
    for name, data in CHARACTERS.items():

        positivo = f"{STYLE} {data['prompt']}"

        p_tokens = len(
            tokenizer(positivo, truncation=False)["input_ids"]
        )

        n_tokens = len(
            tokenizer(data["negative"], truncation=False)["input_ids"]
        )

        print(f"\n{name}")
        print(f"Positivo: {p_tokens}/77")
        print(f"Negativo: {n_tokens}/77")

        if p_tokens > 70 or n_tokens > 70:
            raise ValueError(
                f"El prompt de {name} necesita reducirse."
            )

    print("\nCargando DreamShaper 8...")

    pipe = DiffusionPipeline.from_pretrained(
        str(MODEL),
        variant="fp16",
        dtype=torch.float16,
        use_safetensors=True,
        local_files_only=True
    )

    pipe.enable_sequential_cpu_offload(device="cuda")

    pipe.set_progress_bar_config(
        desc="Generando personaje"
    )

    resultados = {}

    for name, data in CHARACTERS.items():

        print("\n" + "-" * 45)
        print("GENERANDO:", name)

        prompt = f"{STYLE} {data['prompt']}"

        generator = torch.Generator(
            device="cpu"
        ).manual_seed(data["seed"])

        torch.cuda.reset_peak_memory_stats()

        inicio = time.perf_counter()

        result = pipe(
            prompt=prompt,
            negative_prompt=data["negative"],
            width=SIZE,
            height=SIZE,
            num_inference_steps=STEPS,
            guidance_scale=GUIDANCE,
            generator=generator
        )

        torch.cuda.synchronize()

        tiempo = time.perf_counter() - inicio

        imagen = result.images[0]

        ruta = OUTPUT / f"{name}.png"
        imagen.save(ruta)

        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        )

        metadata = {
            "personaje": name,
            "modelo": "DreamShaper 8",
            "precision": "FP16",
            "resolucion": "512x512",
            "semilla": data["seed"],
            "pasos": STEPS,
            "guidance_scale": GUIDANCE,
            "tiempo_segundos": round(tiempo, 2),
            "memoria_gpu_pico_gb": memoria,
            "prompt": prompt,
            "negative_prompt": data["negative"],
            "imagen": str(ruta)
        }

        with open(
            OUTPUT / f"{name}.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=4
            )

        resultados[name] = {
            "tiempo": round(tiempo, 2),
            "vram": memoria
        }

        print("Imagen:", ruta)
        print(f"Tiempo: {tiempo:.2f} segundos")
        print(f"VRAM pico: {memoria} GB")

        imagen.close()
        del result

        gc.collect()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    print("\nGENERACION COMPLETADA")

    for name, data in resultados.items():
        print(name, data)

    print("\nResultados:", OUTPUT)
    print("Memoria GPU liberada.")


if __name__ == "__main__":
    main()
