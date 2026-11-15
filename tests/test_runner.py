import asyncio

import pytest

from evalh import runner, store
from evalh.models import ConfigSpec, Example, ProviderResponse


class FakeProvider:
    """Returns a scripted answer per call; never touches the network."""

    def __init__(self, answers: dict[str, str]):
        self.answers = answers
        self.calls = 0

    async def complete(self, *, model, prompt, temperature, max_tokens):
        self.calls += 1
        # The prompt always ends with the formatted ticket input; look it up.
        for key, answer in self.answers.items():
            if key in prompt:
                return ProviderResponse(
                    text=answer, tokens_in=10, tokens_out=2, latency_ms=5.0
                )
        return ProviderResponse(text="Other", tokens_in=10, tokens_out=2, latency_ms=5.0)


@pytest.fixture
def conn(tmp_path):
    return store.connect(tmp_path / "test.db")


@pytest.fixture
def spec(tmp_path, monkeypatch):
    task_dir = tmp_path / "tasks" / "fake"
    (task_dir / "configs").mkdir(parents=True)
    (task_dir / "prompt.txt").write_text("Classify: {input}")
    (task_dir / "configs" / "c.yaml").write_text(
        "name: c\nprovider: openai\nmodel: gpt-5-mini\nprompt_file: prompt.txt\n"
    )
    monkeypatch.setattr("evalh.dataset.TASKS_ROOT", tmp_path / "tasks")
    return ConfigSpec(name="c", provider="openai", model="gpt-5-mini", prompt_file="prompt.txt")


def test_run_one_scores_and_stores_a_correct_result(conn, spec, monkeypatch):
    fake = FakeProvider({"billing issue": "Billing"})
    monkeypatch.setattr(runner, "get_provider", lambda name: fake)

    example = Example(id="e1", input="billing issue", expected="Billing")
    row = asyncio.run(
        runner.run_one(
            conn=conn, run_id="r1", task="fake", spec=spec, example=example,
            semaphore=asyncio.Semaphore(1),
        )
    )
    assert row.correct is True
    assert row.output_parsed == "Billing"
    assert fake.calls == 1


def test_run_one_uses_cache_on_second_call(conn, spec, monkeypatch):
    fake = FakeProvider({"shipping delay": "Shipping"})
    monkeypatch.setattr(runner, "get_provider", lambda name: fake)

    example = Example(id="e2", input="shipping delay", expected="Shipping")
    sem = asyncio.Semaphore(1)
    kwargs = dict(conn=conn, task="fake", spec=spec, example=example, semaphore=sem)
    asyncio.run(runner.run_one(run_id="r1", **kwargs))
    asyncio.run(runner.run_one(run_id="r2", **kwargs))

    assert fake.calls == 1  # second run_id reused the cached response


def test_run_one_provider_failure_is_recorded_not_raised(conn, spec, monkeypatch):
    class AlwaysFails:
        async def complete(self, **kwargs):
            raise RuntimeError("simulated API outage")

    monkeypatch.setattr(runner, "get_provider", lambda name: AlwaysFails())
    monkeypatch.setattr(runner, "_call_with_retry", _fail_fast)

    example = Example(id="e3", input="anything", expected="Other")
    row = asyncio.run(
        runner.run_one(
            conn=conn, run_id="r1", task="fake", spec=spec, example=example,
            semaphore=asyncio.Semaphore(1),
        )
    )
    assert row.correct is False
    assert row.error is not None


async def _fail_fast(provider, **kwargs):
    # Skip tenacity's real backoff/retry delay in this test.
    return await provider.complete(**kwargs)
