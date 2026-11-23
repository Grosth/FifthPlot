from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/visual_generation_pilot.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

anterior = '''STYLE = (
    "Watercolor gouache children's storybook illustration, "
    "textured paper, soft hand-painted brushstrokes, "
    "magical blue teal and violet palette, warm golden light."
)'''

nuevo = '''STYLE = (
    "Watercolor gouache storybook, textured paper, "
    "soft brushstrokes, blue-violet palette, warm golden light."
)'''

if codigo.count(anterior) != 1:
    raise RuntimeError(
        "No se encontro exactamente el estilo original. "
        "No se modifico el archivo."
    )

codigo_nuevo = codigo.replace(anterior, nuevo, 1)

compile(codigo_nuevo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/visual_pilot_before_style_fix.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("Estilo artistico optimizado.")
print("Se conserva la acuarela y el acabado de cuento.")
print("Respaldo:", respaldo)
