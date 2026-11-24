import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fifthplot.image_engine import DiffusersIllustrator, ImageGenerationError
from tests.story_fixture import make_story


class ImageEngineTests(unittest.TestCase):
    def test_preflight_failure_does_not_keep_runs_from_previous_story(self):
        illustrator = DiffusersIllustrator()
        illustrator.last_run = [{"file": "old-story/scene_01.png"}]

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch("fifthplot.image_engine._available_ram_gb", return_value=2.0),
                patch("fifthplot.image_engine.RAM_RELEASE_WAIT_SECONDS", 0),
            ):
                with self.assertRaisesRegex(ImageGenerationError, "requiere al menos 4 GB"):
                    illustrator._generate_story_in_process(
                        make_story(),
                        Path(temporary) / "new-story",
                        strategy="text_only",
                    )

        self.assertEqual(illustrator.last_run, [])

    def test_waits_briefly_for_unloaded_model_memory(self):
        with (
            patch("fifthplot.image_engine._available_ram_gb", side_effect=[3.9, 4.2]),
            patch("fifthplot.image_engine.time.sleep") as sleep,
        ):
            from fifthplot.image_engine import _wait_for_available_ram

            available = _wait_for_available_ram(4.0)

        self.assertEqual(available, 4.2)
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
