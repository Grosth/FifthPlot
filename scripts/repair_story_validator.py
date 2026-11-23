from pathlib import Path
import shutil

archivo = Path("src/fifthplot/generators/story.py")
codigo = archivo.read_text(encoding="utf-8-sig")

inicio = codigo.find("def validar_historia(historia):")
final = codigo.find("\ndef generar_historia(", inicio)

if inicio == -1 or final == -1:
    raise RuntimeError(
        "No se encontraron los limites de validar_historia()."
    )

nueva_funcion = '''def validar_historia(historia):

    if not isinstance(historia, dict):
        raise ValueError("La historia debe ser un objeto JSON.")

    # Validamos el reparto.
    personajes = historia.get("characters", [])

    if not isinstance(personajes, list) or not personajes:
        raise ValueError("La historia no tiene personajes validos.")

    nombres_validos = {}

    for personaje in personajes:

        if not isinstance(personaje, dict):
            raise ValueError("Un personaje tiene formato incorrecto.")

        campos_personaje = [
            "name",
            "description",
            "role",
            "visual_prompt"
        ]

        for campo in campos_personaje:

            valor = personaje.get(campo, "")

            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"Un personaje tiene el campo {campo} vacio."
                )

        clave = personaje["name"].strip().casefold()

        if clave in nombres_validos:
            raise ValueError("Hay nombres de personajes duplicados.")

        nombres_validos[clave] = personaje["name"].strip()

    # Validamos las cinco escenas.
    escenas = historia.get("scenes", [])

    if not isinstance(escenas, list) or len(escenas) != 5:
        raise ValueError(
            f"Se esperaban 5 escenas y llegaron {len(escenas) if isinstance(escenas, list) else 0}."
        )

    if not all(isinstance(escena, dict) for escena in escenas):
        raise ValueError("Una o mas escenas tienen formato incorrecto.")

    # Conservamos el orden narrativo si hay numeros duplicados.
    try:
        numeros = [int(escena["number"]) for escena in escenas]
    except (KeyError, TypeError, ValueError):
        numeros = []

    if sorted(numeros) == [1, 2, 3, 4, 5]:

        escenas = sorted(
            escenas,
            key=lambda escena: int(escena["number"])
        )

    else:

        print(
            f"Advertencia: numeracion recibida {numeros}. "
            "Se conservara el orden original de las cinco escenas."
        )

    campos_escena = [
        "scene_title",
        "narrative",
        "image_prompt",
        "background_prompt",
        "ambience_prompt",
        "voice_direction"
    ]

    for numero, escena in enumerate(escenas, start=1):

        escena["number"] = numero

        for campo in campos_escena:

            valor = escena.get(campo, "")

            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"La escena {numero} tiene el campo {campo} vacio."
                )

        # Comprobamos los personajes que aparecen.
        presentes = escena.get("characters_present")

        if not isinstance(presentes, list):
            raise ValueError(
                f"La escena {numero} no tiene una lista de personajes."
            )

        nombres_normalizados = []

        for nombre in presentes:

            if not isinstance(nombre, str):
                raise ValueError(
                    f"Nombre de personaje incorrecto en escena {numero}."
                )

            clave = nombre.strip().casefold()

            if clave not in nombres_validos:
                raise ValueError(
                    f"El personaje '{nombre}' de la escena {numero} "
                    "no existe en el reparto."
                )

            nombre_canonico = nombres_validos[clave]

            if nombre_canonico not in nombres_normalizados:
                nombres_normalizados.append(nombre_canonico)

        escena["characters_present"] = nombres_normalizados

    historia["scenes"] = escenas

    return historia


'''

codigo_nuevo = (
    codigo[:inicio]
    + nueva_funcion
    + codigo[final + 1:]
)

# Verificamos sintaxis antes de escribir.
compile(codigo_nuevo, str(archivo), "exec")

# Creamos respaldo.
respaldo = Path(
    "docs/evidence/backups/story_before_validator_repair.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(codigo_nuevo, encoding="utf-8")

print("Validador narrativo reconstruido correctamente.")
print("Variable nombres_validos restaurada.")
print("Validacion de cinco escenas activada.")
print("Respaldo:", respaldo)
