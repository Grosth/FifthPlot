from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/revise_story_images.py")
codigo = archivo.read_text(encoding="utf-8")

# Nueva escala de IP-Adapter.
codigo, n1 = re.subn(
    r"IP_SCALE\s*=\s*0\.5",
    "IP_SCALE = 0.35",
    codigo,
    count=1
)

# Evitamos que aparezcan zorritas duplicadas.
codigo, n2 = re.subn(
    r'NEGATIVE\s*=\s*\(.*?\n\)',
    '''NEGATIVE = (
    "two foxes, multiple foxes, duplicate fox, second fox, "
    "extra fox, cropped, hidden tail, extra limbs, extra ears, "
    "blurry, text, watermark, photorealistic, 3d render."
)''',
    codigo,
    count=1,
    flags=re.S
)

# Nuevas descripciones narrativas.
escenas = '''ESCENAS = {
    3: (
        "Tall mirrors reflect a white-haired guardian "
        "and a red-eyed shadow serpent."
    ),
    4: (
        "Luma faces a coiled black serpent with glowing "
        "red eyes and a sword-shaped tail."
    ),
    5: (
        "Stars return as the defeated shadow serpent "
        "dissolves into glowing light."
    )
}'''

codigo, n3 = re.subn(
    r'ESCENAS\s*=\s*\{.*?\n\}',
    lambda _: escenas,
    codigo,
    count=1,
    flags=re.S
)

if n1 != 1 or n2 != 1 or n3 != 1:
    raise RuntimeError("No se pudieron actualizar todos los bloques.")

# Conservamos las versiones anteriores.
codigo = codigo.replace(
    'Path("outputs/images/revised")',
    'Path("outputs/images/revised_v2")'
)

# Comprobamos los prompts con el tokenizer real.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

style = (
    "Watercolor children's storybook, soft gouache "
    "brushstrokes, teal forest, warm colors."
)

luma = (
    "Luma, small red-orange fox, golden eyes, "
    "tiny nose, fluffy fur, large curled comet tail."
)

descripciones = {
    3: "Tall mirrors reflect a white-haired guardian and a red-eyed shadow serpent.",
    4: "Luma faces a coiled black serpent with glowing red eyes and a sword-shaped tail.",
    5: "Stars return as the defeated shadow serpent dissolves into glowing light."
}

print("\nCONFIGURACION C - VALIDACION")

for numero, descripcion in descripciones.items():
    prompt = f"{style} {luma} Scene: {descripcion}"

    tokens = len(
        tokenizer(prompt, truncation=False)["input_ids"]
    )

    print(f"Escena {numero}: {tokens}/77 tokens")

    if tokens > 70:
        raise RuntimeError(
            f"La escena {numero} supera el limite preventivo."
        )

archivo.write_text(codigo, encoding="utf-8")

print("\nConfiguracion C guardada correctamente.")
print("IP-Adapter Scale: 0.35")
print("Resultados: outputs/images/revised_v2/")
