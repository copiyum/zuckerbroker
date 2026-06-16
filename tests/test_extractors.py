import pytest

from househunt import extractors as ex
from househunt.extractors import normalize_bhk

KEYS = {"bhk", "rent", "deposit", "maintenance", "location", "contact",
        "listing_type", "furnishing", "available_from", "notes"}


def test_returns_all_keys():
    out = ex.regex_extract("random text")
    assert set(out.keys()) == KEYS


def test_rent_k_notation():
    out = ex.regex_extract("2BHK fully furnished, rent 32k, entire flat")
    assert out["rent"] == 32000
    assert out["bhk"] == "2 BHK"
    assert out["listing_type"] == "entire_flat"
    assert out["furnishing"] == "furnished"


def test_rupee_and_deposit():
    out = ex.regex_extract("Rent ₹15000 pm, deposit 30000, maintenance 1500")
    assert out["rent"] == 15000
    assert out["deposit"] == 30000
    assert out["maintenance"] == 1500


def test_flatmate_and_phone():
    out = ex.regex_extract("Looking for flatmate, sharing room. Call 9876543210")
    assert out["listing_type"] == "flatmate"
    assert out["contact"] == "9876543210"


def test_private_room():
    out = ex.regex_extract("Private room available for rent 12k")
    assert out["listing_type"] == "private_room"


def test_deposit_only_does_not_set_rent():
    # "Security deposit ₹60000 only" — no "rent" word, so rent must be None
    out = ex.regex_extract("Security deposit ₹60000 only")
    assert out["rent"] is None
    assert out["deposit"] == 60000


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
