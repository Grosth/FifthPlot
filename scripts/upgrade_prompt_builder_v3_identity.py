from pathlib import Path
import shutil
import re

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v3.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")


def reemplazar_funcion(texto, nombre, siguiente, nueva):

    inicio = texto.find(f"def {nombre}(")
    final = texto.find(f"\ndef {siguiente}(", inicio)

    if inicio == -1 or final == -1:
        raise RuntimeError(
            f"No se encontraron los limites de {nombre}."
        )

    return texto[:inicio] + nueva.strip() + "\n\n" + texto[final + 1:]


# Estilo comun mas compacto.
codigo, cantidad = re.subn(
    r"(?ms)^STYLE_SUFFIX\s*=\s*\(\n.*?^\)",
    '''STYLE_SUFFIX = (
    "watercolor gouache storybook, textured paper, "
    "soft blue-violet brushstrokes, golden accents."
)''',
    codigo,
    count=1
)

if cantidad != 1:
    raise RuntimeError("No se encontro STYLE_SUFFIX.")


# 1. Compactar las identidades mediante Qwen3.
nueva_firma = '''
def comprimir_firmas(tokenizer, cues):

    instrucciones = f"""
Create very compact visual identity cues
for these story characters:

{json.dumps(cues, ensure_ascii=False, indent=2)}

Requirements:
- Preserve each character's species or physical material.
- Preserve the most distinctive color and feature.
- Maximum 8 CLIP tokens per identity.
- Use short English descriptions.
- Do not include artistic style or background.
- Never change identities.

Return JSON:
{{
  "character_cues": [
    {{"name": "Exact character name", "cue": "Short identity"}}
  ]
}}

Return every character exactly once.
"""

    resultado = llamar_qwen(
        instrucciones,
        max_predict=600
    )

    nuevos = {
        item["name"]: item["cue"].strip()
        for item in resultado.get("character_cues", [])
    }

    if set(nuevos) != set(cues):
        raise ValueError(
            "Las identidades compactas no coinciden con el reparto."
        )

    for nombre, cue in nuevos.items():

        cantidad = contar_tokens(tokenizer, cue)

        print(f"Identidad {nombre}: {cantidad} tokens")

        if cantidad > MAX_CUE_TOKENS:
            raise ValueError(
                f"Identidad de {nombre} supera 8 tokens."
            )

    return nuevos

'''

codigo = reemplazar_funcion(
    codigo,
    "comprimir_firmas",
    "construir_prompt",
    nueva_firma
)


# 2. Incorporar las identidades de los personajes
# al prompt que realmente recibe DreamShaper.
nuevo_prompt = '''
def construir_prompt(action, participantes, cues):

    faltantes = [
        nombre for nombre in participantes
        if nombre not in cues
    ]

    if faltantes:
        raise ValueError(
            f"Faltan identidades: {faltantes}"
        )

    identidades = "; ".join(
        cues[nombre]
        for nombre in participantes
    )

    return (
        identidades
        + ". "
        + action.strip()
        + ". "
        + STYLE_SUFFIX
    )

'''

codigo = reemplazar_funcion(
    codigo,
    "construir_prompt",
    "comprimir_acciones",
    nuevo_prompt
)


# 3. Revisar semanticamente las cinco acciones y
# comprobar el presupuesto real de tokens.
nueva_compresion = '''
def comprimir_acciones(tokenizer, escenas, cues, participantes):

    solicitud = []

    for escena in escenas:

        numero = int(escena["number"])

        solicitud.append({
            "number": numero,
            "title": escena.get("title", ""),
            "visual_action": escena["visual_action"],
            "characters_present": participantes[numero],
            "character_identities": {
                nombre: cues[nombre]
                for nombre in participantes[numero]
            }
        })

    instrucciones = f"""
You are revising five visual actions for a children's storybook.

SCENES:
{json.dumps(solicitud, ensure_ascii=False, indent=2)}

Rules:
- Preserve the original narrative events.
- Every listed character must appear visibly.
- Do not introduce any identifiable character not listed.
- Environmental shadows must not have faces or glowing eyes
  unless the shadow character is listed.
- Use the supplied physical identity cues.
- Every animal remains an animal with natural anatomy.
- Give each character a clear action or position.
- Describe the environment and composition.
- Keep each action concise.
- Do not include artistic style in visual_action.
- Write in English.

Return all five scenes in JSON:

{{
  "scenes": [
    {{
      "number": 1,
      "visual_action": "Concise complete scene action"
    }}
  ]
}}
"""

    resultado = llamar_qwen(
        instrucciones,
        max_predict=1200
    )

    nuevos = {
        int(item["number"]): item["visual_action"].strip()
        for item in resultado.get("scenes", [])
    }

    if set(nuevos) != {1, 2, 3, 4, 5}:
        raise ValueError(
            "Qwen3 no devolvio las cinco acciones revisadas."
        )

    for escena in escenas:
        numero = int(escena["number"])
        escena["visual_action"] = nuevos[numero]

    # Comprimir solamente los prompts que superen 70 tokens.
    for ronda in range(1, 4):

        pendientes = []

        for escena in escenas:

            numero = int(escena["number"])

            prompt = construir_prompt(
                escena["visual_action"],
                participantes[numero],
                cues
            )

            cantidad = contar_tokens(tokenizer, prompt)

            if cantidad > MAX_TOKENS:
                pendientes.append({
                    "number": numero,
                    "visual_action": escena["visual_action"],
                    "characters": {
                        nombre: cues[nombre]
                        for nombre in participantes[numero]
                    },
                    "tokens_actuales": cantidad
                })

        if not pendientes:
            print(
                f"Todas las escenas cumplen el limite "
                f"despues de {ronda - 1} rondas."
            )
            return escenas

        print(f"Compresion de acciones: ronda {ronda}/3")

        instrucciones = f"""
Shorten these scene actions for DreamShaper 8.

{json.dumps(pendientes, ensure_ascii=False, indent=2)}

Requirements:
- Preserve every character and identity cue.
- Preserve the main action and environment.
- Preserve character positions and interaction.
- Never invent new characters or actions.
- Keep the common artistic style outside the action.
- Each complete prompt including identities and style
  must be no longer than 70 CLIP tokens.

Return JSON:
{{
  "scenes": [
    {{"number": 1, "visual_action": "Short action"}}
  ]
}}
"""

        resultado = llamar_qwen(
            instrucciones,
            max_predict=900
        )

        nuevos = {
            int(item["number"]): item["visual_action"].strip()
            for item in resultado.get("scenes", [])
        }

        if set(nuevos) != {
            int(e["number"]) for e in pendientes
        }:
            raise ValueError(
                "Respuesta incompleta durante la compresion."
            )

        for escena in escenas:

            numero = int(escena["number"])

            if numero in nuevos:
                escena["visual_action"] = nuevos[numero]

    # Validacion estricta final.
    for escena in escenas:

        numero = int(escena["number"])

        prompt = construir_prompt(
            escena["visual_action"],
            participantes[numero],
            cues
        )

        cantidad = contar_tokens(tokenizer, prompt)

        if cantidad > MAX_TOKENS:
            raise RuntimeError(
                f"Escena {numero}: {cantidad}/70 tokens."
            )

    return escenas

'''

codigo = reemplazar_funcion(
    codigo,
    "comprimir_acciones",
    "main",
    nueva_compresion
)


# 4. Validacion final.
compile(codigo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/prompt_builder_v3_before_identity_injection.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

# Guardar copia del resultado anterior.
for anterior_json in Path("outputs/stories/visual_prompts").glob(
    "*_visual_prompts_v3.json"
):
    copia = respaldo.parent / (
        anterior_json.stem + "_before_identity_injection.json"
    )

    if not copia.exists():
        shutil.copy2(anterior_json, copia)

archivo.write_text(codigo, encoding="utf-8")

print("Prompt Builder V3.1 actualizado.")
print("Identidades integradas en cada prompt.")
print("Acciones revisadas para coherencia narrativa.")
print("Limite CLIP: 70 tokens.")
print("Respaldo:", respaldo)

