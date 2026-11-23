from pathlib import Path
import re
import shutil

from transformers import CLIPTokenizer

archivo = Path(
    "src/fifthplot/generators/visual_generation_pilot.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

patron = re.compile(
    r'(?ms)^    character_prompt\s*=\s*\(\n.*?^    \)'
)

nuevo = '''    character_prompt = (
        "Small white-blue fox, golden eyes, pointed ears, "
        "short muzzle, four paws, fluffy tail. Full body, "
        "standing on all fours, centered on plain ivory "
        "background. Watercolor gouache storybook, "
        "textured paper, soft blue-violet colors."
    )'''

codigo_nuevo, cantidad = patron.subn(
    nuevo,
    codigo,
    count=1
)

if cantidad != 1:
    raise RuntimeError(
        "No se encontro la asignacion actual de character_prompt."
    )

# Comprobamos el prompt antes de modificar el archivo.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/dreamshaper-8/tokenizer",
    local_files_only=True
)

coincidencia = re.search(
    r'(?ms)^    character_prompt\s*=\s*\(\n(.*?)^    \)',
    codigo_nuevo
)

if not coincidencia:
    raise RuntimeError("No se pudo verificar el nuevo prompt.")

texto_prompt = coincidencia.group(1)

# Recuperamos las cadenas literales del bloque.
cadenas = re.findall(r'"([^"]*)"', texto_prompt)

prompt = "".join(cadenas)

tokens = len(
    tokenizer(prompt, truncation=False)["input_ids"]
)

print(f"Nuevo prompt de Luna: {tokens}/77 tokens")

if tokens > 70:
    raise RuntimeError(
        "El nuevo prompt sigue superando el limite preventivo."
    )

# Respaldo del archivo actual.
respaldo = Path(
    "docs/evidence/backups/visual_pilot_before_luna_prompt_v2.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

compile(
    codigo_nuevo,
    str(archivo),
    "exec"
)

archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("\nPrompt simplificado correctamente.")
print("Anatomia animal conservada.")
print("Fondo aprobado se mantiene.")
print("Respaldo:", respaldo)
