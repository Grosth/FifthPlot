import unittest

from pydantic import ValidationError

from fifthplot.domain import Story, StoryRequest
from tests.story_fixture import make_story


class StoryDomainTests(unittest.TestCase):
    def test_accepts_exactly_five_ordered_scenes(self):
        story = make_story()
        self.assertEqual([scene.number for scene in story.scenes], [1, 2, 3, 4, 5])

    def test_rejects_missing_scene(self):
        data = make_story().model_dump()
        data["scenes"].pop()
        with self.assertRaises(ValidationError):
            Story.model_validate(data)

    def test_rejects_unknown_scene_character(self):
        data = make_story().model_dump()
        data["scenes"][1]["characters_present"] = ["Desconocido"]
        with self.assertRaises(ValidationError):
            Story.model_validate(data)

    def test_rejects_reordered_scenes_without_silently_renumbering(self):
        data = make_story().model_dump()
        data["scenes"][0]["number"] = 2
        with self.assertRaises(ValidationError):
            Story.model_validate(data)

    def test_inputs_are_required_and_nonblank(self):
        with self.assertRaises(ValidationError):
            StoryRequest(idea=" ", genre="Fantasía")


if __name__ == "__main__":
    unittest.main()
