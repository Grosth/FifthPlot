import gc
import json
import time
from pathlib import Path

import torch
from transformers import CLIPTokenizer

from fifthplot.generators import ip_adapter_test


# Carpeta independiente para las nuevas pruebas.
OUTPUT = Path("outputs/assets/characters/v3")

TOKENIZER_DIR = Path("models/stable-diffusion-v1-5/tokenizer")

SIZE = 512
STEPS = 20
GUIDANCE = 7.0

STYLE = (
    "Watercolor gouache storybook character illustration, "
    "soft brushstrokes, textured paper, plain warm ivory "
    "background, isolated subject, centered."
)


# Cada personaje tiene su propio prompt y negative prompt.
CHARACTERS = {

    "guardian": {

        "seed": 5201,

        "prompt": (
            "Front-facing elderly human man, clearly visible "
            "wrinkled face, long white hair, bright blue eyes, "
            "gentle serious expression, wearing a flowing black "
            "cloak. Three-quarter body portrait, standing upright."
        ),

        "negative": (
            "back view, facing away, hidden face, white robe, "
            "angel, ghost, bird, owl, wings, blonde hair, "
            "hood covering face, multiple people, trees, "
            "forest, cropped, extra limbs, text, watermark, "
            "3d render, photorealistic."
        )
    },

    "shadow_serpent": {

        "seed": 5202,

        "prompt": ("One black shadow serpent, one head, red glowing eyes, coiled black body, full creature visible, pointed sword-like tail."),

        "negative": (
            "red scales, blue scales, red body, multiple snakes, "
            "multiple heads, hydra, dragon, bird, wings, "
            "tentacles, flowers, plants, cropped, extra limbs, "
            "text, watermark, signature, 3d render, photorealistic."
        )
    }
}


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto CUDA.")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_DIR),
        local_files_only=True
    )

    print("=" * 50)
    print("FIFTHPLOT - PERSONAJES V3")
    print("=" * 50)

    # Validamos todos los prompts antes de cargar el modelo.
    for nombre, datos in CHARACTERS.items():

        prompt = f"{STYLE} {datos['prompt']}"

        tokens_prompt = len(
            tokenizer(prompt, truncation=False)["input_ids"]
        )

        tokens_negative = len(
            tokenizer(
                datos["negative"],
                truncation=False
            )["input_ids"]
        )

        print(f"\n{nombre}")
        print(f"Positivo: {tokens_prompt}/77")
        print(f"Negativo: {tokens_negative}/77")

        if tokens_prompt > 70 or tokens_negative > 70:
            raise ValueError(
                f"El prompt de {nombre} necesita reducirse."
            )

    print("\nCargando Stable Diffusion...")

    pipe = ip_adapter_test.cargar_pipeline(
        usando_referencia=False
    )

    resultados = []

    for nombre, datos in CHARACTERS.items():

        print("\n" + "-" * 40)
        print("GENERANDO:", nombre)

        prompt = f"{STYLE} {datos['prompt']}"

        generador = torch.Generator(
            device="cpu"
        ).manual_seed(datos["seed"])

        torch.cuda.reset_peak_memory_stats()

        inicio = time.perf_counter()

        resultado = pipe(
            prompt=prompt,
            negative_prompt=datos["negative"],
            height=SIZE,
            width=SIZE,
            num_inference_steps=STEPS,
            guidance_scale=GUIDANCE,
            generator=generador
        )

        tiempo = time.perf_counter() - inicio

        imagen = resultado.images[0]

        ruta = OUTPUT / f"{nombre}_v3.png"
        imagen.save(ruta)

        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        )

        metadatos = {
            "personaje": nombre,
            "modelo": "Stable Diffusion 1.5",
            "estilo": "Watercolor y gouache",
            "resolucion": f"{SIZE}x{SIZE}",
            "precision": "FP16",
            "semilla": datos["seed"],
            "pasos": STEPS,
            "guidance_scale": GUIDANCE,
            "tiempo_segundos": round(tiempo, 2),
            "memoria_gpu_pico_gb": memoria,
            "prompt": prompt,
            "negative_prompt": datos["negative"],
            "imagen": str(ruta)
        }

        with open(
            OUTPUT / f"{nombre}_v3.json",
            "w",
            encoding="utf-8"
        ) as archivo:
            json.dump(
                metadatos,
                archivo,
                ensure_ascii=False,
                indent=4
            )

        resultados.append({
            "personaje": nombre,
            "tiempo": round(tiempo, 2)
        })

        print("Imagen:", ruta)
        print(f"Tiempo: {tiempo:.2f} segundos")
        print(f"VRAM pico: {memoria} GB")

        del resultado
        del imagen

        gc.collect()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    print("\nPERSONAJES V3 GENERADOS")

    for item in resultados:
        print(item["personaje"], item["tiempo"], "segundos")

    print("\nCarpeta de resultados:", OUTPUT)


if __name__ == "__main__":
    main()
