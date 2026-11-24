import unittest
from types import SimpleNamespace

from fifthplot.domain import Scene
from fifthplot.prompt_builder import (
    ANIMAL_COMPOSITION_PROMPT,
    COMPOSITION_PROMPT,
    MASTER_VISUAL_STYLE_PROMPT,
    bounded_cast_reference_prompt,
    bounded_scene_prompt,
    negative_prompt_for_scene,
    scene_prompt,
)
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
        self.assertIn("one fox", prompt)
        self.assertIn(MASTER_VISUAL_STYLE_PROMPT, prompt)
        self.assertNotIn("dreamlike blue violet", prompt)

    def test_master_style_and_character_anchor_repeat_across_scenes(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        story.visual_style = "photorealistic cyberpunk oil painting"
        prompts = [
            bounded_scene_prompt(story, scene, WordTokenizer())
            for scene in story.scenes
        ]
        self.assertTrue(all(MASTER_VISUAL_STYLE_PROMPT in prompt for prompt in prompts))
        self.assertTrue(all(COMPOSITION_PROMPT in prompt for prompt in prompts))
        self.assertTrue(all(ANIMAL_COMPOSITION_PROMPT in prompt for prompt in prompts))
        self.assertTrue(all("photorealistic cyberpunk" not in prompt for prompt in prompts))
        self.assertEqual(
            prompts[0].split(".")[1],
            prompts[1].split(".")[1],
        )
        self.assertTrue(all(len(prompt.split()) <= 70 for prompt in prompts))

    def test_repeated_character_appearance_is_replaced_by_compact_anchor(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        character = story.characters[0]
        character.visual_prompt = (
            "Auburn fox with blue eyes, golden fur, and a scar on the cheek, "
            "standing in a moonlit forest."
        )
        scene = story.scenes[0]
        scene.image_prompt = (
            "Auburn fox with blue eyes, golden fur, and a scar on the cheek, "
            "walking past the river."
        )
        prompt = bounded_scene_prompt(story, scene, WordTokenizer())
        self.assertIn("fox Auburn with blue eyes, golden fur, scar cheek", prompt)
        self.assertIn("walking past the river", prompt)
        self.assertNotIn("with blue eyes, golden fur, and a scar", prompt)

    def test_animal_cast_gets_humanoid_negative_prompt_and_one_of_each_rule(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        scene = story.scenes[0]
        prompt = bounded_scene_prompt(story, scene, WordTokenizer())
        negative = negative_prompt_for_scene(story, scene)
        self.assertIn("one fox small orange with golden eyes", prompt)
        self.assertIn("people, humans, children", negative)

        story.characters[0].visual_prompt = "A young human explorer wearing a blue cloak."
        human_negative = negative_prompt_for_scene(story, scene)
        self.assertNotIn("people, humans, children", human_negative)

    def test_spanish_animal_identity_is_normalized_and_blocks_human_substitutions(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        character = story.characters[0]
        character.visual_prompt = (
            "A zorro pelirrojo con ojos azules, caminando por un bosque nocturno."
        )
        scene = story.scenes[0]

        prompt = bounded_scene_prompt(story, scene, WordTokenizer())
        negative = negative_prompt_for_scene(story, scene)

        self.assertIn("one red fox with blue eyes", prompt)
        self.assertIn("Quadruped animals, no humans", prompt)
        self.assertIn("people, humans, children, human bodies, clothes", negative)

    def test_scene_action_does_not_repeat_animals_already_in_the_cast(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        story.characters.append(
            story.characters[0].model_copy(
                update={
                    "name": "Mira",
                    "visual_prompt": "A deer with antlers and violet eyes.",
                }
            )
        )
        scene = story.scenes[1]
        scene.characters_present = ["Luma", "Mira"]
        scene.image_prompt = "A deer guides a fox through a misty forest."
        prompt = bounded_scene_prompt(story, scene, WordTokenizer())

        self.assertIn("one fox", prompt)
        self.assertIn("one deer", prompt)
        self.assertNotIn("guides a fox", prompt)
        self.assertEqual(prompt.count("fox"), 1)

    def test_cast_reference_prompt_contains_all_scene_characters(self):
        class WordTokenizer:
            def __call__(self, text, add_special_tokens=False):
                return SimpleNamespace(input_ids=text.split())

        story = make_story()
        story.characters.append(
            story.characters[0].model_copy(
                update={
                    "name": "Nube",
                    "visual_prompt": "A tiny silver owl with violet eyes and a blue star on its chest.",
                }
            )
        )
        story.scenes[0].characters_present = ["Luma", "Nube"]
        prompt = bounded_cast_reference_prompt(
            story, story.scenes[0], WordTokenizer()
        )
        self.assertIn("one fox", prompt)
        self.assertIn("one owl", prompt)
        self.assertIn("every character visible once", prompt)
        self.assertLessEqual(len(prompt.split()), 70)


if __name__ == "__main__":
    unittest.main()
