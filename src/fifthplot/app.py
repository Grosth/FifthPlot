"""Interfaz Gradio de FifthPlot."""

from pathlib import Path
from threading import Lock

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from fifthplot.pipeline import StorybookPipeline
from fifthplot.story_engine import OllamaStoryGenerator


_PIPELINE = StorybookPipeline(OllamaStoryGenerator())
_GENERATION_LOCK = Lock()


def _generate(
    idea: str,
    genre: str,
    strategy: str,
    progress=gr.Progress(),
):
    if not idea or not idea.strip() or not genre or not genre.strip():
        raise gr.Error("Escribe una idea y un género para continuar.")
    if not _GENERATION_LOCK.acquire(blocking=False):
        raise gr.Error("Ya hay otro cuento generándose. Espera a que termine.")
    try:
        result = _PIPELINE.generate(
            idea,
            genre,
            progress=lambda status: progress(0, desc=status),
            strategy=strategy,
        )
    except Exception as exc:
        raise gr.Error(str(exc)) from exc
    finally:
        _GENERATION_LOCK.release()

    story = result["story"]
    folder = Path(result["folder"])
    cards = []
    for scene in story.scenes:
        scene_dir = folder / f"scene_{scene.number:02d}"
        cards.append(
            {
                "number": scene.number,
                "title": scene.scene_title,
                "narrative": scene.narrative,
                "image": str(folder / f"scene_{scene.number:02d}.png"),
                "voice": str(scene_dir / "narration.wav"),
                "ambience": str(scene_dir / "ambience.wav"),
            }
        )
    return (
        f"# {story.title}\n\n{story.synopsis}",
        cards,
        str(folder),
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="FifthPlot") as demo:
        gr.Markdown("# FifthPlot\nCrea un cuento ilustrado de cinco escenas.")
        with gr.Row():
            idea = gr.Textbox(
                label="Idea inicial",
                placeholder="Una exploradora encuentra una puerta bajo el hielo...",
                lines=3,
            )
            genre = gr.Dropdown(
                choices=[
                    "Fantasía",
                    "Misterio",
                    "Aventura",
                    "Ciencia ficción",
                    "Terror",
                    "Infantil",
                ],
                label="Género",
                value="Fantasía",
                allow_custom_value=True,
            )
        strategy = gr.Dropdown(
            choices=[
                ("IP-Adapter (referencia visual)", "ip_adapter"),
                ("Solo texto (menor uso de RAM)", "text_only"),
            ],
            label="Estrategia de ilustración",
            value="text_only",
        )
        create = gr.Button("Generar cuento", variant="primary")
        title = gr.Markdown()
        scenes = gr.State([])
        output_dir = gr.Textbox(label="Carpeta del cuento", interactive=False)
        with gr.Row():
            previous = gr.Button("← Escena anterior")
            position = gr.Number(value=1, label="Escena", precision=0)
            next_scene = gr.Button("Escena siguiente →")
            scene_counter = gr.Markdown("0 / 5")
        with gr.Row():
            illustration = gr.Image(label="Ilustración", interactive=False)
            narrative = gr.Textbox(label="Narración", lines=8, interactive=False)
        with gr.Row():
            voice = gr.Audio(label="Voz", interactive=False)
            ambience = gr.Audio(label="Ambiente", interactive=False)

        def show_scene(scene_list, number):
            if not scene_list:
                return None, "", None, None, 1, "0 / 5"
            index = max(0, min(4, int(number or 1) - 1))
            item = scene_list[index]
            return (
                item["image"],
                f"**{item['number']}. {item['title']}**\n\n{item['narrative']}",
                item["voice"],
                item["ambience"],
                item["number"],
                f"{item['number']} / 5",
            )

        create.click(
            _generate,
            inputs=[idea, genre, strategy],
            outputs=[title, scenes, output_dir],
        ).then(
            show_scene,
            inputs=[scenes, position],
            outputs=[illustration, narrative, voice, ambience, position, scene_counter],
        )
        previous.click(
            lambda value: max(1, int(value or 1) - 1),
            inputs=position,
            outputs=position,
        ).then(
            show_scene,
            inputs=[scenes, position],
            outputs=[illustration, narrative, voice, ambience, position, scene_counter],
        )
        next_scene.click(
            lambda value: min(5, int(value or 1) + 1),
            inputs=position,
            outputs=position,
        ).then(
            show_scene,
            inputs=[scenes, position],
            outputs=[illustration, narrative, voice, ambience, position, scene_counter],
        )
    return demo


def launch() -> None:
    build_ui().queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        share=False,
        inbrowser=True,
    )
