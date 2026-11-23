from pathlib import Path
import shutil

archivo = Path("src/fifthplot/generators/story.py")
codigo = archivo.read_text(encoding="utf-8-sig")

inicio = "    # Revisamos la numeracion de las escenas."
final = "    for numero, escena in enumerate(escenas, start=1):"

if codigo.count(inicio) != 1:
    raise RuntimeError(
        "No se encontro un unico inicio de validacion. "
        "No se modifico story.py."
    )

pos_inicio = codigo.index(inicio)
pos_final = codigo.find(final, pos_inicio)

if pos_final == -1:
    raise RuntimeError(
        "No se encontro el final de la validacion. "
        "No se modifico story.py."
    )

nuevo_bloque = '''    # Normalizamos la numeracion sin perder el orden narrativo.
    try:
        numeros = [
            int(escena["number"])
            for escena in escenas
        ]
    except (KeyError, TypeError, ValueError):
        numeros = []

    if sorted(numeros) == [1, 2, 3, 4, 5]:
        escenas = sorted(
            escenas,
            key=lambda escena: int(escena["number"])
        )
    else:
        print(
            f"Advertencia: numeracion recibida {numeros}. "
            "Se conservara el orden original de las cinco escenas."
        )

'''

codigo_nuevo = (
    codigo[:pos_inicio]
    + nuevo_bloque
    + codigo[pos_final:]
)

# Verificar sintaxis antes de guardar.
compile(codigo_nuevo, str(archivo), "exec")

# Crear respaldo sin sobrescribirlo.
respaldo = Path(
    "docs/evidence/backups/story_before_number_fix_v2.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("Normalizacion de escenas instalada correctamente.")
print("Orden narrativo conservado cuando hay numeros duplicados.")
print("Respaldo:", respaldo)

