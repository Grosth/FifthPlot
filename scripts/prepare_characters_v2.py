from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/characters.py")
codigo = archivo.read_text(encoding="utf-8")

# Evitamos elementos visuales no deseados.
negative = '''NEGATIVE = (
    "back view, facing away, hidden face, blonde hair, hood, "
    "turquoise robe, red scales, blue scales, dragon, hydra, "
    "multiple heads, tentacles, cropped, cut off, extra limbs, "
    "text, watermark, signature, photorealistic, 3d render."
)'''

# Descripciones mas directas para cada personaje.
personajes = '''PERSONAJES = {
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
}'''

# Actualizamos los bloques.
codigo, n1 = re.subn(
    r'NEGATIVE\s*=\s*\(.*?\n\)',
    lambda _: negative,
    codigo,
    count=1,
    flags=re.S
)

codigo, n2 = re.subn(
    r'PERSONAJES\s*=\s*\{.*?\n\}',
    lambda _: personajes,
    codigo,
    count=1,
    flags=re.S
)

if n1 != 1 or n2 != 1:
    raise RuntimeError("No se encontraron los bloques originales.")

# Cambiamos los nombres para no sobrescribir las pruebas.
codigo = codigo.replace(
    'f"{nombre}_original.png"',
    'f"{nombre}_v2.png"'
)

codigo = codigo.replace(
    'f"{nombre}_original.json"',
    'f"{nombre}_v2.json"'
)

# Verificamos los prompts con el tokenizer real.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

estilo = (
    "Watercolor gouache children's storybook illustration, "
    "soft painterly brushstrokes, textured paper, "
    "teal shadows and warm colors."
)

for nombre, datos in {
    "guardian": {
        "prompt": (
            "Front-facing elderly slender man, long white hair, "
            "visible bright blue eyes, kind serious face, full body, "
            "flowing black cloak, standing alone on plain ivory background."
        )
    },
    "shadow_serpent": {
        "prompt": (
            "One black shadow serpent, single visible head, "
            "glowing red eyes, long coiled black body, "
            "entire creature visible, pointed sword-shaped tail, "
            "smoky dark edges, alone on plain ivory background."
        )
    }
}.items():

    prompt = f"{estilo} {datos['prompt']}"

    tokens = len(
        tokenizer(prompt, truncation=False)["input_ids"]
    )

    print(f"{nombre}: {tokens}/77 tokens")

    if tokens > 70:
        raise RuntimeError(f"El prompt de {nombre} es demasiado largo.")

codigo_nuevo = codigo

codigo_nuevo = codigo_nuevo.replace(
    "PERSONAJES =",
    "PERSONAJES =",
    1
)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("\nNueva configuracion de personajes guardada.")
print("Se conservaran las generaciones anteriores.")
