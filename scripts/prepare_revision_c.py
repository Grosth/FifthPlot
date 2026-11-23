from pathlib import Path
import re

from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/revise_story_images.py")
codigo = archivo.read_text(encoding="utf-8")

# Nueva escala para dar mas libertad al prompt.
codigo, n1 = re.subn(
    r"IP_SCALE\s*=\s*0\.5",
    "IP_SCALE = 0.35",
    codigo,
    count=1
)

# Evitamos la duplicacion de Luma.
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

# Descripciones mas directas de los acontecimientos.
escenas = '''ESCENAS = {
    3: (
        "One fox faces crystal mirrors. One mirror shows an "
        "old white-haired man with blue eyes; another reflects "
        "a black serpent with red eyes."
    ),
    4: (
        "One small fox faces one large black serpent. The serpent "
        "is clearly visible, coiled, with glowing red eyes and "
        "a sword-shaped tail."
    ),
    5: (
        "One fox watches bright stars return. Behind her, the "
        "defeated black serpent dissolves into glowing shadow "
        "particles on the forest floor."
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
    raise RuntimeError(
        "No se pudieron actualizar todos los parametros."
    )

# Guardamos esta variante por separado.
codigo = codigo.replace(
    '"outputs/images/revised"',
    '"outputs/images/revised_v2"'
)

# Verificamos los prompts con el tokenizer real.
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
    3: "One fox faces crystal mirrors. One mirror shows an old white-haired man with blue eyes; another reflects a black serpent with red eyes.",
    4: "One small fox faces one large black serpent. The serpent is clearly visible, coiled, with glowing red eyes and a sword-shaped tail.",
    5: "One fox watches bright stars return. Behind her, the defeated black serpent dissolves into glowing shadow particles on the forest floor."
}

print("\nConfiguracion C - validacion")

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
