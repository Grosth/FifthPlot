"""Interfaz Gradio de FifthPlot."""

from pathlib import Path
from threading import Lock

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from fifthplot.pipeline import StorybookPipeline
from fifthplot.story_engine import OllamaStoryGenerator
from fifthplot.ui.layout import APP_CSS, kitsune_brand_markup


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


def _photo_placeholder() -> str:
    return """
    <section class="fp-entry-card fp-photo-card" aria-disabled="true">
      <span class="fp-entry-icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="7" width="31" height="29" rx="4" fill="#FFFDF8" stroke="#9A7546" stroke-width="2.4"/>
          <circle cx="27" cy="15" r="3.4" fill="#E8B257"/>
          <path d="m9 31 8-9 6 6 4-4 6 7H9Z" fill="#A4AD7A"/>
          <path d="m32 39 9-18 3 2-8 18-4 2v-4Z" fill="#E86C24" stroke="#9A7546" stroke-width="1.4" stroke-linejoin="round"/>
        </svg>
      </span>
      <h3>Dibujo o foto</h3>
      <p>Una imagen para inspirar tu cuento.</p>
      <span class="fp-coming-soon">Próximamente</span>
    </section>
    """


def _voice_placeholder() -> str:
    return """
    <section class="fp-entry-card fp-voice-card" aria-disabled="true">
      <span class="fp-entry-icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="18" y="6" width="12" height="24" rx="6" fill="#F2A04D" stroke="#A65A25" stroke-width="2"/>
          <path d="M12 23a12 12 0 0 0 24 0M24 36v6m-8 0h16M9 15l-3 3m33-3 3 3M12 10l-2-3m28 3 2-3" stroke="#A65A25" stroke-width="2.4" stroke-linecap="round"/>
        </svg>
      </span>
      <h3>Dictado por voz</h3>
      <p>Cuéntanos tu idea hablando.</p>
      <span class="fp-coming-soon">Próximamente</span>
    </section>
    """


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="FifthPlot") as demo:
        with gr.Column(elem_classes=["fp-app", "fp-shell"]):
            with gr.Row(elem_classes=["fp-header"], equal_height=True):
                gr.HTML(kitsune_brand_markup(), elem_classes=["fp-brand-lockup-wrap"])
                with gr.Row(elem_classes=["fp-header-nav"]):
                    create_nav = gr.Button(
                        "Crear cuento",
                        variant="secondary",
                        elem_classes=["fp-nav-current"],
                    )
                    gr.Button(
                        "Mis cuentos · Próximamente",
                        variant="secondary",
                        interactive=False,
                        elem_classes=["fp-nav-future"],
                    )

            with gr.Column(elem_classes=["fp-view", "fp-input-view"]) as input_view:
                gr.Markdown(
                    "## Crea tu cuento local\n"
                    "Convierte tus ideas en un cuento ilustrado de cinco escenas.",
                    elem_classes=["fp-section-heading"],
                )
                with gr.Row(equal_height=True, elem_classes=["fp-entry-options"]):
                    with gr.Column(scale=1, min_width=200):
                        gr.HTML(_photo_placeholder())
                    with gr.Column(scale=1, min_width=200):
                        gr.HTML(_voice_placeholder())
                    with gr.Column(scale=1, min_width=260):
                        with gr.Column(elem_classes=["fp-entry-card", "fp-writing-card"]):
                            gr.HTML(
                                '<span class="fp-entry-icon" aria-hidden="true">'
                                '<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">'
                                '<path d="M9 6h21l9 9v27H9V6Z" fill="#FFFDF8" stroke="#9A7546" stroke-width="2.3" stroke-linejoin="round"/>'
                                '<path d="M29 6v10h10M15 23h16M15 29h12" stroke="#9A7546" stroke-width="2" stroke-linecap="round"/>'
                                '<path d="m27 35 12-12 4 4-12 12-6 2 2-6Z" fill="#E86C24" stroke="#9A7546" stroke-width="1.5" stroke-linejoin="round"/>'
                                '</svg></span>'
                                '<h3>Idea por escrito</h3>'
                                '<p>Escribe aquí de qué trata tu cuento.</p>',
                                elem_classes=["fp-writing-heading"],
                            )
                            idea = gr.Textbox(
                                label="Tu idea",
                                placeholder=(
                                    "Una aventura en el bosque de mi pueblo…"
                                ),
                                lines=4,
                                max_lines=5,
                                elem_classes=["fp-idea-input"],
                            )
                with gr.Row(elem_classes=["fp-story-settings"]):
                    with gr.Column(elem_classes=["fp-setting-field"]):
                        gr.Markdown(
                            "Género del cuento",
                            elem_classes=["fp-setting-label"],
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
                            label="",
                            show_label=False,
                            value="Fantasía",
                            allow_custom_value=True,
                        )
                    with gr.Column(elem_classes=["fp-setting-field"]):
                        gr.Markdown(
                            "Estrategia de ilustración",
                            elem_classes=["fp-setting-label"],
                        )
                        strategy = gr.Dropdown(
                            choices=[
                                ("Solo texto · menor uso de RAM", "text_only"),
                                ("IP-Adapter · referencia visual", "ip_adapter"),
                            ],
                            label="",
                            show_label=False,
                            value="text_only",
                        )
                with gr.Accordion(
                    "Opciones de generación",
                    open=False,
                    elem_classes=["fp-accordion"],
                ):
                    gr.Markdown(
                        "La estrategia controla cómo se crean las ilustraciones. "
                        "La cámara y la entrada por voz todavía no están conectadas."
                    )
                gr.Markdown(
                    "Por ahora, puedes crear tu cuento escribiendo una idea.",
                    elem_classes=["fp-availability-note"],
                )
                create = gr.Button(
                    "✦  Crear mi cuento",
                    variant="primary",
                    elem_classes=["fp-primary-button"],
                )

            with gr.Column(
                visible=False,
                elem_classes=["fp-view", "fp-story-view"],
            ) as story_view:
                title = gr.Markdown(elem_classes=["fp-story-title"])
                position = gr.Number(value=1, precision=0, visible=False)
                scene_counter = gr.Markdown("Escena 1 de 5", elem_classes=["fp-scene-counter"])

                with gr.Row(
                    equal_height=True,
                    elem_classes=["fp-story-layout"],
                ):
                    illustration = gr.Image(
                        label="Ilustración de la escena",
                        interactive=False,
                        elem_classes=["fp-illustration"],
                    )
                    with gr.Column(elem_classes=["fp-story-copy"]):
                        narrative = gr.Markdown(elem_classes=["fp-narrative"])
                with gr.Row(elem_classes=["fp-reading-controls"]):
                    previous = gr.Button("← Anterior", variant="secondary")
                    voice = gr.Audio(
                        label="Escuchar narración",
                        interactive=False,
                        elem_classes=["fp-audio-player"],
                    )
                    gr.Button(
                        "Más lento · Próximamente",
                        interactive=False,
                        variant="secondary",
                    )
                    next_scene = gr.Button("Siguiente →", variant="secondary")
                gr.Button(
                    "Otra historia",
                    variant="primary",
                    elem_classes=["fp-new-story-button"],
                ).click(
                    lambda: (
                        gr.update(visible=True),
                        gr.update(visible=False),
                    ),
                    outputs=[input_view, story_view],
                )

                with gr.Accordion(
                    "Ambiente y archivos del cuento",
                    open=False,
                    elem_classes=["fp-accordion"],
                ):
                    ambience = gr.Audio(
                        label="Ambiente de la escena",
                        interactive=False,
                    )
                    output_dir = gr.Textbox(
                        label="Carpeta del cuento",
                        interactive=False,
                    )

            scenes = gr.State([])

        def show_scene(scene_list, number):
            if not scene_list:
                return None, "", None, None, 1, "Escena 1 de 5"
            index = max(0, min(4, int(number or 1) - 1))
            item = scene_list[index]
            progress = " ".join(
                "●" if scene == item["number"] else "○" for scene in range(1, 6)
            )
            return (
                item["image"],
                f"### {item['number']}. {item['title']}\n\n{item['narrative']}",
                item["voice"],
                item["ambience"],
                item["number"],
                f"**Escena {item['number']} de 5**　<span class='fp-progress-dots'>{progress}</span>",
            )

        create.click(
            _generate,
            inputs=[idea, genre, strategy],
            outputs=[title, scenes, output_dir],
        ).then(
            show_scene,
            inputs=[scenes, position],
            outputs=[illustration, narrative, voice, ambience, position, scene_counter],
        ).then(
            lambda: (gr.update(visible=False), gr.update(visible=True)),
            outputs=[input_view, story_view],
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
        create_nav.click(
            lambda: (gr.update(visible=True), gr.update(visible=False)),
            outputs=[input_view, story_view],
        )
    return demo


def launch() -> None:
    build_ui().queue(default_concurrency_limit=1).launch(
        css=APP_CSS,
        theme=gr.themes.Soft(
            primary_hue="orange",
            secondary_hue="amber",
            neutral_hue="stone",
            radius_size="lg",
        ),
        server_name="127.0.0.1",
        share=False,
        inbrowser=True,
    )
