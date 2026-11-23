from pathlib import Path
import shutil

archivo = Path("src/fifthplot/generators/story.py")
codigo = archivo.read_text(encoding="utf-8-sig")

anterior = '''    # Revisamos la numeracion de las escenas.
    try:
        numeros = [int(escena["number"]) for escena in escenas]
    except (KeyError, TypeError, ValueError):
        raise ValueError("La numeracion de las escenas no es valida.")

    if sorted(numeros) != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"Numeracion incorrecta. Se recibio: {numeros}"
        )

    # Organizamos las escenas del 1 al 5.
    escenas = sorted(
        escenas,
        key=lambda escena: int(escena["number"])
    )
'''

nuevo = '''    # Corregimos automaticamente la numeracion.
    # Si los numeros son unicos y correctos, respetamos ese orden.
    # Si hay duplicados, conservamos el orden narrativo del JSON.
    try:
        numeros = [int(escena["number"]) for escena in escenas]
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
            "Se conservara el orden narrativo y se normalizaran "
            "las escenas del 1 al 5."
        )

    if not all(isinstance(escena, dict) for escena in escenas):
        raise ValueError("Una o mas escenas tienen formato incorrecto.")
'''

if codigo.count(anterior) != 1:
    raise RuntimeError(
        "No se encontro exactamente el bloque de numeracion esperado. "
        "No se modifico story.py."
    )

# Agregamos una instruccion adicional para Qwen3.
instruccion = "    - Genera exactamente cinco escenas."

refuerzo = (
    "    - Genera exactamente cinco escenas.\n"
    "    - Numera las escenas en orden consecutivo: 1, 2, 3, 4 y 5.\n"
    "    - Nunca repitas ni omitas numeros de escena.\n"
    "    - El orden del arreglo scenes debe coincidir con el orden narrativo."
)

if codigo.count(instruccion) != 1:
    raise RuntimeError(
        "No se encontro la instruccion de cantidad de escenas."
    )

codigo_nuevo = codigo.replace(anterior, nuevo, 1)
codigo_nuevo = codigo_nuevo.replace(instruccion, refuerzo, 1)

compile(codigo_nuevo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/story_before_number_normalization.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(archivo, respaldo)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("Normalizacion de escenas activada.")
print("Numeracion automatica: 1, 2, 3, 4 y 5.")
print("Instrucciones de Qwen3 reforzadas.")
print("Respaldo:", respaldo)
