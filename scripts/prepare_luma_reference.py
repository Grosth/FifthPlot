from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/images.py")
codigo = archivo.read_text(encoding="utf-8")

prompt = """full body character portrait of Luma, a small red fox with bright fluffy red fur, golden eyes, tiny nose and a large curled comet tail with white tip. Three-quarter view, standing alone, centered, entire tail visible, plain warm cream background, painterly 2D children's fantasy storybook art."""

negative = """forest, trees, stars, moon, scenery, other animals, extra foxes, cropped body, hidden tail, blurry, deformed, extra legs, extra ears, text, watermark, photorealistic, 3D"""


def reemplazar(nombre, valor):
    global codigo

    patron = rf'{nombre}\s*=\s*""".*?"""'
    nuevo = f'{nombre} = """{valor}"""'

    codigo, cantidad = re.subn(
        patron,
        lambda _: nuevo,
        codigo,
        count=1,
        flags=re.S
    )

    if cantidad != 1:
        raise RuntimeError(f"No se pudo actualizar {nombre}")


reemplazar("PROMPT", prompt)
reemplazar("NEGATIVE_PROMPT", negative)

# Conservamos las dos pruebas anteriores.
codigo = codigo.replace(
    "luma_prueba_02.png",
    "luma_referencia.png"
)

codigo = codigo.replace(
    "luma_prueba_02.json",
    "luma_referencia.json"
)

# Comprobamos los tokens antes de generar.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

tokens_positivos = len(
    tokenizer(prompt, truncation=False)["input_ids"]
)

tokens_negativos = len(
    tokenizer(negative, truncation=False)["input_ids"]
)

print(f"Prompt positivo: {tokens_positivos}/77 tokens")
print(f"Prompt negativo: {tokens_negativos}/77 tokens")

if tokens_positivos > 77 or tokens_negativos > 77:
    raise RuntimeError("Los prompts superan el limite de CLIP.")

archivo.write_text(codigo, encoding="utf-8")

print("Referencia de Luma preparada correctamente.")
