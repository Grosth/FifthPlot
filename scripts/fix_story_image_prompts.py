from pathlib import Path
import re

archivo = Path("src/fifthplot/generators/generate_story_images.py")
codigo = archivo.read_text(encoding="utf-8")

# Reducimos las descripciones que se repiten en todas las escenas.
codigo, n1 = re.subn(
    r'ART_STYLE\s*=\s*\(.*?\n\)',
    'ART_STYLE = "Watercolor storybook art, soft gouache brushstrokes, teal forest, warm colors."',
    codigo,
    count=1,
    flags=re.S
)

codigo, n2 = re.subn(
    r'LUMA_IDENTITY\s*=\s*\(.*?\n\)',
    'LUMA_IDENTITY = "Luma, small red-orange fox, golden eyes, tiny nose, fluffy fur, large curled comet tail."',
    codigo,
    count=1,
    flags=re.S
)

if n1 != 1 or n2 != 1:
    raise RuntimeError("No se encontraron las descripciones originales.")

# Solicitamos traducciones mas cortas.
codigo = codigo.replace(
    "- Cada descripcion debe tener como maximo 18 palabras.",
    "- Cada descripcion debe tener como maximo 10 palabras."
)

# Reemplazamos la validacion anterior por una version flexible.
inicio = codigo.index("def preparar_prompts(")
fin = codigo.index(
    "\n\n# 5. GENERAR LAS CINCO ILUSTRACIONES",
    inicio
)

nueva_funcion = '''
def preparar_prompts(traducciones):

    tokenizer = CLIPTokenizer.from_pretrained(
        str(TOKENIZER_DIR),
        local_files_only=True
    )

    prompts = []

    for item in traducciones:

        descripcion = item["description_en"].strip()

        prefijo = f"{ART_STYLE} {LUMA_IDENTITY} Scene:"
        prompt = f"{prefijo} {descripcion}"

        tokens = tokenizer(
            prompt,
            truncation=False
        )["input_ids"]

        reducciones = 0

        # Reducimos solamente la descripcion de la escena.
        # Nunca eliminamos la identidad de Luma ni el estilo.
        while len(tokens) > 77:

            tokens_escena = tokenizer(
                descripcion,
                add_special_tokens=False
            )["input_ids"]

            if len(tokens_escena) <= 4:
                raise ValueError(
                    f"No se pudo ajustar el prompt de la escena "
                    f"{item['number']}."
                )

            descripcion = tokenizer.decode(
                tokens_escena[:-2],
                skip_special_tokens=True
            ).strip()

            prompt = f"{prefijo} {descripcion}"

            tokens = tokenizer(
                prompt,
                truncation=False
            )["input_ids"]

            reducciones += 1

        item["description_en"] = descripcion

        print(
            f"Escena {item['number']}: "
            f"{len(tokens)}/77 tokens"
        )

        if reducciones:
            print(
                f"Descripcion ajustada: "
                f"{reducciones} reducciones."
            )

        prompts.append(prompt)

    cantidad_negativo = len(
        tokenizer(
            NEGATIVE_PROMPT,
            truncation=False
        )["input_ids"]
    )

    print(f"Prompt negativo: {cantidad_negativo}/77 tokens")

    if cantidad_negativo > 77:
        raise ValueError(
            "El prompt negativo supera el limite de CLIP."
        )

    return prompts

'''

codigo = codigo[:inicio] + nueva_funcion + codigo[fin:]

archivo.write_text(codigo, encoding="utf-8")

print("Generador de cinco ilustraciones corregido.")
print("Se conservaran la identidad de Luma y el estilo artistico.")
print("Los prompts se comprobaran antes de generar.")
