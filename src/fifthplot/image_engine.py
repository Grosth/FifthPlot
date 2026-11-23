"""Generación local de ilustraciones completas con Diffusers."""

from __future__ import annotations

import gc
import ctypes
import os
from pathlib import Path
from time import perf_counter
from typing import Callable

from PIL import Image

from fifthplot.domain import Story
from fifthplot.prompt_builder import (
    bounded_scene_prompt,
    bounded_cast_reference_prompt,
    negative_prompt_for_scene,
)


class ImageGenerationError(RuntimeError):
    pass


def _available_ram_gb() -> float | None:
    if os.name != "nt":
        return None

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
        return status.available_phys / 1024**3
    return None


class DiffusersIllustrator:
    def __init__(
        self,
        model_dir: Path | str = "models/dreamshaper-8",
        adapter_dir: Path | str = "models/ip-adapter",
        reference_dir: Path | str = "outputs/assets/characters",
        steps: int = 20,
        guidance: float = 7.0,
        size: int = 512,
        adapter_scale: float = 0.45,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.adapter_dir = Path(adapter_dir)
        self.reference_dir = Path(reference_dir)
        self.steps = steps
        self.guidance = guidance
        self.size = size
        self.adapter_scale = adapter_scale
        self.last_run: list[dict] = []
        self.gpu_name: str | None = None

    def _load(self, use_ip_adapter: bool) -> StableDiffusionPipeline:
        import torch
        from diffusers import StableDiffusionPipeline

        if not (self.model_dir / "model_index.json").is_file():
            raise ImageGenerationError(
                f"No se encontró el modelo Diffusers local: {self.model_dir}"
            )
        try:
            pipe = StableDiffusionPipeline.from_pretrained(
                str(self.model_dir),
                torch_dtype=torch.float16,
                variant="fp16",
                use_safetensors=True,
                local_files_only=True,
                low_cpu_mem_usage=True,
            )
            pipe.vae.enable_slicing()
            if use_ip_adapter:
                adapter = self.adapter_dir / "models" / "ip-adapter-plus_sd15.safetensors"
                if not adapter.is_file():
                    raise ImageGenerationError(
                        f"No se encontró el IP-Adapter local: {adapter}"
                    )
                pipe.load_ip_adapter(
                    str(self.adapter_dir),
                    subfolder="models",
                    weight_name="ip-adapter-plus_sd15.safetensors",
                    image_encoder_folder="image_encoder",
                    local_files_only=True,
                    low_cpu_mem_usage=True,
                )
                pipe.set_ip_adapter_scale(self.adapter_scale)
            # La carga del adaptador precede a la activación de CPU offload.
            pipe.enable_model_cpu_offload()
            return pipe
        except ImageGenerationError:
            raise
        except Exception as exc:
            raise ImageGenerationError(
                f"No se pudo cargar el generador local de imágenes: {exc}"
            ) from exc

    def _reference(self, pipe, story, scene, folder: Path) -> Path:
        import torch

        ref_path = folder / f"scene_{scene.number:02d}_cast_reference.png"
        prompt = bounded_cast_reference_prompt(story, scene, pipe.tokenizer)
        negative_prompt = negative_prompt_for_scene(story, scene)
        generator = torch.Generator(device="cpu").manual_seed(8100 + scene.number)
        torch.cuda.reset_peak_memory_stats()
        started = perf_counter()
        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=self.size,
            height=self.size,
            num_inference_steps=self.steps,
            guidance_scale=self.guidance,
            generator=generator,
        ).images[0]
        image.save(ref_path)
        image.close()
        self.last_run.append(
            {
                "stage": "scene_cast_reference",
                "scene": scene.number,
                "elapsed_seconds": round(perf_counter() - started, 2),
                "gpu_peak_allocated_gb": round(
                    torch.cuda.max_memory_allocated() / 1024**3, 3
                ),
                "seed": 8100 + scene.number,
                "size": f"{self.size}x{self.size}",
                "steps": self.steps,
                "characters": list(scene.characters_present),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "file": str(ref_path),
            }
        )
        return ref_path

    def generate_story(
        self,
        story,
        folder: Path | str,
        strategy: str = "ip_adapter",
        progress: Callable[[int, int, str], None] | None = None,
    ) -> list[Path]:
        self.last_run = []
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if strategy not in {"ip_adapter", "text_only"}:
            raise ValueError(f"Estrategia visual desconocida: {strategy}")
        available_ram = _available_ram_gb()
        minimum_ram = 6.0 if strategy == "ip_adapter" else 4.0
        if available_ram is not None and available_ram < minimum_ram:
            raise ImageGenerationError(
                f"Hay {available_ram:.1f} GB de RAM disponible; la estrategia "
                f"{strategy} requiere al menos {minimum_ram:.0f} GB disponibles "
                "para cargar el modelo con CPU offload. Cierra aplicaciones y "
                "vuelve a intentarlo."
            )
        import torch

        if not torch.cuda.is_available():
            raise ImageGenerationError(
                "No se detectó CUDA. La generación en CPU no está habilitada "
                "porque sería demasiado lenta para esta configuración."
            )
        self.gpu_name = torch.cuda.get_device_name(0)
        paths: list[Path] = []
        references: dict[int, Path] = {}
        if strategy == "ip_adapter":
            # La imagen de referencia debe generarse antes de cargar IP-Adapter.
            # Un pipeline con adapter exige image_embeds incluso para la
            # primera imagen, cuando todavía no existe una referencia.
            reference_pipe = self._load(use_ip_adapter=False)
            try:
                for scene in story.scenes:
                    references[scene.number] = self._reference(
                        reference_pipe, story, scene, folder
                    )
            finally:
                del reference_pipe
                gc.collect()
                torch.cuda.empty_cache()

        pipe = self._load(use_ip_adapter=(strategy == "ip_adapter"))
        try:
            for scene in story.scenes:
                prompt = bounded_scene_prompt(story, scene, pipe.tokenizer)
                negative_prompt = negative_prompt_for_scene(story, scene)
                seed = 4200 + scene.number
                generator = torch.Generator(device="cpu").manual_seed(seed)
                arguments = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": self.size,
                    "height": self.size,
                    "num_inference_steps": self.steps,
                    "guidance_scale": self.guidance,
                    "generator": generator,
                }
                started = perf_counter()
                torch.cuda.reset_peak_memory_stats()
                reference = references.get(scene.number)
                if reference is not None:
                    with Image.open(reference) as reference_image:
                        arguments["ip_adapter_image"] = reference_image.convert("RGB")
                        result = pipe(**arguments)
                else:
                    result = pipe(**arguments)
                image = result.images[0]
                destination = folder / f"scene_{scene.number:02d}.png"
                image.save(destination)
                image.close()
                del result
                paths.append(destination)
                self.last_run.append(
                    {
                        "stage": "scene",
                        "scene": scene.number,
                        "seed": seed,
                        "size": f"{self.size}x{self.size}",
                        "steps": self.steps,
                        "guidance_scale": self.guidance,
                        "adapter_scale": (
                            self.adapter_scale if reference is not None else None
                        ),
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "elapsed_seconds": round(perf_counter() - started, 2),
                        "gpu_peak_allocated_gb": round(
                            torch.cuda.max_memory_allocated() / 1024**3, 3
                        ),
                        "file": str(destination),
                    }
                )
                if progress:
                    progress(scene.number, 5, scene.scene_title)
                gc.collect()
                torch.cuda.empty_cache()
            return paths
        finally:
            del pipe
            gc.collect()
            torch.cuda.empty_cache()
