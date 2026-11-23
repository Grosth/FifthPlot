from pathlib import Path
import shutil

archivo = Path("src/fifthplot/generators/story.py")
codigo = archivo.read_text(encoding="utf-8-sig")

anterior = "    - Los prompts de sonido describen solo el ambiente."

reglas = """    - Los prompts de sonido describen solo el ambiente.
    - Todo personaje, criatura, aliado o antagonista visible debe
      estar definido previamente en el reparto.
    - Toda entidad visible en una escena debe incluirse en
      characters_present y tener su propia descripcion visual.
    - characters_present debe coincidir exactamente con los
      personajes que aparecen en image_prompt.
    - image_prompt debe describir a todos los personajes indicados.
    - background_prompt describe exclusivamente escenarios,
      paisajes, iluminacion, arquitectura y objetos.
    - Nunca incluir personas, animales, criaturas, siluetas,
      figuras ni personajes en background_prompt.
    - visual_prompt describe solamente un personaje de cuerpo
      completo, centrado y aislado.
    - Utilizar un fondo marfil uniforme, sin decoraciones,
      patrones, paisajes, estrellas ni otros personajes.
    - Todos los visual_prompt deben estar escritos en ingles.
"""

if codigo.count(anterior) != 1:
    raise RuntimeError(
        "No se encontro exactamente una vez el bloque de instrucciones."
    )

respaldo = Path(
    "docs/evidence/backups/story_before_prompt_refinement.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

shutil.copy2(archivo, respaldo)

codigo = codigo.replace(anterior, reglas, 1)

compile(codigo, str(archivo), "exec")

archivo.write_text(codigo, encoding="utf-8")

print("Instrucciones visuales actualizadas.")
print("Respaldo guardado:", respaldo)
print("Validacion de codigo: correcta.")
