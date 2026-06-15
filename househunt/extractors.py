import re

BHK_RE = re.compile(r'(\d+(?:\.\d)?)\s*(?:bhk|bedroom|bed\b|rk\b)', re.I)
PHONE_RE = re.compile(r'(?<!\d)(\+?91[\-\s]?)?([6-9]\d{9})(?!\d)')


def _amount(text: str, keyword_re: str) -> int | None:
    """Find a money amount near a keyword; normalize trailing 'k' to *1000."""
    for m in re.finditer(r'(?:' + keyword_re + r')[^\d]{0,15}(?:rs\.?|₹|inr)?\s*([\d.,]+)\s*(k)?', text, re.I):
        num = m.group(1).replace(',', '')
        try:
            v = float(num)
        except ValueError:
            continue
        if m.group(2) or v < 1000:
            v *= 1000
        if 1000 <= v <= 1_000_000:
            return int(v)
    return None


def parse_rent(text: str) -> int | None:
    return _amount(text, r'rent')


def parse_deposit(text: str) -> int | None:
    return _amount(text, r'deposit|advance|security')


def parse_maintenance(text: str) -> int | None:
    return _amount(text, r'maintenance|maint\b')


def parse_bhk(text: str) -> str | None:
    m = BHK_RE.search(text)
    if m:
        return m.group(1) + " BHK"
    if re.search(r'\b1\s*rk\b', text, re.I):
        return "1 RK"
    if re.search(r'\bstudio\b', text, re.I):
        return "Studio"
    return None


def parse_listing_type(text: str) -> str | None:
    t = text.lower()
    if re.search(r'\b(flatmate|roommate|sharing|shared|looking for (a )?(girl|boy|guy|female|male))\b', t):
        return "flatmate"
    if re.search(r'\b(private|single|own)\s+room\b', t):
        return "private_room"
    if re.search(r'\b(entire|whole|full)\s+(flat|house|apartment|home)\b', t) or re.search(r'\bbhk\b', t):
        return "entire_flat"
    return None


def parse_furnishing(text: str) -> str | None:
    t = text.lower()
    if "semi" in t and "furnish" in t:
        return "semi_furnished"
    if "unfurnish" in t or "no furnish" in t:
        return "unfurnished"
    if "furnish" in t:
        return "furnished"
    return None


def parse_contact(text: str) -> str | None:
    m = PHONE_RE.search(text)
    return m.group(2) if m else None


def regex_extract(text: str) -> dict:
    """Offline best-effort extraction. Unfillable fields are None.
    location, available_from, notes are not reliably regex-able -> None."""
    text = text or ""
    return {
        "bhk": parse_bhk(text),
        "rent": parse_rent(text),
        "deposit": parse_deposit(text),
        "maintenance": parse_maintenance(text),
        "location": None,
        "contact": parse_contact(text),
        "listing_type": parse_listing_type(text),
        "furnishing": parse_furnishing(text),
        "available_from": None,
        "notes": None,
    }
