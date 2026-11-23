from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/revise_story_images.py")
codigo = archivo.read_text(encoding="utf-8")

nuevas_escenas = '''ESCENAS = {
    3: (
        "Luma sees a white-haired guardian and red-eyed shadow "
        "serpent reflected in tall crystal mirrors."
    ),
    4: (
        "Luma faces a giant black shadow serpent with glowing "
        "red eyes and a sword-shaped tail."
    ),
    5: (
        "Stars return as Luma watches the defeated shadow "
        "serpent dissolve into glowing light."
    )
}'''

patron = r'ESCENAS\s*=\s*\{.*?\n\}'

codigo_nuevo, cantidad = re.subn(
    patron,
    lambda _: nuevas_escenas,
    codigo,
    count=1,
    flags=re.S
)

if cantidad != 1:
    raise RuntimeError("No se encontro el bloque de escenas.")

# Revisamos los prompts antes de guardar los cambios.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

estilo = (
    "Watercolor children's storybook, soft gouache "
    "brushstrokes, teal forest, warm colors."
)

luma = (
    "Luma, small red-orange fox, golden eyes, "
    "tiny nose, fluffy fur, large curled comet tail."
)

for numero, descripcion in {
    3: "Luma sees a white-haired guardian and red-eyed shadow serpent reflected in tall crystal mirrors.",
    4: "Luma faces a giant black shadow serpent with glowing red eyes and a sword-shaped tail.",
    5: "Stars return as Luma watches the defeated shadow serpent dissolve into glowing light."
}.items():

    prompt = f"{estilo} {luma} Scene: {descripcion}"

    tokens = len(
        tokenizer(prompt, truncation=False)["input_ids"]
    )

    print(f"Escena {numero}: {tokens}/77 tokens")

    if tokens > 70:
        raise RuntimeError(
            f"La escena {numero} sigue superando el limite preventivo."
        )

codigo_nuevo = codigo_nuevo.replace(
    "No se encontro el bloque de escenas.",
    "No se encontro el bloque de escenas."
) if False else codigo_nuevo

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("\nDescripciones corregidas y guardadas.")
