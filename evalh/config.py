from __future__ import annotations

import hashlib
import json

import yaml

from evalh.dataset import DatasetError, task_dir
from evalh.models import ConfigSpec


class ConfigError(ValueError):
    pass


def load_configs(task: str, pattern: str = "*.yaml") -> list[ConfigSpec]:
    """Load every tasks/<task>/configs/<pattern> file as a ConfigSpec."""
    try:
        configs_dir = task_dir(task) / "configs"
    except DatasetError as e:
        raise ConfigError(str(e)) from e
    if not configs_dir.is_dir():
        raise ConfigError(f"no configs directory at {configs_dir}")

    paths = sorted(configs_dir.glob(pattern))
    if not paths:
        raise ConfigError(f"no config files matching {pattern!r} in {configs_dir}")

    specs: list[ConfigSpec] = []
    names: set[str] = set()
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        if raw is None:
            raise ConfigError(f"{path}: empty config file")
        raw.setdefault("name", path.stem)
        try:
            spec = ConfigSpec.model_validate(raw)
        except Exception as e:
            raise ConfigError(f"{path}: invalid config: {e}") from e

        prompt_path = task_dir(task) / spec.prompt_file
        if not prompt_path.is_file():
            raise ConfigError(f"{path}: prompt_file {spec.prompt_file!r} not found")

        if spec.name in names:
            raise ConfigError(f"duplicate config name {spec.name!r}")
        names.add(spec.name)
        specs.append(spec)
    return specs


def config_hash(task: str, spec: ConfigSpec) -> str:
    """Hash of everything that affects a config's output: model, params, and prompt text."""
    prompt_text = (task_dir(task) / spec.prompt_file).read_text()
    payload = json.dumps(
        {
            "provider": spec.provider,
            "model": spec.model,
            "params": spec.params_json(),
            "prompt": prompt_text,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def load_prompt(task: str, spec: ConfigSpec) -> str:
    return (task_dir(task) / spec.prompt_file).read_text()
