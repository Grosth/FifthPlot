from pathlib import Path
import re

from transformers import CLIPTokenizer

archivo = Path(
    "src/fifthplot/generators/shadow_serpent_v2.py"
)

codigo = archivo.read_text(encoding="utf-8")

nuevo_bloque = '''PROMPT = (
    "One black serpent with a narrow reptile head and "
    "glowing red eyes. Its long body coils in an S shape "
    "and ends in a sharp sword-like tail. Show the entire "
    "creature, centered with clear space around it."
)'''

codigo_nuevo, cantidad = re.subn(
    r'PROMPT\s*=\s*\(.*?\)',
    lambda _: nuevo_bloque,
    codigo,
    count=1,
    flags=re.S
)

if cantidad != 1:
    raise RuntimeError("No se encontro el prompt original.")

tokenizer = CLIPTokenizer.from_pretrained(
    "models/dreamshaper-8/tokenizer",
    local_files_only=True
)

estilo = (
    "Watercolor gouache storybook illustration, "
    "textured paper, soft painterly brushstrokes."
)

prompt = (
    "One black serpent with a narrow reptile head and "
    "glowing red eyes. Its long body coils in an S shape "
    "and ends in a sharp sword-like tail. Show the entire "
    "creature, centered with clear space around it."
)

positivo_tokens = len(
    tokenizer(
        f"{estilo} {prompt}",
        truncation=False
    )["input_ids"]
)

print(f"Prompt positivo: {positivo_tokens}/77 tokens")

if positivo_tokens > 70:
    raise RuntimeError("El prompt todavia supera el limite.")

archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("\nPrompt de la Serpiente corregido.")
print("Semilla y parametros originales conservados.")
