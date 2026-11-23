import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

from fifthplot.audio_engine import AudioGenerationError, PiperNarrator, ProceduralAmbience


class AudioTests(unittest.TestCase):
    def test_ambience_is_nonempty_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            engine = ProceduralAmbience(sample_rate=8000, duration=1.0)
            first = engine.synthesize("bosque de noche", root / "a.wav", 1)
            second = engine.synthesize("bosque de noche", root / "b.wav", 1)
            a, rate_a = sf.read(first)
            b, rate_b = sf.read(second)
            self.assertEqual(rate_a, 8000)
            self.assertEqual(rate_b, 8000)
            self.assertEqual(a.shape, b.shape)
            self.assertGreater(float(np.max(np.abs(a))), 0.01)
            np.testing.assert_allclose(a, b)

    def test_missing_voice_fails_visibly_without_network_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            narrator = PiperNarrator(model_path=Path(temporary) / "missing.onnx")
            with self.assertRaises(AudioGenerationError):
                narrator.synthesize("Hola", Path(temporary) / "voice.wav")


if __name__ == "__main__":
    unittest.main()
