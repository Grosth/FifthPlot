import unittest
from types import SimpleNamespace

from fifthplot.domain import Scene
from fifthplot.prompt_builder import bounded_scene_prompt, scene_prompt
from tests.story_fixture import make_story


class PromptBuilderTests(unittest.TestCase):
    def test_scene_prompt_repeats_identity_and_uses_full_scene_context(self):
        story = make_story()
        prompt = scene_prompt(story, story.scenes[0])
        self.assertIn("A small orange fox with golden eyes", prompt)
        self.assertIn("forest path", prompt)
        self.assertIn("enchanted forest", prompt)
        self.assertIn("watercolor", prompt.casefold())
        self.assertIn("Complete storybook illustration", prompt)

    def test_bounded_prompt_stays_within_clip_budget(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        story.visual_style = "dreamlike blue violet watercolor palette " * 8
        scene = story.scenes[0]
        scene.image_prompt = "Luma discovers a golden compass beside a river of clouds " * 8
        scene.background_prompt = "Floating islands, moonlit clouds, and stars " * 8
        prompt = bounded_scene_prompt(story, scene, WordTokenizer())
        self.assertLessEqual(len(prompt.split()), 70)
        self.assertIn("Luma discovers", prompt)
        self.assertIn("orange fox", prompt)
        self.assertIn("Watercolor storybook", prompt)


if __name__ == "__main__":
    unittest.main()
