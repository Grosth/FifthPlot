from pathlib import Path
import re

from transformers import CLIPTokenizer

archivo = Path("scripts/test_dreamshaper_ip_adapter.py")
codigo = archivo.read_text(encoding="utf-8")

nuevo_prompt = '''PROMPT = (
    "Luma, a small red-orange fox with golden eyes and a white muzzle, "
    "fluffy fur and a curled tail, standing beside an old tree in a "
    "teal enchanted forest at night, beneath a starless sky. "
    "Watercolor children's storybook illustration, gouache, "
    "textured paper, soft brushstrokes, warm amber light."
)'''

codigo_nuevo, cantidad = re.subn(
    r'PROMPT\s*=\s*\(.*?\)',
    lambda _: nuevo_prompt,
    codigo,
    count=1,
    flags=re.S
)

if cantidad != 1:
    raise RuntimeError("No se encontro el bloque PROMPT.")

# Comprobamos los dos prompts antes de guardar.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/dreamshaper-8/tokenizer",
    local_files_only=True
)

coincidencia = re.search(
    r'PROMPT\s*=\s*\((.*?)\)',
    codigo_nuevo,
    re.S
)

positivo = (
    "Luma, a small red-orange fox with golden eyes and a white muzzle, "
    "fluffy fur and a curled tail, standing beside an old tree in a "
    "teal enchanted forest at night, beneath a starless sky. "
    "Watercolor children's storybook illustration, gouache, "
    "textured paper, soft brushstrokes, warm amber light."
)

negativo_match = re.search(
    r'NEGATIVE\s*=\s*\((.*?)\)',
    codigo_nuevo,
    re.S
)

if not negativo_match:
    raise RuntimeError("No se encontro el prompt negativo.")

positivo_tokens = len(
    tokenizer(positivo, truncation=False)["input_ids"]
)

negativo = re.findall(
    r'"([^"]*)"',
    negativo_match.group(1)
)

negativo = "".join(negativo)

negativo_tokens = len(
    tokenizer(negativo, truncation=False)["input_ids"]
)

print(f"Prompt positivo: {positivo_tokens}/77 tokens")
print(f"Prompt negativo: {negativo_tokens}/77 tokens")

if positivo_tokens > 70 or negativo_tokens > 70:
    raise RuntimeError("Los prompts siguen superando el limite.")

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("\nPrompt corregido correctamente.")
print("La configuracion del experimento se conserva.")
