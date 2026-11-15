import pytest

from evalh.dataset import DatasetError, dataset_hash, load_dataset


def test_loads_tickets_dataset():
    examples = load_dataset("tickets")
    assert len(examples) == 100
    assert len({e.id for e in examples}) == 100


def test_every_category_has_at_least_ten_examples():
    examples = load_dataset("tickets")
    counts: dict[str, int] = {}
    for e in examples:
        counts[e.expected] = counts.get(e.expected, 0) + 1
    assert set(counts) == {
        "Billing", "Technical issue", "Account access", "Shipping", "Refund", "Other",
    }
    assert all(n >= 10 for n in counts.values())


def test_unknown_task_raises():
    with pytest.raises(DatasetError):
        load_dataset("does-not-exist")


def test_dataset_hash_is_stable_and_short():
    h1 = dataset_hash("tickets")
    h2 = dataset_hash("tickets")
    assert h1 == h2
    assert len(h1) == 16


def test_duplicate_id_rejected(tmp_path, monkeypatch):
    task_root = tmp_path / "tasks" / "dupes"
    task_root.mkdir(parents=True)
    (task_root / "data.jsonl").write_text(
        '{"id": "a", "input": "x", "expected": "Other"}\n'
        '{"id": "a", "input": "y", "expected": "Other"}\n'
    )
    monkeypatch.setattr("evalh.dataset.TASKS_ROOT", tmp_path / "tasks")
    with pytest.raises(DatasetError):
        load_dataset("dupes")
