import gc
import json
import time
from pathlib import Path

import torch
from transformers import CLIPTokenizer

from fifthplot.generators import ip_adapter_test


CARPETA = Path("outputs/assets/characters")
TOKENIZER_DIR = Path("models/stable-diffusion-v1-5/tokenizer")

TAMANO = 512
PASOS = 20
GUIDANCE = 7.0

ESTILO = (
    "Watercolor gouache children's storybook illustration, "
    "soft painterly brushstrokes, textured paper, "
    "teal shadows and warm colors."
)

NEGATIVE = (
    "back view, facing away, hidden face, blonde hair, hood, "
    "turquoise robe, red scales, blue scales, dragon, hydra, "
    "multiple heads, tentacles, cropped, cut off, extra limbs, "
    "text, watermark, signature, photorealistic, 3d render."
)

PERSONAJES = {
    "guardian": {
        "seed": 5101,
        "prompt": (
            "Front-facing elderly slender man, long white hair, "
            "visible bright blue eyes, kind serious face, full body, "
            "flowing black cloak, standing alone on plain ivory background."
        )
    },

    "shadow_serpent": {
        "seed": 5102,
        "prompt": (
            "One black shadow serpent, single visible head, "
            "glowing red eyes, long coiled black body, "
            "entire creature visible, pointed sword-shaped tail, "
            "smoky dark edges, alone on plain ivory background."
        )
    }
}


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto CUDA.")

    CARPETA.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_DIR),
        local_files_only=True
    )

    print("FIFTHPLOT - GENERADOR DE PERSONAJES")
    print("GPU:", torch.cuda.get_device_name(0))

    # Comprobamos los prompts.
    for nombre, datos in PERSONAJES.items():

        prompt = f"{ESTILO} {datos['prompt']}"

        tokens = len(
            tokenizer(prompt, truncation=False)["input_ids"]
        )

        print(f"{nombre}: {tokens}/77 tokens")

        if tokens > 70:
            raise ValueError(
                f"El prompt de {nombre} supera el limite."
            )

    # No usamos IP-Adapter porque son personajes nuevos.
    print("\nCargando Stable Diffusion...")

    pipe = ip_adapter_test.cargar_pipeline(
        usando_referencia=False
    )

    resultados = []

    for nombre, datos in PERSONAJES.items():

        print("\nGenerando:", nombre)

        prompt = f"{ESTILO} {datos['prompt']}"

        generador = torch.Generator(
            device="cpu"
        ).manual_seed(datos["seed"])

        torch.cuda.reset_peak_memory_stats()

        inicio = time.perf_counter()

        resultado = pipe(
            prompt=prompt,
            negative_prompt=NEGATIVE,
            height=TAMANO,
            width=TAMANO,
            num_inference_steps=PASOS,
            guidance_scale=GUIDANCE,
            generator=generador
        )

        tiempo = time.perf_counter() - inicio

        imagen = resultado.images[0]

        ruta = CARPETA / f"{nombre}_v2.png"
        imagen.save(ruta)

        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        )

        metadatos = {
            "personaje": nombre,
            "modelo": "Stable Diffusion 1.5",
            "estilo": "Watercolor y gouache",
            "precision": "FP16",
            "resolucion": f"{TAMANO}x{TAMANO}",
            "semilla": datos["seed"],
            "pasos": PASOS,
            "guidance_scale": GUIDANCE,
            "tiempo_segundos": round(tiempo, 2),
            "memoria_gpu_pico_gb": memoria,
            "prompt": prompt,
            "negative_prompt": NEGATIVE,
            "imagen": str(ruta)
        }

        with open(
            CARPETA / f"{nombre}_v2.json",
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

        print("Imagen guardada:", ruta)
        print(f"Tiempo: {tiempo:.2f} segundos")
        print(f"VRAM pico: {memoria} GB")

        del resultado
        del imagen

        gc.collect()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    print("\nPERSONAJES GENERADOS")

    for item in resultados:
        print(item["personaje"], "-", item["tiempo"], "segundos")

    print("\nProceso terminado.")


if __name__ == "__main__":
    main()
