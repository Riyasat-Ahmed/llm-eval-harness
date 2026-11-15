from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evalh.models import Example

TASKS_ROOT = Path(__file__).resolve().parent.parent / "tasks"


class DatasetError(ValueError):
    pass


def task_dir(task: str) -> Path:
    d = TASKS_ROOT / task
    if not d.is_dir():
        raise DatasetError(f"unknown task {task!r}; expected a directory at {d}")
    return d


def load_dataset(task: str) -> list[Example]:
    """Load and validate tasks/<task>/data.jsonl. Raises DatasetError on any problem."""
    path = task_dir(task) / "data.jsonl"
    if not path.is_file():
        raise DatasetError(f"no dataset at {path}")

    examples: list[Example] = []
    seen_ids: set[str] = set()
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            raise DatasetError(f"{path}:{lineno}: invalid JSON: {e}") from e
        try:
            example = Example.model_validate(raw)
        except Exception as e:
            raise DatasetError(f"{path}:{lineno}: invalid row: {e}") from e
        if example.id in seen_ids:
            raise DatasetError(f"{path}:{lineno}: duplicate id {example.id!r}")
        seen_ids.add(example.id)
        examples.append(example)

    if not examples:
        raise DatasetError(f"{path}: no examples found")
    return examples


def dataset_hash(task: str) -> str:
    """Hash of the raw dataset file bytes, used for reproducibility tracking."""
    path = task_dir(task) / "data.jsonl"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
