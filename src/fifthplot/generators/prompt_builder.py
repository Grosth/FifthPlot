import json
import re
import urllib.request
import urllib.error

from pathlib import Path
from transformers import CLIPTokenizer


MODEL = "qwen3:4b-q4_K_M"
OLLAMA_URL = "http://localhost:11434"

TOKENIZER_PATH = Path("models/dreamshaper-8/tokenizer")

STORIES = Path("outputs/stories")

OUTPUT = STORIES / "visual_prompts"

MAX_TOKENS = 70

NEGATIVE_PROMPT = (
    "text, watermark, logo, blurry, low quality, "
    "duplicate characters, extra limbs, distorted anatomy, "
    "photorealistic, 3d render."
)


def llamar_qwen(prompt, max_tokens=1800):

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.25,
            "num_predict": max_tokens,
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
            request,
            timeout=900
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.URLError as error:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Comprueba que Ollama este abierto."
        ) from error

    if data.get("error"):
        raise RuntimeError(data["error"])

    return data.get("response", "")


def extraer_json(texto):

    texto = texto.strip()

    inicio = texto.find("{")
    final = texto.rfind("}")

    if inicio == -1 or final == -1:
        raise ValueError("Qwen3 no devolvio un JSON reconocible.")

    return json.loads(texto[inicio:final + 1])


def contar_tokens(tokenizer, texto):

    return len(
        tokenizer(
            texto,
            truncation=False
        )["input_ids"]
    )


def obtener_historia():

    archivos = sorted(
        STORIES.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron historias en outputs/stories."
        )

    archivo = archivos[0]

    historia = json.loads(
        archivo.read_text(encoding="utf-8-sig")
    )

    if len(historia.get("scenes", [])) != 5:
        raise ValueError("La historia no tiene exactamente cinco escenas.")

    return archivo, historia


def construir_contexto(historia):

    personajes = {
        personaje["name"]: personaje
        for personaje in historia["characters"]
    }

    escenas = []

    for escena in historia["scenes"]:

        presentes = escena.get("characters_present", [])

        if not presentes:
            raise ValueError(
                f"La escena {escena.get('number')} no tiene personajes."
            )

        fichas = []

        for nombre in presentes:

            if nombre not in personajes:
                raise ValueError(
                    f"Personaje no encontrado: {nombre}"
                )

            personaje = personajes[nombre]

            fichas.append({
                "name": personaje["name"],
                "role": personaje.get("role", ""),
                "appearance": personaje.get("description", ""),
                "visual_reference": personaje.get("visual_prompt", "")
            })

        escenas.append({
            "number": escena["number"],
            "title": escena["scene_title"],
            "narrative": escena["narrative"],
            "visual_plan": escena.get("image_prompt", ""),
            "setting": escena.get("background_prompt", ""),
            "characters_present": presentes,
            "character_details": fichas
        })

    return {
        "title": historia["title"],
        "genre": historia["genre"],
        "synopsis": historia.get("synopsis", ""),
        "visual_style": historia.get("visual_style", ""),
        "scenes": escenas
    }


def generar_prompts(historia):

    contexto = construir_contexto(historia)

    instrucciones = f"""
You are the visual prompt designer for FifthPlot,
a local AI illustrated storybook generator.

Your task is to transform an existing five-scene story
into five detailed image generation prompts.

SOURCE STORY:
{json.dumps(contexto, ensure_ascii=False, indent=2)}

REQUIREMENTS:

1. Return exactly five scenes, numbered 1 to 5.

2. Write every image prompt in English.

3. Each prompt describes one complete illustration,
not a character isolated on a plain background.

4. Include the actual action happening in that scene.

5. Include the specific environment, composition,
camera framing, lighting and atmosphere.

6. Respect the physical appearance of every character.
Use the supplied character descriptions as the source
of truth for their identity.

7. Include every character listed in characters_present.
Do not omit characters or introduce new ones.

8. Keep the same artistic direction across all five images.
Use watercolor gouache children's storybook illustration,
textured paper and painterly details.

9. Each prompt should be concise but visually descriptive.
Aim for 40 to 55 words, preferably no more than 65 CLIP tokens.

10. Avoid text, subtitles, watermarks, split panels,
collages and image borders.

11. Do not change the original plot or invent new events.

OUTPUT JSON FORMAT:

{{
  "scenes": [
    {{
      "number": 1,
      "image_prompt": "Complete English visual prompt"
    }}
  ]
}}

Return only valid JSON.
"""

    respuesta = llamar_qwen(instrucciones)

    resultado = extraer_json(respuesta)

    escenas = resultado.get("scenes", [])

    if not isinstance(escenas, list) or len(escenas) != 5:
        raise ValueError(
            "Qwen3 no devolvio exactamente cinco prompts."
        )

    numeros = [int(e["number"]) for e in escenas]

    if sorted(numeros) != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"Numeracion incorrecta: {numeros}"
        )

    return sorted(
        escenas,
        key=lambda e: int(e["number"])
    )


def comprimir_prompts(tokenizer, escenas, contexto):

    excesos = [
        escena
        for escena in escenas
        if contar_tokens(
            tokenizer,
            escena["image_prompt"]
        ) > MAX_TOKENS
    ]

    if not excesos:
        return escenas

    print("\nOptimizando prompts que superan 70 tokens...")

    instrucciones = f"""
Rewrite only the following image prompts for CLIP
text encoder used by Stable Diffusion 1.5.

SOURCE CONTEXT:
{json.dumps(contexto, ensure_ascii=False)}

PROMPTS TO OPTIMIZE:
{json.dumps(excesos, ensure_ascii=False)}

Requirements:
- Preserve the scene action and all named characters.
- Preserve their defining physical features.
- Preserve the setting and important visual details.
- Keep the watercolor gouache storybook aesthetic.
- Remove redundant adjectives and unnecessary wording.
- Target 45 to 55 CLIP tokens per prompt.
- Write in English.

Return valid JSON with this structure:

{{
  "scenes": [
    {{
      "number": 1,
      "image_prompt": "Optimized prompt"
    }}
  ]
}}
"""

    respuesta = llamar_qwen(
        instrucciones,
        max_tokens=1200
    )

    corregidos = extraer_json(respuesta).get("scenes", [])

    mapa = {
        int(e["number"]): e["image_prompt"]
        for e in corregidos
    }

    for escena in escenas:

        numero = int(escena["number"])

        if numero in mapa:
            escena["image_prompt"] = mapa[numero]

    return escenas


def main():

    print("=" * 60)
    print("FIFTHPLOT - CONSTRUCTOR DE PROMPTS VISUALES")
    print("=" * 60)

    if not TOKENIZER_PATH.exists():
        raise FileNotFoundError(
            "No se encontro el tokenizer local de DreamShaper 8."
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("\nCargando tokenizer CLIP...")

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_PATH),
        local_files_only=True
    )

    archivo_historia, historia = obtener_historia()

    print("Historia:", historia["title"])
    print("Genero:", historia["genre"])
    print("Escenas:", len(historia["scenes"]))
    print("Modelo de texto:", MODEL)

    contexto = construir_contexto(historia)

    print("\nGenerando cinco prompts con Qwen3...")

    escenas = generar_prompts(historia)

    escenas = comprimir_prompts(
        tokenizer,
        escenas,
        contexto
    )

    resultados = []
    errores = []

    for escena in escenas:

        numero = int(escena["number"])
        prompt = escena["image_prompt"].strip()

        if not prompt:
            raise ValueError(
                f"El prompt de la escena {numero} esta vacio."
            )

        tokens = contar_tokens(tokenizer, prompt)

        if tokens > MAX_TOKENS:

            errores.append({
                "escena": numero,
                "tokens": tokens,
                "prompt": prompt
            })

        fuente = historia["scenes"][numero - 1]

        resultados.append({
            "number": numero,
            "scene_title": fuente["scene_title"],
            "narrative": fuente["narrative"],
            "characters_present": fuente["characters_present"],
            "image_prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "positive_tokens": tokens,
            "negative_tokens": contar_tokens(
                tokenizer,
                NEGATIVE_PROMPT
            )
        })

    if errores:

        print("\nPROMPTS QUE REQUIEREN REVISION:")

        for error in errores:
            print(
                f"Escena {error['escena']}: "
                f"{error['tokens']}/{MAX_TOKENS} tokens"
            )

        raise RuntimeError(
            "No se guardaron prompts fuera del limite."
        )

    resultado_final = {
        "project": "FifthPlot",
        "source_story": archivo_historia.name,
        "story_title": historia["title"],
        "model_text": MODEL,
        "model_image": "DreamShaper 8",
        "tokenizer": str(TOKENIZER_PATH),
        "max_positive_tokens": MAX_TOKENS,
        "visual_style": historia.get("visual_style", ""),
        "scenes": resultados
    }

    destino = (
        OUTPUT /
        f"{archivo_historia.stem}_visual_prompts.json"
    )

    destino.write_text(
        json.dumps(
            resultado_final,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    reporte = [
        "FIFTHPLOT - INFORME DE PROMPTS VISUALES",
        "=" * 60,
        f"Historia: {historia['title']}",
        f"Modelo: {MODEL}",
        "Modelo visual previsto: DreamShaper 8",
        f"Limite CLIP: {MAX_TOKENS} tokens",
        ""
    ]

    for escena in resultados:

        reporte.extend([
            "=" * 60,
            f"ESCENA {escena['number']}: {escena['scene_title']}",
            f"Personajes: {', '.join(escena['characters_present'])}",
            f"Tokens positivos: {escena['positive_tokens']}/77",
            f"Tokens negativos: {escena['negative_tokens']}/77",
            "",
            "PROMPT VISUAL:",
            escena["image_prompt"],
            "",
            "PROMPT NEGATIVO:",
            escena["negative_prompt"],
            ""
        ])

    print("\n" + "\n".join(reporte))

    report_dir = Path("docs/evidence/prompt_reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = (
        report_dir /
        f"{archivo_historia.stem}_prompt_report.txt"
    )

    report_path.write_text(
        "\n".join(reporte),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("PROMPTS VISUALES GENERADOS CORRECTAMENTE")
    print("Escenas:", len(resultados), "de 5")
    print("JSON:", destino)
    print("Informe:", report_path)
    print("=" * 60)


if __name__ == "__main__":
    main()
