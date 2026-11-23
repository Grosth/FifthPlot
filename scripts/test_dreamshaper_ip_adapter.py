import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
import json
import time

from pathlib import Path

import torch
from PIL import Image, ImageDraw
from diffusers import DiffusionPipeline
from transformers import CLIPTokenizer


MODEL_DIR = Path("models/dreamshaper-8")
ADAPTER_DIR = Path("models/ip-adapter")

LUMA_PATH = Path(
    "outputs/assets/characters/luma_reference_cropped.png"
)

OUTPUT_DIR = Path("outputs/images/ip_adapter_test")

OUTPUT_A = OUTPUT_DIR / "dreamshaper_text_only.png"
OUTPUT_B = OUTPUT_DIR / "dreamshaper_with_ip_adapter.png"

SEED = 42
STEPS = 15
GUIDANCE = 7.0
SCALE = 0.45

PROMPT = (
    "Luma, a small red-orange fox with golden eyes and a white muzzle, "
    "fluffy fur and a curled tail, standing beside an old tree in a "
    "teal enchanted forest at night, beneath a starless sky. "
    "Watercolor children's storybook illustration, gouache, "
    "textured paper, soft brushstrokes, warm amber light."
)

NEGATIVE = (
    "blurry, low quality, deformed anatomy, extra legs, "
    "extra ears, duplicate fox, cropped body, text, watermark, "
    "photorealistic, 3d render."
)


def preparar_referencia():

    original = Image.open(LUMA_PATH).convert("RGBA")

    fondo = Image.new(
        "RGB",
        (512, 512),
        (246, 241, 226)
    )

    escala = min(
        440 / original.width,
        440 / original.height
    )

    ancho = int(original.width * escala)
    alto = int(original.height * escala)

    personaje = original.resize(
        (ancho, alto),
        Image.Resampling.LANCZOS
    )

    posicion = (
        (512 - ancho) // 2,
        (512 - alto) // 2
    )

    fondo.paste(
        personaje,
        posicion,
        personaje.getchannel("A")
    )

    destino = OUTPUT_DIR / "luma_ip_reference.png"
    fondo.save(destino)

    original.close()
    personaje.close()
    fondo.close()

    return destino


def cargar_pipeline(con_adaptador=False):

    print("\nCargando DreamShaper 8...")

    pipe = DiffusionPipeline.from_pretrained(
        str(MODEL_DIR),
        variant="fp16",
        dtype=torch.float16,
        use_safetensors=True,
        local_files_only=True
    )

    if con_adaptador:

        print("Cargando IP-Adapter Plus SD15...")

        pipe.load_ip_adapter(
            str(ADAPTER_DIR),
            subfolder="models",
            weight_name="ip-adapter-plus_sd15.safetensors",
            image_encoder_folder="image_encoder",
            local_files_only=True
        )

        pipe.set_ip_adapter_scale(SCALE)

        print(f"IP-Adapter Scale: {SCALE}")

    # Evitamos trasladar todo el modelo a los 4 GB de VRAM.
    pipe.enable_sequential_cpu_offload(device="cuda")

    return pipe


def generar(pipe, nombre, referencia=None):

    generador = torch.Generator(
        device="cpu"
    ).manual_seed(SEED)

    torch.cuda.reset_peak_memory_stats()

    inicio = time.perf_counter()

    argumentos = {
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE,
        "width": 512,
        "height": 512,
        "num_inference_steps": STEPS,
        "guidance_scale": GUIDANCE,
        "generator": generador
    }

    if referencia is not None:
        imagen_referencia = Image.open(referencia).convert("RGB")
        argumentos["ip_adapter_image"] = imagen_referencia

    resultado = pipe(**argumentos)

    torch.cuda.synchronize()

    tiempo = time.perf_counter() - inicio

    imagen = resultado.images[0]

    ruta = OUTPUT_DIR / nombre
    imagen.save(ruta)

    memoria = round(
        torch.cuda.max_memory_allocated() / (1024 ** 3),
        2
    )

    if referencia is not None:
        imagen_referencia.close()

    imagen.close()
    del resultado

    print(f"Imagen guardada: {ruta}")
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"VRAM pico: {memoria} GB")

    return {
        "imagen": str(ruta),
        "tiempo_segundos": round(tiempo, 2),
        "memoria_gpu_pico_gb": memoria
    }


def crear_comparacion():

    imagen_a = Image.open(OUTPUT_A).convert("RGB")
    imagen_b = Image.open(OUTPUT_B).convert("RGB")

    comparacion = Image.new(
        "RGB",
        (1024, 550),
        "white"
    )

    dibujo = ImageDraw.Draw(comparacion)

    dibujo.text(
        (20, 12),
        "A - DREAMSHAPER 8 SIN IP-ADAPTER",
        fill="black"
    )

    dibujo.text(
        (532, 12),
        "B - DREAMSHAPER 8 CON IP-ADAPTER",
        fill="black"
    )

    comparacion.paste(imagen_a, (0, 38))
    comparacion.paste(imagen_b, (512, 38))

    destino = OUTPUT_DIR / "comparacion_ip_adapter.png"
    comparacion.save(destino)

    imagen_a.close()
    imagen_b.close()
    comparacion.close()

    print("\nComparacion guardada:", destino)


def main():

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA no esta disponible.")

    if not LUMA_PATH.exists():
        raise FileNotFoundError(
            f"No se encontro la referencia: {LUMA_PATH}"
        )

    adapter_weight = (
        ADAPTER_DIR / "models" /
        "ip-adapter-plus_sd15.safetensors"
    )

    image_encoder = (
        ADAPTER_DIR / "models" /
        "image_encoder" / "model.safetensors"
    )

    image_encoder_config = (
        ADAPTER_DIR / "models" /
        "image_encoder" / "config.json"
    )

    for archivo in [
        adapter_weight,
        image_encoder,
        image_encoder_config
    ]:
        if not archivo.exists():
            raise FileNotFoundError(
                f"No se encontro un componente: {archivo}"
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(MODEL_DIR / "tokenizer"),
        local_files_only=True
    )

    positivos = len(
        tokenizer(PROMPT, truncation=False)["input_ids"]
    )

    negativos = len(
        tokenizer(NEGATIVE, truncation=False)["input_ids"]
    )

    print("=" * 55)
    print("FIFTHPLOT - EXPERIMENTO DREAMSHAPER + IP-ADAPTER")
    print("=" * 55)

    print("GPU:", torch.cuda.get_device_name(0))
    print(f"Prompt positivo: {positivos}/77")
    print(f"Prompt negativo: {negativos}/77")

    if positivos > 70 or negativos > 70:
        raise ValueError("Los prompts superan el limite preventivo.")

    referencia = preparar_referencia()

    print("\nReferencia preparada:", referencia)

    resultados = {}

    # Primera prueba: solamente texto.
    pipe = cargar_pipeline(con_adaptador=False)

    print("\nGENERANDO PRUEBA A - SIN IP-ADAPTER")

    resultados["sin_ip_adapter"] = generar(
        pipe,
        OUTPUT_A.name
    )

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    # Segunda prueba: texto y referencia visual.
    pipe = cargar_pipeline(con_adaptador=True)

    print("\nGENERANDO PRUEBA B - CON IP-ADAPTER")

    resultados["con_ip_adapter"] = generar(
        pipe,
        OUTPUT_B.name,
        referencia
    )

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    crear_comparacion()

    manifiesto = {
        "experimento": "Comparacion DreamShaper 8 con IP-Adapter",
        "modelo": "DreamShaper 8",
        "adaptador": "IP-Adapter Plus SD15",
        "ip_adapter_scale": SCALE,
        "semilla": SEED,
        "pasos": STEPS,
        "guidance_scale": GUIDANCE,
        "resolucion": "512x512",
        "precision": "FP16",
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE,
        "referencia": str(referencia),
        "resultados": resultados
    }

    with open(
        OUTPUT_DIR / "manifest_ip_adapter.json",
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            manifiesto,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print("\nEXPERIMENTO COMPLETADO")
    print("Carpeta:", OUTPUT_DIR)
    print("Memoria GPU liberada.")


if __name__ == "__main__":
    main()
