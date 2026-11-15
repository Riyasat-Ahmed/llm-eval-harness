import pytest

from evalh.pricing import PricingError, cost_usd


def test_ollama_is_always_free():
    assert cost_usd("ollama", "anything", tokens_in=10_000, tokens_out=10_000) == 0.0


def test_known_openai_model_priced_correctly():
    # gpt-5-mini: $0.25/1M in, $2.00/1M out
    cost = cost_usd("openai", "gpt-5-mini", tokens_in=1_000_000, tokens_out=1_000_000)
    assert cost == pytest.approx(0.25 + 2.00)


def test_unknown_model_raises():
    with pytest.raises(PricingError):
        cost_usd("openai", "no-such-model", tokens_in=1, tokens_out=1)


def test_unknown_provider_raises():
    with pytest.raises(PricingError):
        cost_usd("no-such-provider", "x", tokens_in=1, tokens_out=1)
