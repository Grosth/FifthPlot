"""Orquestación de los componentes de generación."""

import json
import ctypes
import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from typing import Callable

from fifthplot.audio_engine import PiperNarrator, ProceduralAmbience
from fifthplot.domain import StoryRequest
from fifthplot.image_engine import DiffusersIllustrator
from fifthplot.prompt_builder import MASTER_VISUAL_STYLE_PROMPT, VISUAL_PROMPT_POLICY
from fifthplot.storage import StoryStorage


class StorybookPipeline:
    def __init__(
        self,
        story_generator,
        illustrator=None,
        narrator=None,
        ambience=None,
        storage=None,
    ) -> None:
        self.story_generator = story_generator
        self.illustrator = illustrator or DiffusersIllustrator()
        self.narrator = narrator or PiperNarrator()
        self.ambience = ambience or ProceduralAmbience()
        self.storage = storage or StoryStorage()

    def generate(
        self,
        idea: str,
        genre: str,
        progress: Callable[[str], None] | None = None,
        strategy: str = "ip_adapter",
    ) -> dict:
        request = StoryRequest(idea=idea, genre=genre)
        request_started = perf_counter()
        story = self.story_generator.generate(request)
        story_id, folder = self.storage.create_story_dir(story.title)
        start = perf_counter()
        manifest = {
            "story_id": story_id,
            "status": "generating",
            "story_title": story.title,
            "genre": story.genre,
            "strategy": strategy,
            "models": {
                "narrative": getattr(
                    self.story_generator, "model", type(self.story_generator).__name__
                ),
                "image": getattr(
                    getattr(self.illustrator, "model_dir", None),
                    "name",
                    type(self.illustrator).__name__,
                ),
                "image_adapter": (
                    "IP-Adapter Plus SD15" if strategy == "ip_adapter" else None
                ),
                "voice": getattr(
                    getattr(self.narrator, "model_path", None),
                    "name",
                    type(self.narrator).__name__,
                ),
                "ambience": "ProceduralAmbience",
            },
            "parameters": {
                "story_generation_seconds": round(perf_counter() - request_started, 2),
                "scene_count": 5,
                "image_strategy": strategy,
                "visual_prompt_policy": VISUAL_PROMPT_POLICY,
                "visual_style_prompt": MASTER_VISUAL_STYLE_PROMPT,
                "image_size": getattr(self.illustrator, "size", None),
                "image_steps": getattr(self.illustrator, "steps", None),
                "image_guidance_scale": getattr(self.illustrator, "guidance", None),
                "ip_adapter_scale": getattr(
                    self.illustrator, "adapter_scale", None
                ),
            },
            "environment": _environment_info(),
            "scenes": [],
        }
        self.storage.write_story(folder, story)
        self.storage.write_json(folder / "manifest.json", manifest)
        if progress:
            progress("Ilustrando las cinco escenas...")
        try:
            images = self.illustrator.generate_story(
                story,
                folder,
                strategy=strategy,
                progress=(
                    lambda number, total, title: progress(
                        f"Generando ilustración {number} de {total}: {title}"
                    )
                    if progress
                    else None
                ),
            )
            for scene, image_path in zip(story.scenes, images, strict=True):
                scene_dir = folder / f"scene_{scene.number:02d}"
                scene_dir.mkdir(exist_ok=True)
                voice_started = perf_counter()
                voice_path = self.narrator.synthesize(
                    scene.narrative, scene_dir / "narration.wav"
                )
                voice_seconds = round(perf_counter() - voice_started, 2)
                ambience_started = perf_counter()
                ambience_path = self.ambience.synthesize(
                    scene.ambience_prompt,
                    scene_dir / "ambience.wav",
                    scene.number,
                )
                ambience_seconds = round(perf_counter() - ambience_started, 2)
                manifest["scenes"].append(
                    {
                        "number": scene.number,
                        "image": str(Path(image_path).relative_to(folder)),
                        "narration": str(Path(voice_path).relative_to(folder)),
                        "ambience": str(Path(ambience_path).relative_to(folder)),
                        "narration_seconds": voice_seconds,
                        "ambience_seconds": ambience_seconds,
                        "narrative_characters": len(scene.narrative),
                    }
                )
                self.storage.write_json(folder / "manifest.json", manifest)
                if progress:
                    progress(f"Escena {scene.number} de 5 lista.")
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            manifest["elapsed_seconds"] = round(perf_counter() - start, 2)
            manifest["parameters"]["image_runs"] = getattr(
                self.illustrator, "last_run", []
            )
            self.storage.write_json(folder / "manifest.json", manifest)
            raise
        manifest["parameters"]["image_runs"] = getattr(
            self.illustrator, "last_run", []
        )
        voice_model = getattr(self.narrator, "model_path", None)
        manifest["parameters"]["narration_voice"] = (
            str(voice_model) if voice_model is not None else None
        )
        manifest["environment"]["gpu"] = getattr(
            self.illustrator, "gpu_name", None
        )
        manifest["environment"].update(
            _environment_info(manifest["environment"]["gpu"])
        )
        manifest["parameters"]["ambience_sample_rate"] = getattr(
            self.ambience, "sample_rate", None
        )
        manifest["parameters"]["ambience_duration_seconds"] = getattr(
            self.ambience, "duration", None
        )
        manifest["status"] = "complete"
        manifest["elapsed_seconds"] = round(perf_counter() - start, 2)
        self.storage.write_json(folder / "manifest.json", manifest)
        return {
            "story": story,
            "story_id": story_id,
            "folder": folder,
            "manifest": manifest,
        }


def _environment_info(gpu: str | None = None) -> dict:
    package_versions = {}
    for package in ("fifthplot", "torch", "diffusers", "transformers", "gradio", "piper-tts"):
        try:
            package_versions[package] = version(package)
        except PackageNotFoundError:
            package_versions[package] = None
    memory = {"total_gb": None, "available_gb": None}
    if os.name == "nt":
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_phys", ctypes.c_ulonglong),
                ("available_phys", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.length = ctypes.sizeof(MemoryStatusEx)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            memory = {
                "total_gb": round(status.total_phys / 1024**3, 2),
                "available_gb": round(status.available_phys / 1024**3, 2),
            }
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": platform.processor() or None,
        "logical_processors": os.cpu_count(),
        "ram": memory,
        "gpu": gpu,
        "versions": package_versions,
    }
