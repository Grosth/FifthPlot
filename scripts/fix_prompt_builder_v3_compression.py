from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v3.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

inicio = codigo.find("def comprimir_acciones(")
final = codigo.find("\ndef main(", inicio)

if inicio == -1 or final == -1:
    raise RuntimeError(
        "No se encontraron los limites de comprimir_acciones."
    )

nueva_funcion = '''def comprimir_acciones(tokenizer, escenas, cues, participantes):

    style_tokens = contar_tokens(tokenizer, STYLE_SUFFIX)

    presupuesto = MAX_TOKENS - style_tokens - 5

    print(f"Tokens del estilo comun: {style_tokens}")
    print(f"Presupuesto recomendado para acciones: {presupuesto}")

    # Hasta tres rondas de optimizacion.
    for ronda in range(1, 4):

        excesos = []

        for escena in escenas:

            numero = int(escena["number"])

            prompt = construir_prompt(
                escena["visual_action"],
                participantes[numero],
                cues
            )

            cantidad = contar_tokens(tokenizer, prompt)

            if cantidad > MAX_TOKENS:

                detalles = []

                for nombre in participantes[numero]:

                    detalles.append({
                        "name": nombre,
                        "identity": cues[nombre]
                    })

                excesos.append({
                    "number": numero,
                    "current_tokens": cantidad,
                    "visual_action": escena["visual_action"],
                    "required_characters": detalles
                })

        if not excesos:

            print(
                f"Todas las escenas cumplen el limite "
                f"despues de {ronda - 1} rondas."
            )

            return escenas

        print(
            f"\\nRONDA DE COMPRESION {ronda}/3"
        )

        for escena in excesos:

            print(
                f"Escena {escena['number']}: "
                f"{escena['current_tokens']}/70 tokens"
            )

        instrucciones = f"""
You are editing visual prompts for DreamShaper 8,
a Stable Diffusion 1.5 image model.

Your task is to shorten ONLY the visual actions below.

SCENES TO OPTIMIZE:
{json.dumps(excesos, ensure_ascii=False, indent=2)}

COMMON ART STYLE:
{STYLE_SUFFIX}

HARD REQUIREMENTS:

1. Keep the original event and meaning.
2. Preserve every required character.
3. Preserve the essential physical identity of each character.
4. Keep the action and environment visually understandable.
5. Do not invent events, characters or objects.
6. Do not include artistic style in visual_action.
7. Use concise English visual descriptions.
8. Target approximately {presupuesto - 5} CLIP tokens
   for each visual_action.
9. Prefer concrete nouns and verbs over decorative adjectives.
10. Every character must have a clear visible role.

IMPORTANT:
The actual final prompt will append this common style:
{STYLE_SUFFIX}

The complete prompt, including that suffix, must fit
within 70 CLIP tokens.

RETURN ONLY THIS JSON FORMAT:

{{
  "scenes": [
    {{
      "number": 1,
      "visual_action": "Short complete visual action"
    }}
  ]
}}

Return every requested scene exactly once.
"""

        resultado = llamar_qwen(
            instrucciones,
            max_predict=1200
        )

        nuevas = resultado.get("scenes", [])

        if not isinstance(nuevas, list):
            raise ValueError(
                "Qwen3 no devolvio una lista de escenas."
            )

        numeros_esperados = {
            int(e["number"]) for e in excesos
        }

        mapa = {}

        for item in nuevas:

            numero = int(item["number"])

            if numero not in numeros_esperados:
                raise ValueError(
                    f"Qwen3 devolvio una escena no solicitada: {numero}"
                )

            if numero in mapa:
                raise ValueError(
                    f"Escena duplicada en la compresion: {numero}"
                )

            accion = item.get("visual_action", "").strip()

            if not accion:
                raise ValueError(
                    f"La accion de la escena {numero} esta vacia."
                )

            mapa[numero] = accion

        if set(mapa) != numeros_esperados:
            raise ValueError(
                "Qwen3 no devolvio todas las escenas solicitadas."
            )

        for escena in escenas:

            numero = int(escena["number"])

            if numero in mapa:
                escena["visual_action"] = mapa[numero]

                prompt = construir_prompt(
                    escena["visual_action"],
                    participantes[numero],
                    cues
                )

                cantidad = contar_tokens(tokenizer, prompt)

                print(
                    f"Escena {numero} despues de compresion: "
                    f"{cantidad}/70 tokens"
                )

    # Validacion final estricta.
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
                "escena": numero,
                "tokens": cantidad
            })

    if pendientes:

        raise RuntimeError(
            "No se pudieron ajustar todos los prompts "
            f"en tres rondas: {pendientes}"
        )

    print("\\nCompresion completada y validada.")
    return escenas


'''

codigo_nuevo = (
    codigo[:inicio]
    + nueva_funcion
    + codigo[final + 1:]
)

compile(codigo_nuevo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/prompt_builder_v3_before_iterative_compression.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("Compresor iterativo instalado.")
print("Maximo de rondas: 3.")
print("Validacion CLIP despues de cada ronda.")
print("Respaldo:", respaldo)

