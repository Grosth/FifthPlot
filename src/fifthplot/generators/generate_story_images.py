import gc
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import CLIPTokenizer

from fifthplot.generators import ip_adapter_test as ip_test


# 1. CONFIGURACION

MODEL = "qwen3:4b-q4_K_M"
OLLAMA_URL = "http://localhost:11434/api/chat"

STORY_DIR = Path("outputs/stories")
IMAGE_DIR = Path("outputs/images/final")
REFERENCE = Path("outputs/images/luma_prueba_01.png")
TOKENIZER_DIR = Path("models/stable-diffusion-v1-5/tokenizer")

IMAGE_SIZE = 512
STEPS = 20
GUIDANCE = 7.0
IP_SCALE = 0.5

BASE_SEED = 4200

ART_STYLE = "Watercolor storybook art, soft gouache brushstrokes, teal forest, warm colors."

LUMA_IDENTITY = "Luma, small red-orange fox, golden eyes, tiny nose, fluffy fur, large curled comet tail."

NEGATIVE_PROMPT = (
    "cropped, hidden tail, extra limbs, extra ears, "
    "duplicate fox, blurry, low quality, text, watermark, "
    "photorealistic, 3d render, plastic texture."
)

PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "prompts": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "description_en": {"type": "string"}
                },
                "required": ["number", "description_en"]
            }
        }
    },
    "required": ["prompts"]
}


# 2. BUSCAR LA HISTORIA

def cargar_historia():

    historias = list(STORY_DIR.glob("*.json"))

    if not historias:
        raise FileNotFoundError(
            "No se encontraron historias en outputs/stories."
        )

    # Utilizamos la historia mas reciente.
    archivo = max(
        historias,
        key=lambda ruta: ruta.stat().st_mtime
    )

    with open(archivo, "r", encoding="utf-8") as f:
        historia = json.load(f)

    escenas = historia.get("scenes", [])

    if len(escenas) != 5:
        raise ValueError("La historia debe tener cinco escenas.")

    numeros = [escena["number"] for escena in escenas]

    if sorted(numeros) != [1, 2, 3, 4, 5]:
        raise ValueError("La numeracion de las escenas no es valida.")

    print(f"\nHistoria seleccionada: {historia['title']}")
    print(f"Archivo: {archivo}")

    return historia, archivo


# 3. TRADUCIR LOS PROMPTS CON QWEN3

def traducir_prompts(escenas):

    print("\nPreparando las descripciones visuales...")

    entradas = []

    for escena in escenas:
        entradas.append({
            "number": escena["number"],
            "title": escena["scene_title"],
            "description": escena["image_prompt"],
            "context": escena["narrative"]
        })

    mensaje = """
    Traduce al ingles las cinco descripciones visuales de un cuento.

    Devuelve exactamente cinco descripciones, numeradas del 1 al 5.

    Reglas:
    - Utiliza ingles sencillo para Stable Diffusion 1.5.
    - Cada descripcion debe tener como maximo 10 palabras.
    - Conserva la accion y el escenario de cada escena.
    - Incluye otros personajes cuando sean importantes.
    - No inventes acontecimientos.
    - No repitas la descripcion fisica de Luma.
    - No incluyas explicaciones ni texto adicional.

    DESCRIPCIONES:
    """ + json.dumps(entradas, ensure_ascii=False)

    datos = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You translate concise visual prompts for image generation."
            },
            {
                "role": "user",
                "content": mensaje
            }
        ],
        "format": PROMPT_SCHEMA,
        "think": False,
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": 1200
        }
    }

    solicitud = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(solicitud, timeout=600) as respuesta:
            resultado = json.loads(respuesta.read().decode("utf-8"))

        contenido = resultado["message"]["content"]
        traducciones = json.loads(contenido)["prompts"]

    except urllib.error.URLError as error:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Comprueba que Ollama este iniciado."
        ) from error

    numeros = [item["number"] for item in traducciones]

    if sorted(numeros) != [1, 2, 3, 4, 5]:
        raise ValueError("Qwen3 no devolvio las cinco traducciones.")

    traducciones.sort(key=lambda item: item["number"])

    print("Cinco descripciones traducidas correctamente.")

    return traducciones


# 4. PREPARAR LOS PROMPTS


def preparar_prompts(traducciones):

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_DIR),
        local_files_only=True
    )

    prompts = []

    for item in traducciones:

        descripcion = item["description_en"].strip()

        prefijo = f"{ART_STYLE} {LUMA_IDENTITY} Scene:"
        prompt = f"{prefijo} {descripcion}"

        tokens = tokenizer(
            prompt,
            truncation=False
        )["input_ids"]

        reducciones = 0

        # Reducimos solamente la descripcion de la escena.
        # Nunca eliminamos la identidad de Luma ni el estilo.
        while len(tokens) > 77:

            tokens_escena = tokenizer(
                descripcion,
                add_special_tokens=False
            )["input_ids"]

            if len(tokens_escena) <= 4:
                raise ValueError(
                    f"No se pudo ajustar el prompt de la escena "
                    f"{item['number']}."
                )

            descripcion = tokenizer.decode(
                tokens_escena[:-2],
                skip_special_tokens=True
            ).strip()

            prompt = f"{prefijo} {descripcion}"

            tokens = tokenizer(
                prompt,
                truncation=False
            )["input_ids"]

            reducciones += 1

        item["description_en"] = descripcion

        print(
            f"Escena {item['number']}: "
            f"{len(tokens)}/77 tokens"
        )

        if reducciones:
            print(
                f"Descripcion ajustada: "
                f"{reducciones} reducciones."
            )

        prompts.append(prompt)

    cantidad_negativo = len(
        tokenizer(
            NEGATIVE_PROMPT,
            truncation=False
        )["input_ids"]
    )

    print(f"Prompt negativo: {cantidad_negativo}/77 tokens")

    if cantidad_negativo > 77:
        raise ValueError(
            "El prompt negativo supera el limite de CLIP."
        )

    return prompts



# 5. GENERAR LAS CINCO ILUSTRACIONES

def generar_ilustraciones(historia, archivo_historia, traducciones, prompts):

    if not torch.cuda.is_available():
        raise RuntimeError("No se detecto una GPU CUDA.")

    if not REFERENCE.exists():
        raise FileNotFoundError("No se encontro la referencia de Luma 01.")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 55)
    print("FIFTHPLOT - ILUSTRACIONES DEL CUENTO")
    print("=" * 55)

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Resolucion: {IMAGE_SIZE}x{IMAGE_SIZE}")
    print(f"Pasos: {STEPS}")
    print(f"IP-Adapter Scale: {IP_SCALE}")
    print("Referencia: Luma 01")

    # Utilizamos el mismo metodo de carga que ya validamos.
    ip_test.REFERENCE = REFERENCE
    ip_test.ADAPTER_SCALE = IP_SCALE

    print("\nCargando Stable Diffusion e IP-Adapter...")

    pipe = ip_test.cargar_pipeline(usando_referencia=True)

    referencia = Image.open(REFERENCE).convert("RGB")

    resultados = []

    for escena, traduccion, prompt in zip(
        historia["scenes"],
        traducciones,
        prompts
    ):

        numero = escena["number"]
        semilla = BASE_SEED + numero

        print("\n" + "-" * 45)
        print(f"GENERANDO ESCENA {numero}/5")
        print(escena["scene_title"])

        generador = torch.Generator(
            device="cpu"
        ).manual_seed(semilla)

        torch.cuda.reset_peak_memory_stats()

        inicio = time.perf_counter()

        resultado = pipe(
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            ip_adapter_image=referencia,
            height=IMAGE_SIZE,
            width=IMAGE_SIZE,
            num_inference_steps=STEPS,
            guidance_scale=GUIDANCE,
            generator=generador
        )

        tiempo = time.perf_counter() - inicio

        imagen = resultado.images[0]

        ruta = IMAGE_DIR / f"scene_{numero:02d}.png"
        imagen.save(ruta)

        memoria = round(
            torch.cuda.max_memory_allocated() / (1024 ** 3),
            2
        )

        datos = {
            "escena": numero,
            "titulo": escena["scene_title"],
            "historia": historia["title"],
            "modelo": "Stable Diffusion 1.5",
            "adaptador": "IP-Adapter Plus SD15",
            "referencia": str(REFERENCE),
            "adapter_scale": IP_SCALE,
            "semilla": semilla,
            "resolucion": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
            "pasos": STEPS,
            "guidance_scale": GUIDANCE,
            "precision": "FP16",
            "tiempo_segundos": round(tiempo, 2),
            "memoria_gpu_pico_gb": memoria,
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "descripcion_original": escena["image_prompt"],
            "descripcion_traducida": traduccion["description_en"],
            "imagen": str(ruta)
        }

        ruta_json = IMAGE_DIR / f"scene_{numero:02d}.json"

        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

        resultados.append(datos)

        print(f"Imagen guardada: {ruta}")
        print(f"Tiempo: {tiempo:.2f} segundos")
        print(f"Memoria GPU pico: {memoria} GB")

        del resultado
        del imagen

        gc.collect()
        torch.cuda.empty_cache()

    referencia.close()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    # Guardamos el registro general.
    resumen = {
        "historia": historia["title"],
        "archivo_historia": str(archivo_historia),
        "modelo": "Stable Diffusion 1.5",
        "estrategia": "Prompt + IP-Adapter Plus",
        "referencia": str(REFERENCE),
        "adapter_scale": IP_SCALE,
        "resolucion": f"{IMAGE_SIZE}x{IMAGE_SIZE}",
        "pasos": STEPS,
        "resultados": resultados
    }

    with open(IMAGE_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=4)

    return resultados


# 6. CREAR HOJA DE CONTACTO

def crear_hoja_contacto(historia):

    nombres = [
        IMAGE_DIR / f"scene_{i:02d}.png"
        for i in range(1, 6)
    ]

    ancho = 360
    alto = 360
    margen = 20
    espacio = 20
    cabecera = 45

    lienzo = Image.new(
        "RGB",
        (margen * 2 + ancho * 2 + espacio,
         margen * 2 + (alto + cabecera) * 3),
        "white"
    )

    dibujo = ImageDraw.Draw(lienzo)

    for indice, ruta in enumerate(nombres):

        if not ruta.exists():
            continue

        imagen = Image.open(ruta).convert("RGB")
        imagen = imagen.resize((ancho, alto))

        columna = indice % 2
        fila = indice // 2

        x = margen + columna * (ancho + espacio)
        y = margen + fila * (alto + cabecera)

        dibujo.text(
            (x, y),
            f"Escena {indice + 1}",
            fill="black"
        )

        lienzo.paste(imagen, (x, y + cabecera))

        imagen.close()

    ruta_contacto = IMAGE_DIR / "hoja_contacto.png"

    lienzo.save(ruta_contacto)
    lienzo.close()

    print(f"\nHoja de contacto guardada: {ruta_contacto}")


# 7. EJECUCION PRINCIPAL

def main():

    historia, archivo_historia = cargar_historia()

    traducciones = traducir_prompts(historia["scenes"])

    prompts = preparar_prompts(traducciones)

    # Guardamos las traducciones antes de generar.
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    with open(IMAGE_DIR / "prompts_traducidos.json", "w", encoding="utf-8") as f:
        json.dump(traducciones, f, ensure_ascii=False, indent=4)

    resultados = generar_ilustraciones(
        historia,
        archivo_historia,
        traducciones,
        prompts
    )

    crear_hoja_contacto(historia)

    tiempo_total = sum(
        item["tiempo_segundos"] for item in resultados
    )

    print("\n" + "=" * 55)
    print("ILUSTRACIONES GENERADAS CORRECTAMENTE")
    print("Escenas: 5 de 5")
    print(f"Tiempo total de generacion: {tiempo_total:.2f} segundos")
    print(f"Resultados: {IMAGE_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
