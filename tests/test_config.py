import pytest

from evalh.config import ConfigError, config_hash, load_configs


def test_loads_all_launch_configs():
    specs = load_configs("tickets")
    names = {s.name for s in specs}
    assert names == {
        "large_baseline", "small_baseline", "small_fewshot",
        "anthropic_large_baseline", "anthropic_small_baseline", "anthropic_small_fewshot",
    }


def test_configs_have_distinct_hashes():
    specs = load_configs("tickets")
    hashes = {config_hash("tickets", s) for s in specs}
    assert len(hashes) == len(specs)


def test_hash_is_stable_for_same_config():
    specs = load_configs("tickets")
    spec = specs[0]
    assert config_hash("tickets", spec) == config_hash("tickets", spec)


def test_missing_configs_dir_raises():
    with pytest.raises(ConfigError):
        load_configs("does-not-exist")
