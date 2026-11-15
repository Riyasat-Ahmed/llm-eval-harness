from __future__ import annotations

import statistics
from collections import defaultdict

from evalh.models import RunSummary


def summarize(results: list[dict]) -> list[RunSummary]:
    """One RunSummary per config_name, computed from store.fetch_results() rows."""
    by_config: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_config[row["config_name"]].append(row)

    summaries = []
    for name, rows in sorted(by_config.items()):
        n = len(rows)
        n_correct = sum(1 for r in rows if r["correct"])
        n_errors = sum(1 for r in rows if r["error"])
        n_parse_failures = sum(
            1 for r in rows if r["error"] is None and r["output_parsed"] is None
        )
        total_cost = sum(r["cost_usd"] for r in rows)
        latencies = sorted(r["latency_ms"] for r in rows if r["error"] is None)

        summaries.append(
            RunSummary(
                config_name=name,
                n=n,
                accuracy=n_correct / n if n else 0.0,
                parse_failures=n_parse_failures + n_errors,
                cost_per_1000=(total_cost / n * 1000) if n else 0.0,
                median_latency_ms=statistics.median(latencies) if latencies else 0.0,
                p95_latency_ms=_percentile(latencies, 0.95) if latencies else 0.0,
                total_cost_usd=total_cost,
            )
        )
    return summaries


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p
    floor, ceil = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if floor == ceil:
        return sorted_values[floor]
    return sorted_values[floor] + (sorted_values[ceil] - sorted_values[floor]) * (k - floor)
