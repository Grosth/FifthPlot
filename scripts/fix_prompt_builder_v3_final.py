from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v3.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

# 1. Desactivar el razonamiento en las solicitudes a Ollama.
anterior = '        "format": "json",'

nuevo = (
    '        "format": "json",\n'
    '        "think": False,'
)

if codigo.count(anterior) != 1:
    raise RuntimeError(
        "No se encontro el campo format en la solicitud Ollama."
    )

codigo = codigo.replace(anterior, nuevo, 1)


# 2. Eliminar la consulta secundaria para comprimir firmas.
inicio = codigo.find("def comprimir_firmas(")
final = codigo.find("\ndef construir_prompt(", inicio)

if inicio == -1 or final == -1:
    raise RuntimeError(
        "No se encontro la funcion comprimir_firmas."
    )

nueva_funcion = '''def comprimir_firmas(tokenizer, cues):

    # Las firmas son metadatos de identidad.
    # No requieren otra consulta a Qwen ni limite CLIP.

    for nombre, cue in cues.items():

        if not isinstance(cue, str) or not cue.strip():
            raise ValueError(
                f"La referencia visual de {nombre} esta vacia."
            )

        cantidad = contar_tokens(tokenizer, cue)

        print(
            f"Referencia {nombre}: {cantidad} tokens "
            "(metadato conservado)."
        )

    print("No se requieren consultas adicionales para las firmas.")

    return cues


'''

codigo = (
    codigo[:inicio]
    + nueva_funcion
    + codigo[final + 1:]
)


# 3. Verificacion de sintaxis.
compile(codigo, str(archivo), "exec")

# 4. Crear respaldo.
respaldo = Path(
    "docs/evidence/backups/prompt_builder_v3_before_think_fix.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo, encoding="utf-8")

print("\nPrompt Builder actualizado.")
print("Razonamiento de Qwen3 desactivado.")
print("Consulta secundaria de firmas eliminada.")
print("Firmas visuales conservadas.")
print("Compilacion correcta.")
print("Respaldo:", respaldo)

