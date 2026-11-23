from fifthplot.generators.story import validar_historia

personaje = {
    "name": "Luma",
    "description": "Una zorrita naranja.",
    "role": "Protagonista",
    "visual_prompt": "A small orange fox, full body."
}

def escena(numero, titulo):
    return {
        "number": numero,
        "scene_title": titulo,
        "narrative": "Luma continua su aventura.",
        "image_prompt": "Luma walking through a forest.",
        "background_prompt": "An enchanted forest without characters.",
        "characters_present": ["Luma"],
        "ambience_prompt": "Soft forest wind.",
        "voice_direction": "Gentle and curious."
    }

prueba = {
    "characters": [personaje],
    "scenes": [
        escena(1, "Inicio"),
        escena(2, "Viaje"),
        escena(1, "Descubrimiento"),
        escena(4, "Conflicto"),
        escena(5, "Final")
    ]
}

resultado = validar_historia(prueba)

numeros = [s["number"] for s in resultado["scenes"]]

assert numeros == [1, 2, 3, 4, 5]
assert resultado["scenes"][2]["scene_title"] == "Descubrimiento"

print("\nPRUEBA DE NUMERACION SUPERADA")
print("Numeracion:", numeros)
print("Orden narrativo conservado.")
