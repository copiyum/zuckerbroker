import pytest

from househunt.extractors import clean_url, looks_like_sale, normalize_bhk


@pytest.mark.parametrize("raw,expected", [
    ("2", "2 BHK"),
    ("2 BHK", "2 BHK"),
    ("2BHK", "2 BHK"),
    ("3bhk", "3 BHK"),
    ("1 BHK", "1 BHK"),
    ("1BHK", "1 BHK"),
    ("1 RK", "1 RK"),
    ("rk", "1 RK"),
    ("studio", "Studio"),
    ("Studio", "Studio"),
    ("2 BHK / 3 BHK", "2 BHK / 3 BHK"),
    ("1bhk 2bhk 3bhk", "1 BHK / 2 BHK / 3 BHK"),
    ("2.5 BHK", "2.5 BHK"),
    ("", None),
    (None, None),
    ("no bedroom info", None),
])
def test_normalize_bhk(raw, expected):
    assert normalize_bhk(raw) == expected


def test_clean_url_strips_tracking_params():
    dirty = ("https://www.facebook.com/groups/flat.and.flatmates/posts/27416511608002190/"
             "?__cft__[0]=AZabc&__tn__=%2CO%2CP-R")
    assert clean_url(dirty) == ("https://www.facebook.com/groups/"
                                "flat.and.flatmates/posts/27416511608002190/")


def test_clean_url_already_clean():
    u = "https://www.facebook.com/groups/g/posts/123/"
    assert clean_url(u) == u


def test_clean_url_none_passthrough():
    assert clean_url(None) is None
    assert clean_url("") is None


@pytest.mark.parametrize("text,expected", [
    ("Move out sale. Sofa 10000, fridge 5000", True),
    ("Moving out sale, everything must go", True),
    ("Selling my study table, 2.5k", True),
    ("Dining table for sale", True),
    ("Sofa- 10000\nStudy table -6500\nBed - 5000", True),
    ("2BHK fully furnished with sofa, fridge, washing machine, rent 30k", False),
    ("1 BHK semi furnished, deposit 60000, near HSR", False),
    ("Looking for a room in a 2BHK", False),
    ("Flatmate wanted for 3BHK", False),
    ("", False),
])
def test_looks_like_sale(text, expected):
    assert looks_like_sale(text) is expected
