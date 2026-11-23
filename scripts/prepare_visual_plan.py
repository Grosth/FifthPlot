import json
import shutil
from pathlib import Path

DIRECTORY = Path("outputs/stories")
BACKUPS = Path("docs/evidence/backups")

CHARACTERS = {
    "Luna": {
        "role": "Protagonista",
        "visual_prompt": (
            "Full body small white and pale blue fox, bright golden "
            "eyes, soft flowing tail, delicate shimmering silver blue "
            "cloak, curious gentle expression, centered, isolated on "
            "plain warm ivory background, watercolor gouache storybook."
        )
    },
    "El Titán del Amanecer": {
        "role": "Guía",
        "visual_prompt": (
            "Full body colossal humanoid guardian, weathered stone "
            "face, glowing amber eyes, long powerful stone arms, "
            "subtle magical runes, flowing veil of dawn light, "
            "centered, isolated on plain warm ivory background, "
            "watercolor gouache storybook."
        )
    },
    "La Sombra del Anochecer": {
        "role": "Antagonista",
        "visual_prompt": (
            "Single mysterious shadow entity formed from flowing "
            "black mist, one recognizable central silhouette, two "
            "subtle crimson glowing eyes, curling wisps of darkness, "
            "centered, isolated on plain warm ivory background, "
            "watercolor gouache storybook."
        )
    },
    "El Jardinero de Estrellas": {
        "role": "Aliado",
        "visual_prompt": (
            "Full body elderly celestial gardener, kind luminous "
            "face, midnight blue cloak embroidered with tiny silver "
            "stars, sparkling diamond collar, silver eyes, holding "
            "a small cluster of glowing stars, centered, isolated "
            "on plain warm ivory background, watercolor gouache storybook."
        )
    }
}

SCENES = [
    {
        "characters": ["Luna"],
        "background": (
            "Enchanted ancient forest at night, tall slender trees, "
            "winding path, completely starless violet blue sky, "
            "soft silver moonlight, quiet mysterious atmosphere, "
            "empty foreground, watercolor gouache storybook landscape."
        ),
        "image": (
            "Luna, a small white and blue fox wearing a shimmering "
            "cloak, stands on a forest path looking upward at the "
            "empty starless sky, curious and worried. Wide cinematic composition."
        )
    },
    {
        "characters": ["Luna"],
        "background": (
            "Dense magical forest with a gigantic ancient tree, "
            "twisted roots, tall whispering branches, dark teal leaves, "
            "misty winding path and cold blue violet light, "
            "open foreground, watercolor gouache landscape."
        ),
        "image": (
            "Luna approaches a gigantic ancient tree and gently "
            "touches its textured trunk, listening to its mysterious "
            "whispers. The forest feels alive around her."
        )
    },
    {
        "characters": [
            "Luna",
            "El Titán del Amanecer"
        ],
        "background": (
            "Desolate celestial plateau beneath a dark violet sky, "
            "ancient broken stone pillars, rocky ground, distant "
            "mountain silhouettes, subtle golden light and blue mist, "
            "open foreground, watercolor gouache landscape."
        ),
        "image": (
            "Luna faces the enormous stone Titan of Dawn on a "
            "mysterious rocky plateau. The small fox looks upward "
            "as the colossal guardian reveals the secret of the "
            "missing stars. Both characters clearly visible."
        )
    },
    {
        "characters": [
            "Luna",
            "La Sombra del Anochecer"
        ],
        "background": (
            "Dark enchanted forest clearing, twisted bare trees, "
            "swirling ribbons of magical darkness, scattered distant "
            "silver lights, deep violet and teal atmosphere, "
            "open central foreground, watercolor gouache landscape."
        ),
        "image": (
            "Luna confronts the mysterious shadow entity in a dark "
            "forest clearing. The small fox stands bravely before "
            "the flowing black silhouette with glowing red eyes, "
            "while tiny stars begin to escape the darkness."
        )
    },
    {
        "characters": [
            "Luna",
            "El Jardinero de Estrellas",
            "El Titán del Amanecer",
            "La Sombra del Anochecer"
        ],
        "background": (
            "Magical celestial garden in a forest clearing, "
            "countless silver stars returning to a brilliant blue "
            "and violet sky, glowing flowers, golden dawn light, "
            "luminous peaceful atmosphere, watercolor gouache landscape."
        ),
        "image": (
            "Luna and the elderly Star Gardener restore the stars "
            "together in a magical forest clearing. The Titan watches "
            "from the distance while the shadow entity dissolves "
            "into the returning light. Four characters clearly staged."
        )
    }
]


def main():

    archivos = sorted(
        DIRECTORY.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not archivos:
        raise FileNotFoundError("No hay historias JSON.")

    archivo = archivos[0]

    historia = json.loads(
        archivo.read_text(encoding="utf-8-sig")
    )

    if len(historia.get("scenes", [])) != 5:
        raise ValueError("La historia debe tener exactamente cinco escenas.")

    personajes = {
        p["name"]: p
        for p in historia.get("characters", [])
    }

    if set(personajes) != set(CHARACTERS):
        raise ValueError(
            "El reparto del JSON no coincide con el plan visual. "
            f"Encontrados: {list(personajes)}"
        )

    # Respaldo de la historia antes de modificarla.
    BACKUPS.mkdir(parents=True, exist_ok=True)

    backup = BACKUPS / f"{archivo.stem}_before_visual_plan.json"

    if not backup.exists():
        shutil.copy2(archivo, backup)

    historia["visual_style"] = (
        "Ilustracion de cuento infantil en acuarela y gouache, "
        "papel texturizado, pinceladas suaves, tonos azul, violeta "
        "y plata con acentos dorados, iluminacion magica, "
        "continuidad artistica entre las cinco escenas."
    )

    # Actualizar referencias visuales del reparto.
    for nombre, configuracion in CHARACTERS.items():

        personaje = personajes[nombre]

        personaje["role"] = configuracion["role"]
        personaje["visual_prompt"] = configuracion["visual_prompt"]

    # Actualizar los cinco planes visuales.
    for escena, plan in zip(historia["scenes"], SCENES):

        escena["background_prompt"] = plan["background"]
        escena["image_prompt"] = plan["image"]
        escena["characters_present"] = plan["characters"]

    historia["visual_plan_version"] = "1.0"

    # Verificacion final.
    for index, escena in enumerate(historia["scenes"]):

        if len(escena["characters_present"]) == 0:
            raise ValueError(f"Escena {index + 1} sin personajes.")

        for nombre in escena["characters_present"]:
            if nombre not in personajes:
                raise ValueError(
                    f"Personaje desconocido en escena {index + 1}: {nombre}"
                )

        if not escena["background_prompt"].strip():
            raise ValueError(f"Fondo vacio en escena {index + 1}.")

    archivo.write_text(
        json.dumps(historia, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    print("=" * 55)
    print("FIFTHPLOT - PLAN VISUAL PREPARADO")
    print("=" * 55)
    print("Historia:", historia["title"])
    print("Personajes:", len(personajes))
    print("Escenas:", len(historia["scenes"]))
    print("Respaldo:", backup)
    print("Archivo actualizado:", archivo)

    for escena in historia["scenes"]:
        print(
            f"\nEscena {escena['number']}: {escena['scene_title']}"
        )
        print("Personajes:", ", ".join(escena["characters_present"]))
        print("Fondo:", escena["background_prompt"][:100], "...")

    print("\nPLAN VISUAL VALIDADO CORRECTAMENTE.")


if __name__ == "__main__":
    main()
