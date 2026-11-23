"""Síntesis local de narración y ambientes de escena."""

import hashlib
import math
import os
import wave
from pathlib import Path

import numpy as np
import soundfile as sf


class AudioGenerationError(RuntimeError):
    pass


class PiperNarrator:
    """TTS Piper local; carga una voz ONNX bajo demanda y reutiliza el modelo."""

    def __init__(
        self,
        model_path: Path | str | None = None,
        data_dir: Path | str = "models/voices",
        rate_scale: float = 1.0,
    ) -> None:
        self.model_path = Path(
            model_path
            or os.getenv(
                "FIFTHPLOT_PIPER_VOICE",
                str(Path(data_dir) / "es_ES-carlfm-x_low.onnx"),
            )
        )
        self.rate_scale = rate_scale
        self._voice = None

    def _load_voice(self):
        if not self.model_path.is_file():
            raise AudioGenerationError(
                "Falta la voz local de Piper. Instala la voz española elegida "
                "en models/voices y conserva su MODEL_CARD y licencia."
            )
        if self._voice is None:
            try:
                from piper import PiperVoice

                self._voice = PiperVoice.load(str(self.model_path))
            except Exception as exc:
                raise AudioGenerationError(
                    f"No se pudo cargar la voz Piper local: {exc}"
                ) from exc
        return self._voice

    def synthesize(self, text: str, destination: Path | str) -> Path:
        if not text.strip():
            raise AudioGenerationError("No hay texto para narrar.")
        voice = self._load_voice()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with wave.open(str(destination), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except Exception as exc:
            raise AudioGenerationError(f"Falló la síntesis de voz: {exc}") from exc
        return destination


def _seed_for(text: str, number: int) -> int:
    digest = hashlib.sha256(f"{number}:{text}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


class ProceduralAmbience:
    """Genera una pista ambiental determinista con ruido filtrado y tonos."""

    def __init__(self, sample_rate: int = 22050, duration: float = 9.0) -> None:
        self.sample_rate = sample_rate
        self.duration = duration

    def synthesize(
        self,
        prompt: str,
        destination: Path | str,
        scene_number: int,
    ) -> Path:
        if not prompt.strip():
            raise AudioGenerationError("La escena no tiene indicación de ambiente.")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(_seed_for(prompt, scene_number))
        count = int(self.sample_rate * self.duration)
        time_axis = np.arange(count, dtype=np.float32) / self.sample_rate
        raw = rng.standard_normal(count).astype(np.float32)
        # Suavizado acumulado: ruido grave y continuo para viento, agua y bosque.
        brown = np.cumsum(raw, dtype=np.float64).astype(np.float32)
        brown /= max(float(np.max(np.abs(brown))), 1e-6)
        high_pass = raw - np.roll(raw, 1)
        high_pass /= max(float(np.max(np.abs(high_pass))), 1e-6)
        prompt_lower = prompt.casefold()
        if any(word in prompt_lower for word in ("noche", "estrellas", "mágic", "magic", "mystic")):
            base_hz, tone_gain = 523.25, 0.12
        elif any(word in prompt_lower for word in ("lluvia", "tormenta", "rain", "thunder")):
            base_hz, tone_gain = 196.0, 0.06
        elif any(word in prompt_lower for word in ("agua", "río", "rio", "water", "river")):
            base_hz, tone_gain = 330.0, 0.07
        else:
            base_hz, tone_gain = 261.63, 0.08
        envelope = (0.55 + 0.22 * np.sin(2 * math.pi * 0.11 * time_axis)).astype(np.float32)
        tonal = (
            np.sin(2 * math.pi * base_hz * time_axis)
            + 0.45 * np.sin(2 * math.pi * base_hz * 1.5 * time_axis + 0.7)
        ).astype(np.float32)
        audio = 0.19 * brown * envelope + tone_gain * tonal
        if any(word in prompt_lower for word in ("hojas", "bosque", "leaves", "forest")):
            gusts = np.maximum(
                0.0,
                np.sin(2 * math.pi * (0.17 + 0.03 * rng.random()) * time_axis),
            )
            audio += 0.075 * high_pass * gusts
        if any(word in prompt_lower for word in ("lluvia", "rain", "tormenta")):
            drop_mask = rng.random(count) > 0.9992
            drop = np.zeros(count, dtype=np.float32)
            drop[drop_mask] = rng.uniform(0.2, 0.8, int(drop_mask.sum()))
            audio += drop
        if any(word in prompt_lower for word in ("fuego", "fire", "crackle")):
            crackle_mask = rng.random(count) > 0.9988
            crackle = np.zeros(count, dtype=np.float32)
            crackle[crackle_mask] = rng.uniform(0.08, 0.35, int(crackle_mask.sum()))
            audio += crackle
        audio = np.clip(audio, -0.95, 0.95).astype(np.float32)
        sf.write(destination, audio, self.sample_rate, subtype="PCM_16")
        return destination
