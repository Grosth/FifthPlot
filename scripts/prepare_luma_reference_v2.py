from pathlib import Path
import re
from transformers import CLIPTokenizer

archivo = Path("src/fifthplot/generators/images.py")
codigo = archivo.read_text(encoding="utf-8")

prompt = """Watercolor storybook art of Luma, a small red orange fox with golden eyes, tiny nose, fluffy messy fur and a large curled comet tail. Full body, all paws visible, standing in a teal enchanted forest. Soft moonlight, painterly gouache, visible brushstrokes, warm fur and cool blue green background."""

negative = """cropped, hidden tail, extra limbs, extra ears, duplicate fox, other animals, blurry, text, watermark, photorealistic, 3d, plastic texture."""

# Comprobamos los tokens antes de modificar el archivo.
tokenizer = CLIPTokenizer.from_pretrained(
    "models/stable-diffusion-v1-5/tokenizer",
    local_files_only=True
)

for nombre, texto in [
    ("Positivo", prompt),
    ("Negativo", negative)
]:
    cantidad = len(
        tokenizer(texto, truncation=False)["input_ids"]
    )
    print(f"Prompt {nombre}: {cantidad}/77 tokens")

    if cantidad > 77:
        raise RuntimeError(f"El prompt {nombre} supera el limite.")

# Actualizamos los dos prompts.
for nombre, valor in [
    ("PROMPT", prompt),
    ("NEGATIVE_PROMPT", negative)
]:
    patron = rf'^{nombre}\s*=\s*""".*?"""'

    codigo, cantidad = re.subn(
        patron,
        lambda _: f'{nombre} = """{valor}"""',
        codigo,
        count=1,
        flags=re.M | re.S
    )

    if cantidad != 1:
        raise RuntimeError(f"No se encontro {nombre}.")

# Usamos nombres nuevos para conservar las pruebas anteriores.
codigo = codigo.replace(
    '"luma_referencia.png"',
    '"luma_referencia_v2.png"'
)
codigo = codigo.replace(
    '"luma_referencia.json"',
    '"luma_referencia_v2.json"'
)

archivo.write_text(codigo, encoding="utf-8")

print("\nNueva configuracion guardada correctamente.")
print("Archivo de salida: luma_referencia_v2.png")
