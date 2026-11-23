import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
import json
import time

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

import torch
from diffusers import DiffusionPipeline
from transformers import CLIPTokenizer
from rembg import new_session, remove


MODEL = Path("models/dreamshaper-8")
OUTPUT = Path("outputs/images/visual_pilot")

STEPS = 20
GUIDANCE = 7.0

STYLE = (
    "Watercolor gouache storybook, textured paper, "
    "soft brushstrokes, blue-violet palette, warm golden light."
)

NEGATIVE_CHARACTER = (
    "human, woman, girl, humanoid, princess, elf, person, "
    "hands, arms, dress, robe, cloak, upright body, "
    "multiple animals, extra legs, extra heads, cropped, "
    "text, watermark, photorealistic, 3d render, blurry."
)

NEGATIVE_BACKGROUND = (
    "fox, animal, person, human, creature, character, "
    "face, silhouette, text, watermark, photorealistic, "
    "3d render, blurry, low quality."
)


def newest_story():

    files = sorted(
        Path("outputs/stories").glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise FileNotFoundError("No hay historias disponibles.")

    return files[0]


def prepare_prompt(tokenizer, prompt, name):

    tokens = len(
        tokenizer(prompt, truncation=False)["input_ids"]
    )

    print(f"{name}: {tokens}/77 tokens")

    if tokens > 70:
        raise ValueError(
            f"El prompt de {name} supera el limite preventivo."
        )


def generate(pipe, prompt, negative, seed, filename):

    generator = torch.Generator(
        device="cpu"
    ).manual_seed(seed)

    torch.cuda.reset_peak_memory_stats()

    inicio = time.perf_counter()

    result = pipe(
        prompt=prompt,
        negative_prompt=negative,
        width=512,
        height=512,
        num_inference_steps=STEPS,
        guidance_scale=GUIDANCE,
        generator=generator
    )

    torch.cuda.synchronize()

    elapsed = time.perf_counter() - inicio

    image = result.images[0]

    destination = OUTPUT / filename
    image.save(destination)

    memory = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3),
        2
    )

    print(f"Imagen: {destination}")
    print(f"Tiempo: {elapsed:.2f} segundos")
    print(f"VRAM pico: {memory} GB")

    image.close()
    del result

    gc.collect()
    torch.cuda.empty_cache()

    return {
        "archivo": str(destination),
        "tiempo_segundos": round(elapsed, 2),
        "memoria_gpu_pico_gb": memory,
        "semilla": seed
    }


def create_preview(image):

    background = Image.new(
        "RGB",
        image.size,
        (245, 245, 245)
    )

    draw = ImageDraw.Draw(background)

    for y in range(0, image.height, 24):
        for x in range(0, image.width, 24):

            if (x // 24 + y // 24) % 2 == 0:
                draw.rectangle(
                    (x, y, x + 24, y + 24),
                    fill=(210, 210, 210)
                )

    result = Image.alpha_composite(
        background.convert("RGBA"),
        image
    ).convert("RGB")

    return background, result


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no disponible.")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    story_path = newest_story()

    historia = json.loads(
        story_path.read_text(encoding="utf-8-sig")
    )

    if len(historia["scenes"]) != 5:
        raise ValueError("La historia no tiene cinco escenas.")

    luna = next(
        (
            p for p in historia["characters"]
            if p["name"] == "Luna"
        ),
        None
    )

    if luna is None:
        raise ValueError("No existe el personaje Luna.")

    escena = historia["scenes"][0]

    if "Luna" not in escena["characters_present"]:
        raise ValueError("Luna no aparece en la primera escena.")

    character_prompt = (
        "Small white-blue fox, golden eyes, pointed ears, "
        "short muzzle, four paws, fluffy tail. Full body, "
        "standing on all fours, centered on plain ivory "
        "background. Watercolor gouache storybook, "
        "textured paper, soft blue-violet colors."
    )

    background_prompt = (
        escena["background_prompt"] + " " + STYLE
    )

    tokenizer = CLIPTokenizer.from_pretrained(
        str(MODEL / "tokenizer"),
        local_files_only=True
    )

    print("=" * 55)
    print("FIFTHPLOT - PRUEBA PILOTO VISUAL")
    print("=" * 55)

    print("Historia:", historia["title"])
    print("Personaje:", luna["name"])
    print("Escena:", escena["scene_title"])
    print("GPU:", torch.cuda.get_device_name(0))

    prepare_prompt(
        tokenizer,
        character_prompt,
        "Referencia de Luna"
    )

    prepare_prompt(
        tokenizer,
        background_prompt,
        "Fondo de escena 1"
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

    print("\nGENERANDO REFERENCIA DE LUNA")

    luna_result = generate(
        pipe,
        character_prompt,
        NEGATIVE_CHARACTER,
        8151,
        "luna_pilot_reference.png"
    )

    print("\nGENERANDO FONDO DE ESCENA 1")

    background_path = OUTPUT / "scene_01_background.png"

    if background_path.exists():
        print("\nReutilizando fondo aprobado de escena 1.")
        background_result = {
            "archivo": str(background_path),
            "reutilizado": True
        }
    else:
        background_result = generate(
            pipe,
            background_prompt,
            NEGATIVE_BACKGROUND,
            8152,
            "scene_01_background.png"
        )

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    print("\nSEPARANDO PERSONAJE CON U2NET...")

    with Image.open(
        OUTPUT / "luna_pilot_reference.png"
    ) as original:

        session = new_session(
            "u2net",
            providers=["CPUExecutionProvider"]
        )

        transparent = remove(
            original.convert("RGB"),
            session=session,
            alpha_matting=False,
            post_process_mask=True
        ).convert("RGBA")

    bbox = transparent.getchannel("A").getbbox()

    if bbox is None:
        raise RuntimeError("No se pudo segmentar a Luna.")

    left, top, right, bottom = bbox

    padding = 12

    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(512, right + padding)
    bottom = min(512, bottom + padding)

    luna_cutout = transparent.crop(
        (left, top, right, bottom)
    )

    cutout_path = OUTPUT / "luna_transparent.png"
    luna_cutout.save(cutout_path)

    print("Personaje transparente:", cutout_path)

    with Image.open(
        OUTPUT / "scene_01_background.png"
    ) as original_background:

        scene = original_background.convert("RGBA")

    # Ajustamos a Luma respetando sus proporciones.
    factor = min(
        250 / luna_cutout.width,
        275 / luna_cutout.height
    )

    size = (
        int(luna_cutout.width * factor),
        int(luna_cutout.height * factor)
    )

    luna_cutout = luna_cutout.resize(
        size,
        Image.Resampling.LANCZOS
    )

    x = (512 - size[0]) // 2
    y = 512 - size[1] - 28

    # Sombra suave debajo del personaje.
    alpha = luna_cutout.getchannel("A")

    shadow_alpha = alpha.filter(
        ImageFilter.GaussianBlur(8)
    ).point(
        lambda value: int(value * 0.25)
    )

    shadow = Image.new(
        "RGBA",
        size,
        (10, 20, 15, 0)
    )

    shadow.putalpha(shadow_alpha)

    scene.alpha_composite(shadow, (x, y + 7))
    scene.alpha_composite(luna_cutout, (x, y))

    final_path = OUTPUT / "scene_01_composed.png"

    scene.convert("RGB").save(final_path)

    # Vista previa del recorte.
    checker, preview = create_preview(luna_cutout)

    preview.save(OUTPUT / "luna_preview.png")

    manifest = {
        "proyecto": "FifthPlot",
        "historia": historia["title"],
        "modelo": "DreamShaper 8",
        "precision": "FP16",
        "resolucion": "512x512",
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "personaje": luna["name"],
        "referencia_visual": luna["visual_prompt"],
        "fondo": escena["background_prompt"],
        "participantes": escena["characters_present"],
        "generaciones": {
            "luna": luna_result,
            "fondo": background_result
        },
        "resultado": str(final_path)
    }

    with open(
        OUTPUT / "pilot_manifest.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            manifest,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    transparent.close()
    luna_cutout.close()
    scene.close()
    alpha.close()
    shadow_alpha.close()
    shadow.close()
    checker.close()
    preview.close()

    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 55)
    print("PRUEBA PILOTO COMPLETADA")
    print("Fondo: scene_01_background.png")
    print("Luna: luna_transparent.png")
    print("Composicion: scene_01_composed.png")
    print("Manifest: pilot_manifest.json")
    print("=" * 55)


if __name__ == "__main__":
    main()
