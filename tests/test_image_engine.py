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
            with patch("fifthplot.image_engine._available_ram_gb", return_value=2.0):
                with self.assertRaisesRegex(ImageGenerationError, "requiere al menos 4 GB"):
                    illustrator.generate_story(
                        make_story(),
                        Path(temporary) / "new-story",
                        strategy="text_only",
                    )

        self.assertEqual(illustrator.last_run, [])


if __name__ == "__main__":
    unittest.main()
