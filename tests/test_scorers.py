from evalh.scoring.scorers import exact_match


def test_correct_match():
    assert exact_match("Billing", "Billing") is True


def test_incorrect_match():
    assert exact_match("Billing", "Refund") is False


def test_none_parsed_is_always_wrong():
    assert exact_match(None, "Billing") is False


def test_whitespace_is_trimmed():
    assert exact_match(" Billing ", "Billing") is True
