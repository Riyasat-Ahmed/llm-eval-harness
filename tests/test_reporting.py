from evalh.reporting import summarize


def _row(config_name, correct, error=None, parsed="Billing", cost=0.001, latency=100.0):
    return {
        "config_name": config_name,
        "correct": correct,
        "error": error,
        "output_parsed": parsed,
        "cost_usd": cost,
        "latency_ms": latency,
    }


def test_accuracy_and_cost_per_1000():
    rows = [_row("a", True) for _ in range(3)] + [_row("a", False) for _ in range(1)]
    [summary] = summarize(rows)
    assert summary.n == 4
    assert summary.accuracy == 0.75
    assert summary.cost_per_1000 == 1.0  # $0.001 avg * 1000


def test_parse_failures_and_errors_both_counted_and_never_correct():
    rows = [
        _row("a", False, parsed=None),  # unparseable
        _row("a", False, error="boom", parsed=None),  # provider error
    ]
    [summary] = summarize(rows)
    assert summary.parse_failures == 2
    assert summary.accuracy == 0.0


def test_multiple_configs_summarized_separately():
    rows = [_row("a", True), _row("b", False)]
    summaries = {s.config_name: s for s in summarize(rows)}
    assert summaries["a"].accuracy == 1.0
    assert summaries["b"].accuracy == 0.0
