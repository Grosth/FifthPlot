from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/visual_generation_pilot.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

anterior_prompt = '''    character_prompt = (
        luna["visual_prompt"] + " " + STYLE
    )'''

nuevo_prompt = '''    character_prompt = (
        "Small quadruped white and pale blue fox, four paws, "
        "pointed fox ears, short fox muzzle, golden eyes, "
        "large bushy tail. Walking on all fours, full body, "
        "natural animal anatomy, centered, isolated on plain "
        "ivory background. " + STYLE
    )'''

anterior_negative = '''NEGATIVE_CHARACTER = (
    "multiple characters, multiple animals, cropped, "
    "out of frame, extra legs, extra ears, text, watermark, "
    "photorealistic, 3d render, blurry."
)'''

nuevo_negative = '''NEGATIVE_CHARACTER = (
    "human, woman, girl, humanoid, princess, elf, person, "
    "hands, arms, dress, robe, cloak, upright body, "
    "multiple animals, extra legs, extra heads, cropped, "
    "text, watermark, photorealistic, 3d render, blurry."
)'''

if codigo.count(anterior_prompt) != 1:
    raise RuntimeError("No se encontro el prompt original de Luna.")

if codigo.count(anterior_negative) != 1:
    raise RuntimeError("No se encontro el prompt negativo original.")

codigo_nuevo = codigo.replace(
    anterior_prompt,
    nuevo_prompt,
    1
)

codigo_nuevo = codigo_nuevo.replace(
    anterior_negative,
    nuevo_negative,
    1
)

# Evitamos generar nuevamente el fondo ya aprobado.
anterior_fondo = '''    background_result = generate(
        pipe,
        background_prompt,
        NEGATIVE_BACKGROUND,
        8152,
        "scene_01_background.png"
    )'''

nuevo_fondo = '''    background_path = OUTPUT / "scene_01_background.png"

    if background_path.exists():
        print("\\nReutilizando fondo aprobado de escena 1.")
        background_result = {
            "archivo": str(background_path),
            "reutilizado": True
        }
    else:
        background_result = generate(
            pipe,
            background_prompt,
            NEGATIVE_BACKGROUND,
            8152,
            "scene_01_background.png"
        )'''

if codigo_nuevo.count(anterior_fondo) != 1:
    raise RuntimeError("No se encontro el bloque original del fondo.")

codigo_nuevo = codigo_nuevo.replace(
    anterior_fondo,
    nuevo_fondo,
    1
)

compile(codigo_nuevo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/visual_pilot_before_fox_fix.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("Prompt de Luna corregido.")
print("Se reforzo la anatomia de zorro.")
print("Se reutilizara el fondo ya generado.")
print("Respaldo:", respaldo)
