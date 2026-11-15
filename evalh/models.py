from __future__ import annotations

from pydantic import BaseModel


class Example(BaseModel):
    """One labelled row from a task's dataset.jsonl."""

    id: str
    input: str
    expected: str
    notes: str | None = None


class ConfigSpec(BaseModel):
    """One LLM configuration to evaluate, loaded from a task's configs/*.yaml."""

    name: str
    provider: str
    model: str
    prompt_file: str
    temperature: float = 0.0
    max_tokens: int = 50

    def params_json(self) -> str:
        import json

        return json.dumps(
            {"temperature": self.temperature, "max_tokens": self.max_tokens},
            sort_keys=True,
        )


class ProviderResponse(BaseModel):
    """What every provider wrapper returns, in one shape."""

    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    error: str | None = None


class ResultRow(BaseModel):
    """One run x config x example outcome, as stored in SQLite."""

    run_id: str
    config_hash: str
    config_name: str
    example_id: str
    output_raw: str | None
    output_parsed: str | None
    correct: bool
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    error: str | None = None


class RunSummary(BaseModel):
    config_name: str
    n: int
    accuracy: float
    parse_failures: int
    cost_per_1000: float
    median_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
