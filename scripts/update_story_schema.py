from pathlib import Path
import shutil

archivo = Path("src/fifthplot/generators/story.py")

codigo = archivo.read_text(encoding="utf-8-sig")

def sustituir(texto, anterior, nuevo, etiqueta):
    cantidad = texto.count(anterior)
    if cantidad != 1:
        raise RuntimeError(
            f"No se pudo verificar el bloque: {etiqueta}. "
            f"Coincidencias encontradas: {cantidad}"
        )
    return texto.replace(anterior, nuevo, 1)


# 1. Añadir descripcion visual de cada personaje.
codigo = sustituir(
    codigo,
    '''                    "role": {"type": "string"}
                },
                "required": ["name", "description", "role"]''',
    '''                    "role": {"type": "string"},
                    "visual_prompt": {"type": "string"}
                },
                "required": [
                    "name", "description", "role", "visual_prompt"
                ]''',
    "Esquema de personajes"
)


# 2. Añadir participantes y fondo independiente por escena.
codigo = sustituir(
    codigo,
    '''                    "image_prompt": {"type": "string"},
                    "ambience_prompt": {"type": "string"},
                    "voice_direction": {"type": "string"}''',
    '''                    "image_prompt": {"type": "string"},
                    "background_prompt": {"type": "string"},
                    "characters_present": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "ambience_prompt": {"type": "string"},
                    "voice_direction": {"type": "string"}''',
    "Propiedades de escenas"
)


codigo = sustituir(
    codigo,
    '''                    "image_prompt",
                    "ambience_prompt",
                    "voice_direction"''',
    '''                    "image_prompt",
                    "background_prompt",
                    "characters_present",
                    "ambience_prompt",
                    "voice_direction"''',
    "Campos obligatorios de escenas"
)


# 3. Preparar validacion de personajes.
codigo = sustituir(
    codigo,
    '''    # Organizamos las escenas del 1 al 5.
    escenas = sorted(
        escenas,
        key=lambda escena: int(escena["number"])
    )

    for numero, escena in enumerate(escenas, start=1):''',
    '''    # Comprobamos el reparto general.
    personajes = historia.get("characters", [])

    if not isinstance(personajes, list) or not personajes:
        raise ValueError("La historia no tiene personajes validos.")

    nombres_validos = {}

    for personaje in personajes:
        if not isinstance(personaje, dict):
            raise ValueError("La estructura de un personaje no es valida.")

        for campo in ["name", "description", "role", "visual_prompt"]:
            valor = personaje.get(campo, "")
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"El personaje tiene el campo {campo} vacio."
                )

        clave = personaje["name"].strip().casefold()

        if clave in nombres_validos:
            raise ValueError("Hay nombres de personajes duplicados.")

        nombres_validos[clave] = personaje["name"].strip()

    # Organizamos las escenas del 1 al 5.
    escenas = sorted(
        escenas,
        key=lambda escena: int(escena["number"])
    )

    for numero, escena in enumerate(escenas, start=1):''',
    "Validacion del reparto"
)


# 4. Validar los personajes participantes y los prompts.
codigo = sustituir(
    codigo,
    '''        for campo in campos:
            valor = escena.get(campo, "")

            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"La escena {numero} tiene el campo {campo} vacio."
                )

    historia["scenes"] = escenas''',
    '''        for campo in campos:
            valor = escena.get(campo, "")

            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"La escena {numero} tiene el campo {campo} vacio."
                )

        presentes = escena.get("characters_present")

        if not isinstance(presentes, list) or not presentes:
            raise ValueError(
                f"La escena {numero} no tiene personajes asignados."
            )

        nombres_normalizados = []

        for nombre in presentes:
            if not isinstance(nombre, str):
                raise ValueError(
                    f"Nombre de personaje invalido en escena {numero}."
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

    historia["scenes"] = escenas''',
    "Validacion de participantes"
)


# 5. Actualizar las instrucciones de Qwen3.
codigo = sustituir(
    codigo,
    '''    - Los prompts de imagen deben describir claramente
      los personajes, el lugar y la accion.
    - Los prompts de sonido describen solo el ambiente.''',
    '''    - Cada personaje debe incluir un visual_prompt en ingles.
    - El visual_prompt describe un personaje de cuerpo completo,
      con rasgos fisicos estables y fondo neutro.
    - Cada escena debe incluir characters_present.
    - Los nombres de characters_present deben coincidir exactamente
      con los nombres definidos en el reparto.
    - Cada escena debe incluir background_prompt en ingles.
    - background_prompt describe unicamente el escenario,
      iluminacion, paisaje y objetos; nunca personajes, animales
      ni figuras humanas.
    - image_prompt describe la accion visual completa de la escena.
    - Mantiene la identidad y apariencia de los personajes
      a lo largo de las cinco escenas.
    - Los prompts de sonido describen solo el ambiente.''',
    "Instrucciones del sistema"
)


# 6. Actualizar la estructura solicitada al modelo.
codigo = sustituir(
    codigo,
    '''    - Personajes con descripciones fisicas estables
    - Exactamente cinco escenas

    Cada escena debe incluir:
    - Numero
    - Titulo
    - Texto narrativo
    - Prompt para generar la ilustracion
    - Descripcion de la ambientacion sonora
    - Direccion de voz para la narracion''',
    '''    - Personajes con descripciones fisicas estables
    - visual_prompt en ingles para cada personaje
    - Exactamente cinco escenas

    Cada escena debe incluir:
    - Numero
    - Titulo
    - Texto narrativo
    - image_prompt con la accion visual
    - background_prompt en ingles, sin personajes
    - characters_present con los nombres exactos del reparto
    - Descripcion de la ambientacion sonora
    - Direccion de voz para la narracion''',
    "Estructura solicitada"
)


# Verificacion final antes de modificar el original.
compilacion = compile(codigo, str(archivo), "exec")

# Respaldo del archivo anterior.
respaldo = Path(
    "docs/evidence/backups/story_before_scene_planning.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

shutil.copy2(archivo, respaldo)

archivo.write_text(codigo, encoding="utf-8")

print("Esquema narrativo actualizado correctamente.")
print("Respaldo:", respaldo)
print("Campos nuevos:")
print("- visual_prompt")
print("- background_prompt")
print("- characters_present")
print("Validacion de participantes activada.")
