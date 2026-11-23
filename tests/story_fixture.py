from fifthplot.domain import Story


def make_story() -> Story:
    return Story.model_validate(
        {
            "title": "La llave del bosque",
            "genre": "Fantasía",
            "synopsis": "Una zorra encuentra una llave y salva su bosque.",
            "visual_style": "Watercolor and gouache storybook illustration.",
            "characters": [
                {
                    "name": "Luma",
                    "description": "Una zorra naranja de ojos dorados.",
                    "role": "Protagonista",
                    "visual_prompt": (
                        "A small orange fox with golden eyes, white muzzle, "
                        "and a large curled tail."
                    ),
                }
            ],
            "scenes": [
                {
                    "number": i,
                    "scene_title": f"Escena {i}",
                    "narrative": f"Luma avanza por el bosque en la escena {i}.",
                    "image_prompt": f"Luma explores a forest path, scene {i}.",
                    "background_prompt": "An enchanted forest at twilight.",
                    "characters_present": ["Luma"],
                    "ambience_prompt": "Viento y hojas en un bosque nocturno.",
                    "voice_direction": "Voz tranquila y curiosa.",
                }
                for i in range(1, 6)
            ],
        }
    )
