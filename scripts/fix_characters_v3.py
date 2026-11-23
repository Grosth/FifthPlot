from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/characters_v3.py")
codigo = archivo.read_text(encoding="utf-8")

# Localizamos exclusivamente el bloque de la serpiente.
inicio = re.search(
    r'"shadow_serpent"\s*:\s*\{',
    codigo
)

if not inicio:
    raise RuntimeError("No se encontro el bloque de la serpiente.")

resto = codigo[inicio.start():]

# Reemplazamos su prompt sin depender de los espacios originales.
patron = re.compile(
    r'("prompt"\s*:\s*)\(.*?\)',
    re.S
)

nuevo_prompt = (
    '"One black shadow serpent, one head, '
    'red glowing eyes, coiled black body, '
    'full creature visible, pointed sword-like tail."'
)

resto_nuevo, cantidad = patron.subn(
    lambda m: m.group(1) + "(" + nuevo_prompt + ")",
    resto,
    count=1
)

if cantidad != 1:
    raise RuntimeError("No se pudo actualizar el prompt.")

codigo_nuevo = codigo[:inicio.start()] + resto_nuevo

# Comprobamos el prompt completo con el tokenizer de Stable Diffusion.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

estilo = (
    "Watercolor gouache storybook character illustration, "
    "soft brushstrokes, textured paper, plain warm ivory "
    "background, isolated subject, centered."
)

prompt_completo = estilo + " " + nuevo_prompt

tokens = len(
    tokenizer(prompt_completo, truncation=False)["input_ids"]
)

print(f"Prompt de la serpiente: {tokens}/77 tokens")

if tokens > 70:
    raise RuntimeError("El prompt supera el limite preventivo.")

# Solo guardamos si todas las comprobaciones pasan.
archivo.write_text(codigo_nuevo, encoding="utf-8")

print("\nPrompt actualizado correctamente.")
print("El personaje Guardian permanece sin cambios.")
print("Las generaciones anteriores se conservan.")
