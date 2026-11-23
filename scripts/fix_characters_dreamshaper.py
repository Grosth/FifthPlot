from pathlib import Path
import re

from transformers import CLIPTokenizer

archivo = Path(
    "src/fifthplot/generators/characters_dreamshaper.py"
)

codigo = archivo.read_text(encoding="utf-8")

# Descripciones mas cortas para evitar el limite de CLIP.
prompts = {
    "guardian": (
        "Front-facing elderly human man with white hair, "
        "blue eyes, a wise wrinkled face and a long black "
        "cloak, standing alone, full body."
    ),

    "shadow_serpent": (
        "One black shadow serpent, single head, glowing "
        "red eyes, continuous coiled body, full creature "
        "visible, sharp sword-shaped tail."
    )
}

# Comprobamos los prompts con el tokenizer real.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/dreamshaper-8/tokenizer",
    local_files_only=True
)

style = (
    "Watercolor gouache children's storybook illustration, "
    "soft hand-painted brushstrokes, textured paper, "
    "beautiful warm colors, isolated full body character, "
    "centered on a plain warm ivory background."
)

codigo_nuevo = codigo

for nombre, prompt in prompts.items():

    patron = re.compile(
        rf'("{nombre}"\s*:\s*\{{.*?"prompt"\s*:\s*)\(.*?\)',
        re.S
    )

    reemplazo = (
        lambda m: m.group(1) + '(\n            "'
        + prompt + '"\n        )'
    )

    codigo_nuevo, cantidad = patron.subn(
        reemplazo,
        codigo_nuevo,
        count=1
    )

    if cantidad != 1:
        raise RuntimeError(
            f"No se encontro el prompt de {nombre}."
        )

    cantidad_tokens = len(
        tokenizer(
            style + " " + prompt,
            truncation=False
        )["input_ids"]
    )

    print(f"{nombre}: {cantidad_tokens}/77 tokens")

    if cantidad_tokens > 70:
        raise RuntimeError(
            f"El prompt de {nombre} supera el limite."
        )

# Guardamos solo cuando ambos prompts pasan la validacion.
archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("\nAmbos prompts corregidos correctamente.")
print("Semillas y configuracion conservadas.")
