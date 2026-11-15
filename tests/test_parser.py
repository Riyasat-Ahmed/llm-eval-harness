from evalh.scoring.parser import parse_label


def test_exact_category_passes_through():
    assert parse_label("Billing") == "Billing"


def test_case_and_whitespace_insensitive():
    assert parse_label("  technical issue \n") == "Technical issue"


def test_strips_quotes_and_punctuation():
    assert parse_label('"Refund."') == "Refund"
    assert parse_label("- Shipping") == "Shipping"


def test_prefixed_answer_with_single_match():
    assert parse_label("Category: Account access") == "Account access"


def test_unparseable_output_returns_none():
    assert parse_label("I'm not sure which category this fits.") is None


def test_empty_output_returns_none():
    assert parse_label("") is None
    assert parse_label(None) is None  # type: ignore[arg-type]


def test_multiple_category_mentions_is_unparseable():
    assert parse_label("Could be Billing or Refund depending on intent") is None
