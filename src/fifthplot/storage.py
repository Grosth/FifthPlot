"""Persistencia local y manifiestos de generación."""

import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fifthplot.domain import Story


def safe_slug(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return (slug[:limit].strip("-") or "cuento")


class StoryStorage:
    def __init__(self, root: Path | str = "outputs/storybooks") -> None:
        self.root = Path(root)

    def create_story_dir(self, title: str) -> tuple[str, Path]:
        story_id = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
        folder = self.root / f"{safe_slug(title)}_{story_id}"
        folder.mkdir(parents=True, exist_ok=False)
        return story_id, folder

    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(path)

    def write_story(self, folder: Path, story: Story) -> Path:
        path = folder / "story.json"
        self.write_json(path, story.model_dump(mode="json"))
        return path
