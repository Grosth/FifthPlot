"""One-story image worker, isolated so its model memory is released on exit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fifthplot.domain import Story
from fifthplot.image_engine import DiffusersIllustrator


def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def run(request_path: Path, result_path: Path, progress_path: Path) -> int:
    request = json.loads(request_path.read_text(encoding="utf-8"))
    story = Story.model_validate_json(request["story"])
    illustrator = DiffusersIllustrator(**request["illustrator"])

    def report_progress(number: int, total: int, title: str) -> None:
        _write_json(
            progress_path,
            {"number": number, "total": total, "title": title},
        )

    try:
        illustrator._generate_story_in_process(
            story,
            Path(request["folder"]),
            strategy=request["strategy"],
            progress=report_progress,
        )
        _write_json(
            result_path,
            {
                "ok": True,
                "gpu_name": illustrator.gpu_name,
                "last_run": illustrator.last_run,
            },
        )
        return 0
    except Exception as exc:
        _write_json(
            result_path,
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
        )
        return 1


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Uso: python -m fifthplot.image_worker REQUEST RESULT PROGRESS",
            file=sys.stderr,
        )
        return 2
    return run(*(Path(argument) for argument in sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
