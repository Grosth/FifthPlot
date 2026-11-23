from pathlib import Path
import re
import shutil

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v2.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")


# 1. Las firmas son referencias maestras, no se agregan
# completas a todos los prompts de imagen.

patron_funcion = re.compile(
    r"(?ms)^def construir_prompt\(core, participantes, firmas\):\n"
    r".*?(?=^def comprimir_escenas\()"
)

nueva_funcion = '''def construir_prompt(core, participantes, firmas):

    # Verificamos que todos los participantes tengan
    # una referencia visual registrada.
    faltantes = [
        nombre
        for nombre in participantes
        if not firmas.get(nombre)
    ]

    if faltantes:
        raise ValueError(
            f"Faltan referencias visuales: {faltantes}"
        )

    # El visual_core ya contiene la apariencia necesaria
    # de los personajes de esta escena.
    # Solo agregamos una vez el estilo artistico comun.
    return core.strip() + " " + STYLE_SUFFIX


'''

codigo_nuevo, cantidad = patron_funcion.subn(
    nueva_funcion,
    codigo,
    count=1
)

if cantidad != 1:
    raise RuntimeError(
        "No se pudo identificar la funcion construir_prompt. "
        "No se modifico el archivo."
    )


# 2. Eliminamos el limite artificial de 8 tokens
# para las firmas visuales.

patron_firmas = re.compile(
    r"(?ms)^    for nombre, firma in firmas\.items\(\):\n"
    r".*?^    escenas = resultado\.get\(\"scenes\", \[\]\)"
)

nuevo_bloque = '''    for nombre, firma in firmas.items():

        if not isinstance(firma, str) or not firma.strip():
            raise ValueError(
                f"La firma visual de {nombre} esta vacia."
            )

        cantidad = tokens(tokenizer, firma)

        print(
            f"Firma de personaje {nombre}: "
            f"{cantidad} tokens (referencia maestra)"
        )

    escenas = resultado.get("scenes", [])'''

codigo_nuevo, cantidad = patron_firmas.subn(
    nuevo_bloque,
    codigo_nuevo,
    count=1
)

if cantidad != 1:
    raise RuntimeError(
        "No se encontro la validacion de firmas visuales."
    )


# 3. Las descripciones de cada escena deben incluir
# los rasgos necesarios de todos sus participantes.

anterior = '''- Use 4 to 7 CLIP tokens per signature when possible.
- Describe species, distinctive colors and identifying features.
- Do not include background or artistic style.
- Never change a character's identity.'''

nuevo = '''- Create concise but useful physical identity references.
- Describe species, distinctive colors and identifying features.
- Character signatures are reference metadata, not complete
  image prompts.
- Each visual_core must include concise defining appearance
  cues for every character visible in that scene.
- Do not include background or artistic style in signatures.
- Never change a character's identity.'''

if codigo_nuevo.count(anterior) != 1:
    raise RuntimeError(
        "No se encontraron las instrucciones originales de firmas."
    )

codigo_nuevo = codigo_nuevo.replace(anterior, nuevo, 1)


# 4. Ajustamos la compresion para considerar el prompt completo.

codigo_nuevo = codigo_nuevo.replace(
    '''        "maximum_tokens_for_scene_core": 18
    }''',
    '''        "maximum_final_prompt_tokens": MAX_TOKENS,
        "style_suffix": STYLE_SUFFIX
    }''',
    1
)

codigo_nuevo = codigo_nuevo.replace(
    '''- Keep the watercolor gouache storybook aesthetic.
- Do not remove characters.
- Do not add artistic style.
- Do not include character appearance, since it is
  already supplied separately.

Return JSON:''',
    '''- Keep the watercolor gouache storybook aesthetic.
- Do not remove any character.
- Preserve concise defining physical features of all
  characters appearing in the scene.
- Preserve their actions, positions and narrative meaning.
- Do not add artistic style to visual_core.
- The final prompt plus style suffix must fit within
  70 CLIP tokens.

Return JSON:''',
    1
)


# 5. Verificamos sintaxis antes de escribir.

compile(
    codigo_nuevo,
    str(archivo),
    "exec"
)

respaldo = Path(
    "docs/evidence/backups/prompt_builder_v2_before_token_fix.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("Prompt Builder V2 corregido.")
print("Firmas visuales conservadas como referencias maestras.")
print("Prompts completos con presupuesto de 70 tokens.")
print("Respaldo:", respaldo)

