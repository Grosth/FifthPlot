import json
import unittest
from urllib.error import URLError

from fifthplot.domain import StoryRequest
from fifthplot.story_engine import OllamaStoryGenerator, StoryGenerationError
from tests.story_fixture import make_story


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class StoryEngineTests(unittest.TestCase):
    def test_uses_local_endpoint_and_validates_structured_response(self):
        story = make_story()
        requests = []

        def transport(request, timeout):
            requests.append((request, timeout))
            body = json.dumps(
                {"message": {"content": story.model_dump_json()}}
            ).encode()
            return FakeResponse(body)

        generator = OllamaStoryGenerator(transport=transport)
        result = generator.generate(
            StoryRequest(idea="Una llave perdida", genre="Fantasía")
        )
        self.assertEqual(result.title, story.title)
        self.assertTrue(requests[0][0].full_url.startswith("http://127.0.0.1:"))
        payload = json.loads(requests[0][0].data)
        self.assertIn("format", payload)
        self.assertEqual(payload["keep_alive"], 0)

    def test_refuses_remote_endpoint(self):
        with self.assertRaises(ValueError):
            OllamaStoryGenerator(base_url="https://example.com")

    def test_reports_local_service_failure(self):
        def transport(request, timeout):
            raise URLError("unavailable")

        generator = OllamaStoryGenerator(transport=transport)
        with self.assertRaises(StoryGenerationError):
            generator.generate(StoryRequest(idea="Una llave", genre="Fantasía"))

    def test_repairs_scene_character_missing_from_cast_once(self):
        story = make_story()
        invalid = story.model_dump()
        invalid["scenes"][0]["characters_present"] = ["The Compass"]
        responses = [
            json.dumps({"message": {"content": json.dumps(invalid)}}).encode(),
            json.dumps({"message": {"content": story.model_dump_json()}}).encode(),
        ]
        requests = []

        def transport(request, timeout):
            requests.append(json.loads(request.data))
            return FakeResponse(responses.pop(0))

        result = OllamaStoryGenerator(transport=transport).generate(
            StoryRequest(idea="Una brújula", genre="Aventura")
        )
        self.assertEqual(result.title, story.title)
        self.assertEqual(len(requests), 2)
        self.assertIn("reparto", requests[1]["messages"][-1]["content"])


if __name__ == "__main__":
    unittest.main()
