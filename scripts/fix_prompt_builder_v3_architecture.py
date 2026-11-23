from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v3.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")


def reemplazar_funcion(texto, nombre, siguiente, nueva):

    inicio = texto.find(f"def {nombre}(")

    final = texto.find(
        f"\ndef {siguiente}(",
        inicio
    )

    if inicio == -1 or final == -1:
        raise RuntimeError(
            f"No se encontraron los limites de {nombre}."
        )

    return texto[:inicio] + nueva.rstrip() + "\n\n" + texto[final + 1:]


# 1. Las firmas quedan como metadatos.
nueva_firma = '''
def comprimir_firmas(tokenizer, cues):

    for nombre, cue in cues.items():

        if not isinstance(cue, str) or not cue.strip():
            raise ValueError(
                f"La referencia visual de {nombre} esta vacia."
            )

        print(
            f"Referencia {nombre}: "
            f"{contar_tokens(tokenizer, cue)} tokens "
            "(metadato, no enviado a CLIP)"
        )

    return cues

'''

codigo = reemplazar_funcion(
    codigo,
    "comprimir_firmas",
    "construir_prompt",
    nueva_firma
)


# 2. El prompt final contiene la accion y el estilo,
# no las firmas completas de los personajes.
nuevo_prompt = '''
def construir_prompt(action, participantes, cues):

    faltantes = [
        nombre for nombre in participantes
        if not cues.get(nombre)
    ]

    if faltantes:
        raise ValueError(
            f"Faltan referencias visuales: {faltantes}"
        )

    return action.strip() + " " + STYLE_SUFFIX

'''

codigo = reemplazar_funcion(
    codigo,
    "construir_prompt",
    "comprimir_acciones",
    nuevo_prompt
)


# 3. Actualizar las instrucciones de identidad.
anterior = (
    "- Use no more than 8 CLIP tokens per cue.\n"
    "- Be specific, not generic."
)

nuevo = (
    "- Character cues are detailed reference metadata.\n"
    "- They are not appended to the final CLIP prompt.\n"
    "- Preserve species, distinctive colors and identity.\n"
    "- Be specific, not generic."
)

if codigo.count(anterior) != 1:
    raise RuntimeError("No se encontro el bloque de identidad.")

codigo = codigo.replace(anterior, nuevo, 1)


# 4. Exigir rasgos fisicos dentro de las acciones.
anterior = "- Aim for 15 to 25 CLIP tokens per action."

nuevo = (
    "- Aim for 25 to 40 CLIP tokens per action when possible.\n"
    "- Include compact physical identity cues for every visible "
    "character directly in visual_action.\n"
    "- The final prompt, including artistic style, must fit "
    "within 70 CLIP tokens."
)

if codigo.count(anterior) != 1:
    raise RuntimeError("No se encontro el limite de acciones.")

codigo = codigo.replace(anterior, nuevo, 1)


# 5. Aumentar el presupuesto de la consulta de compresion.
anterior = "        max_predict=700"
if codigo.count(anterior) != 1:
    raise RuntimeError("No se encontro el presupuesto de compresion.")

codigo = codigo.replace(
    anterior,
    "        max_predict=1200",
    1
)


# 6. Eliminar el rechazo de firmas largas.
inicio = codigo.find("    # Verificar las identidades compactas.")
final = codigo.find("    # Verificar acciones narrativas.", inicio)

if inicio == -1 or final == -1:
    raise RuntimeError("No se encontro la validacion de identidades.")

nuevo_bloque = '''    # Las firmas son metadatos de referencia.
    # No se aplica un limite CLIP a estas descripciones.
    cues = comprimir_firmas(tokenizer, cues)

'''

codigo = codigo[:inicio] + nuevo_bloque + codigo[final:]


# 7. Compilar antes de guardar.
compile(codigo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/prompt_builder_v3_before_architecture_fix.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo, encoding="utf-8")

print("Arquitectura de Prompt Builder V3 actualizada.")
print("Firmas: metadatos independientes.")
print("Acciones: incorporan rasgos fisicos.")
print("Prompts finales: maximo 70 tokens.")
print("Compilacion: correcta.")
print("Respaldo:", respaldo)

