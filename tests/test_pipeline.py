import tempfile
import unittest
from pathlib import Path

from fifthplot.audio_engine import ProceduralAmbience
from fifthplot.domain import StoryRequest
from fifthplot.pipeline import StorybookPipeline
from fifthplot.storage import StoryStorage
from tests.story_fixture import make_story


class FakeStoryGenerator:
    def generate(self, request: StoryRequest):
        return make_story()


class FakeIllustrator:
    def generate_story(self, story, folder, strategy, progress=None):
        paths = []
        for scene in story.scenes:
            path = Path(folder) / f"scene_{scene.number:02d}.png"
            path.write_bytes(b"simulated-image")
            paths.append(path)
        return paths


class FakeNarrator:
    def synthesize(self, text, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"simulated-voice")
        return destination


class FailingNarrator(FakeNarrator):
    def synthesize(self, text, destination):
        raise RuntimeError("simulated voice failure")


class PipelineIntegrationTests(unittest.TestCase):
    def test_simulated_models_create_five_complete_scene_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = StorybookPipeline(
                story_generator=FakeStoryGenerator(),
                illustrator=FakeIllustrator(),
                narrator=FakeNarrator(),
                ambience=ProceduralAmbience(sample_rate=8000, duration=0.1),
                storage=StoryStorage(root / "books"),
            )
            result = service.generate("Una llave", "Fantasía", strategy="text_only")
            self.assertEqual(result["manifest"]["status"], "complete")
            self.assertEqual(len(result["manifest"]["scenes"]), 5)
            for item in result["manifest"]["scenes"]:
                self.assertTrue((result["folder"] / item["image"]).is_file())
                self.assertTrue((result["folder"] / item["narration"]).is_file())
                self.assertTrue((result["folder"] / item["ambience"]).is_file())

    def test_failure_is_visible_in_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = StorybookPipeline(
                story_generator=FakeStoryGenerator(),
                illustrator=FakeIllustrator(),
                narrator=FailingNarrator(),
                ambience=ProceduralAmbience(sample_rate=8000, duration=0.1),
                storage=StoryStorage(root / "books"),
            )
            with self.assertRaisesRegex(RuntimeError, "simulated voice failure"):
                service.generate("Una llave", "Misterio", strategy="text_only")
            manifests = list((root / "books").glob("*/manifest.json"))
            self.assertEqual(len(manifests), 1)
            import json

            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed")
            self.assertIn("simulated voice failure", manifest["error"])


if __name__ == "__main__":
    unittest.main()
