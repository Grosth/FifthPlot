import json
import urllib.request
import urllib.error

from pathlib import Path
from transformers import CLIPTokenizer


MODEL = "qwen3:4b-q4_K_M"
OLLAMA_URL = "http://localhost:11434"

TOKENIZER_PATH = Path("models/dreamshaper-8/tokenizer")

PLAN_DIR = Path("outputs/stories/visual_prompts")
STORY_DIR = Path("outputs/stories")

OUTPUT_DIR = PLAN_DIR
REPORT_DIR = Path("docs/evidence/prompt_reports")

MAX_TOKENS = 70
MAX_CORE_TOKENS = 30
MAX_SIGNATURE_TOKENS = 8

STYLE_SUFFIX = (
    "watercolor gouache storybook illustration, "
    "textured paper, soft painterly brushstrokes, "
    "blue violet silver palette, warm golden light."
)

NEGATIVE_PROMPT = (
    "text, watermark, logo, blurry, low quality, "
    "duplicate characters, extra limbs, distorted anatomy, "
    "photorealistic, 3d render."
)


def qwen(prompt, max_predict=1800):

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": max_predict,
            "num_ctx": 4096
        }
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(
            request, timeout=900
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.URLError as error:
        raise RuntimeError(
            "No fue posible conectar con Ollama."
        ) from error

    return json.loads(data["response"])


def tokens(tokenizer, text):

    return len(
        tokenizer(
            text,
            truncation=False
        )["input_ids"]
    )


def cargar_archivos():

    archivos = sorted(
        PLAN_DIR.glob("*_visual_prompts.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not archivos:
        raise FileNotFoundError(
            "No se encontro el plan visual original."
        )

    plan_path = archivos[0]

    plan = json.loads(
        plan_path.read_text(encoding="utf-8-sig")
    )

    historia_path = STORY_DIR / plan["source_story"]

    historia = json.loads(
        historia_path.read_text(encoding="utf-8-sig")
    )

    return plan_path, plan, historia


def preparar_contexto(plan, historia):

    personajes = []

    for personaje in historia["characters"]:

        personajes.append({
            "name": personaje["name"],
            "description": personaje["description"],
            "visual_reference": personaje.get(
                "visual_prompt", ""
            )
        })

    escenas = []

    for escena in plan["scenes"]:

        escenas.append({
            "number": escena["number"],
            "title": escena["scene_title"],
            "narrative": escena["narrative"],
            "characters_present": escena["characters_present"]
        })

    return {
        "title": historia["title"],
        "genre": historia["genre"],
        "synopsis": historia.get("synopsis", ""),
        "visual_style": historia.get("visual_style", ""),
        "characters": personajes,
        "scenes": escenas
    }


def generar_plan_visual(contexto):

    instrucciones = f"""
You are the visual director of FifthPlot,
a local AI illustrated storybook generator.

Create compact visual instructions for exactly five
complete illustrations using DreamShaper 8,
based on this story:

{json.dumps(contexto, ensure_ascii=False, indent=2)}

RETURN THIS JSON STRUCTURE:

{{
  "character_signatures": [
    {{
      "name": "Exact character name",
      "signature": "Compact physical appearance"
    }}
  ],
  "scenes": [
    {{
      "number": 1,
      "visual_core": "Scene action and environment"
    }}
  ]
}}

CHARACTER SIGNATURE RULES:

- Include every character in the supplied cast.
- Preserve their defining physical appearance.
- Create concise but useful physical identity references.
- Describe species, distinctive colors and identifying features.
- Character signatures are reference metadata, not complete
  image prompts.
- Each visual_core must include concise defining appearance
  cues for every character visible in that scene.
- Do not include background or artistic style in signatures.
- Never change a character's identity.

SCENE RULES:

- Return exactly five scenes numbered 1 to 5.
- Write all visual_core descriptions in English.
- Aim for 15 to 25 CLIP tokens per visual_core.
- Describe action, setting, composition and atmosphere.
- Include every character assigned to that scene.
- Follow the narrative, not just the character role.
- Do not invent characters or new plot events.
- All scenes must describe complete illustrations.
- For animal characters, use paws rather than human hands.
- A speaking tree that is not listed in the cast must remain
  an environmental element: glowing bark, moving branches
  and whispering leaves, without a face or eyes.
- Do not describe isolated characters on plain backgrounds.
- Do not include artistic style terms. The application
  will add the same artistic style to every final prompt.

The fifth scene must clearly stage all its assigned characters.

Return valid JSON only.
"""

    return qwen(instrucciones)


def construir_prompt(core, participantes, firmas):

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


def comprimir_escenas(tokenizer, escenas, firmas, participantes):

    excesos = []

    for escena in escenas:

        nombre_scene = int(escena["number"])

        prompt = construir_prompt(
            escena["visual_core"],
            participantes[nombre_scene],
            firmas
        )

        if tokens(tokenizer, prompt) > MAX_TOKENS:
            excesos.append(escena)

    if not excesos:
        return escenas

    print("\nComprimiendo escenas que exceden el limite...")

    solicitud = {
        "scenes_to_rewrite": excesos,
        "character_signatures": firmas,
        "maximum_final_prompt_tokens": MAX_TOKENS,
        "style_suffix": STYLE_SUFFIX
    }

    instrucciones = f"""
Shorten the visual_core of the following scenes.

{json.dumps(solicitud, ensure_ascii=False, indent=2)}

Keep:
- The main action.
- The essential environment.
- The characters' actions and positions.
- The narrative meaning.

Do not remove characters.
Do not add artistic style.
Do not include character appearance, since it is
already supplied separately.

Return JSON:

{{
  "scenes": [
    {{
      "number": 1,
      "visual_core": "Short scene description"
    }}
  ]
}}

Return only scenes that were supplied.
"""

    resultado = qwen(instrucciones, max_predict=700)

    nuevos = {
        int(item["number"]): item["visual_core"]
        for item in resultado["scenes"]
    }

    for escena in escenas:

        numero = int(escena["number"])

        if numero in nuevos:
            escena["visual_core"] = nuevos[numero]

    return escenas


def main():

    print("=" * 60)
    print("FIFTHPLOT - PROMPT BUILDER V2")
    print("=" * 60)

    if not TOKENIZER_PATH.exists():
        raise FileNotFoundError(
            "No se encontro el tokenizer de DreamShaper 8."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_PATH),
        local_files_only=True
    )

    plan_path, plan, historia = cargar_archivos()

    contexto = preparar_contexto(plan, historia)

    print("Historia:", historia["title"])
    print("Modelo textual:", MODEL)
    print("Modelo visual:", "DreamShaper 8")

    print("\nGenerando firmas de personajes y escenas...")

    resultado = generar_plan_visual(contexto)

    firmas_lista = resultado.get("character_signatures", [])

    firmas = {
        item["name"]: item["signature"].strip()
        for item in firmas_lista
    }

    nombres_reales = {
        p["name"] for p in historia["characters"]
    }

    if set(firmas) != nombres_reales:
        raise ValueError(
            "Las firmas visuales no coinciden con el reparto."
        )

    for nombre, firma in firmas.items():

        if not isinstance(firma, str) or not firma.strip():
            raise ValueError(
                f"La firma visual de {nombre} esta vacia."
            )

        cantidad = tokens(tokenizer, firma)

        print(
            f"Firma de personaje {nombre}: "
            f"{cantidad} tokens (referencia maestra)"
        )

    escenas = resultado.get("scenes", [])

    if len(escenas) != 5:
        raise ValueError(
            "El modelo no devolvio cinco escenas."
        )

    numeros = [int(e["number"]) for e in escenas]

    if sorted(numeros) != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"Numeracion incorrecta: {numeros}"
        )

    escenas.sort(key=lambda e: int(e["number"]))

    participantes = {
        int(e["number"]): e["characters_present"]
        for e in plan["scenes"]
    }

    # Validar el contenido antes de generar los prompts finales.
    for escena in escenas:

        numero = int(escena["number"])

        if not escena.get("visual_core", "").strip():
            raise ValueError(
                f"Escena {numero} sin contenido visual."
            )

        cantidad = tokens(
            tokenizer,
            escena["visual_core"]
        )

        print(f"Escena {numero} - contenido: {cantidad} tokens")

    escenas = comprimir_escenas(
        tokenizer,
        escenas,
        firmas,
        participantes
    )

    resultados = []
    errores = []

    print("\nCOMPROBACION DE PROMPTS FINALES")

    for escena in escenas:

        numero = int(escena["number"])

        prompt = construir_prompt(
            escena["visual_core"],
            participantes[numero],
            firmas
        )

        positivos = tokens(tokenizer, prompt)
        negativos = tokens(tokenizer, NEGATIVE_PROMPT)

        print(
            f"Escena {numero}: "
            f"{positivos}/70 positivos | "
            f"{negativos}/77 negativos"
        )

        if positivos > MAX_TOKENS:
            errores.append(numero)

        resultados.append({
            "number": numero,
            "scene_title": plan["scenes"][numero - 1]["scene_title"],
            "characters_present": participantes[numero],
            "visual_core": escena["visual_core"],
            "image_prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "positive_tokens": positivos,
            "negative_tokens": negativos
        })

    if errores:
        raise RuntimeError(
            f"Las siguientes escenas superan 70 tokens: {errores}. "
            "No se guardo el resultado."
        )

    documento = {
        "project": "FifthPlot",
        "version": "2.0",
        "source_story": plan["source_story"],
        "story_title": historia["title"],
        "model_text": MODEL,
        "model_image": "DreamShaper 8",
        "tokenizer": str(TOKENIZER_PATH),
        "max_positive_tokens": MAX_TOKENS,
        "visual_style_suffix": STYLE_SUFFIX,
        "character_signatures": firmas,
        "scenes": resultados
    }

    destino = (
        OUTPUT_DIR /
        f"{Path(plan['source_story']).stem}_visual_prompts_v2.json"
    )

    destino.write_text(
        json.dumps(documento, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    # Generar informe legible.
    lineas = [
        "FIFTHPLOT - INFORME DE PROMPTS VISUALES V2",
        "=" * 65,
        f"Historia: {historia['title']}",
        f"Modelo textual: {MODEL}",
        "Modelo visual: DreamShaper 8",
        f"Estilo comun: {STYLE_SUFFIX}",
        ""
    ]

    for nombre, firma in firmas.items():
        lineas.append(f"PERSONAJE: {nombre}")
        lineas.append(f"Firma: {firma}")
        lineas.append("")

    for escena in resultados:

        lineas.extend([
            "=" * 65,
            f"ESCENA {escena['number']}: {escena['scene_title']}",
            f"Personajes: {', '.join(escena['characters_present'])}",
            f"Tokens positivos: {escena['positive_tokens']}/77",
            "",
            "PROMPT COMPLETO:",
            escena["image_prompt"],
            "",
            "PROMPT NEGATIVO:",
            escena["negative_prompt"],
            ""
        ])

    informe = (
        REPORT_DIR /
        f"{Path(plan['source_story']).stem}_prompt_report_v2.txt"
    )

    informe.write_text(
        "\n".join(lineas),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("PROMPT BUILDER V2 COMPLETADO")
    print("Escenas:", len(resultados), "/ 5")
    print("JSON:", destino)
    print("Informe:", informe)
    print("=" * 60)


if __name__ == "__main__":
    main()
