from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from evalh import store
from evalh.config import config_hash, load_prompt
from evalh.models import ConfigSpec, Example, ProviderResponse, ResultRow
from evalh.pricing import cost_usd
from evalh.providers import get_provider
from evalh.scoring import exact_match, parse_label

DEFAULT_CONCURRENCY = 8


class RetryableError(RuntimeError):
    """Raised for transient provider failures (rate limit, timeout, 5xx)."""


@retry(
    retry=retry_if_exception_type(RetryableError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _call_with_retry(provider, **kwargs) -> ProviderResponse:
    try:
        return await provider.complete(**kwargs)
    except RetryableError:
        raise
    except Exception as e:
        # Treat anything else (rate limits, timeouts, transient 5xx) as retryable;
        # F3 requires backoff retries and F3/NFR-Reliability requires one failed
        # call to never stop the whole run, so retries are capped at 3 attempts.
        raise RetryableError(str(e)) from e


async def run_one(
    *,
    conn: sqlite3.Connection,
    run_id: str,
    task: str,
    spec: ConfigSpec,
    example: Example,
    semaphore: asyncio.Semaphore,
) -> ResultRow:
    chash = config_hash(task, spec)
    cached = store.get_cached(conn, config_hash=chash, example_id=example.id)

    if cached is not None:
        response = cached
        error = cached.error
    else:
        async with semaphore:
            try:
                prompt = load_prompt(task, spec).format(input=example.input)
                provider = get_provider(spec.provider)
                response = await _call_with_retry(
                    provider,
                    model=spec.model,
                    prompt=prompt,
                    temperature=spec.temperature,
                    max_tokens=spec.max_tokens,
                )
                error = None
            except Exception as e:
                response = ProviderResponse(text="", tokens_in=0, tokens_out=0, latency_ms=0.0)
                error = str(e)
        store.save_cache(
            conn,
            config_hash=chash,
            example_id=example.id,
            response=response.model_copy(update={"error": error}),
            created_at=datetime.now(UTC).isoformat(),
        )

    parsed = parse_label(response.text) if error is None else None
    correct = exact_match(parsed, example.expected) if error is None else False
    cost = cost_usd(spec.provider, spec.model, response.tokens_in, response.tokens_out)

    row = ResultRow(
        run_id=run_id,
        config_hash=chash,
        config_name=spec.name,
        example_id=example.id,
        output_raw=response.text if error is None else None,
        output_parsed=parsed,
        correct=correct,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd=cost,
        latency_ms=response.latency_ms,
        error=error,
    )
    store.save_result(conn, row)
    return row


async def run_all(
    *,
    conn: sqlite3.Connection,
    run_id: str,
    task: str,
    configs: list[ConfigSpec],
    examples: list[Example],
    concurrency: int = DEFAULT_CONCURRENCY,
    on_result=None,
) -> list[ResultRow]:
    for spec in configs:
        store.upsert_config(conn, config_hash=config_hash(task, spec), spec=spec)

    semaphore = asyncio.Semaphore(concurrency)

    async def _run_and_report(spec: ConfigSpec, example: Example) -> ResultRow:
        row = await run_one(
            conn=conn, run_id=run_id, task=task, spec=spec, example=example, semaphore=semaphore
        )
        if on_result is not None:
            on_result(row)
        return row

    tasks = [
        _run_and_report(spec, example)
        for spec in configs
        for example in examples
    ]
    return await asyncio.gather(*tasks)
