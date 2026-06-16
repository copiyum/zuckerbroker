import re

BHK_RE = re.compile(r'(\d+(?:\.\d)?)\s*(?:bhk|bedroom|bed\b)', re.I)
_RK_RE = re.compile(r'(\d+)\s*rk\b', re.I)
PHONE_RE = re.compile(r'(?<!\d)(\+?91[\-\s]?)?([6-9]\d{9})(?!\d)')

_BHK_NUM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:bhk|bedroom|bed\b)', re.I)
_BARE_NUM_RE = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*$')


def clean_url(url: str | None) -> str | None:
    """Drop query string (FB `?__cft__…&__tn__=…` tracking) from a permalink."""
    if not url:
        return None
    return url.split("?", 1)[0]


def normalize_bhk(raw: str | None) -> str | None:
    """Canonicalize messy bhk strings -> 'N BHK' / '1 RK' / 'Studio' / None.
    Multi-config strings ('1bhk 2bhk 3bhk') -> '1 BHK / 2 BHK / 3 BHK'."""
    if not raw:
        return None
    text = str(raw).strip()
    low = text.lower()
    if "studio" in low:
        return "Studio"
    nums = _BHK_NUM_RE.findall(text)
    if not nums:
        m = _BARE_NUM_RE.match(text)
        if m:
            nums = [m.group(1)]
    if nums:
        labels = []
        for n in nums:
            label = f"{n} BHK"
            if label not in labels:
                labels.append(label)
        return " / ".join(labels)
    # RK is conventionally always 1RK (one room + kitchen); any "RK" mention -> "1 RK".
    if re.search(r'\brk\b', low) or low == "rk":
        return "1 RK"
    return None


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
    # RK is conventionally always 1RK; any "RK"/"1rk"/"2rk" mention -> "1 RK".
    if _RK_RE.search(text) or re.search(r'\brk\b', text, re.I):
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


_SALE_INTENT_RE = re.compile(
    r'\b(move\s*out\s*sale|moving\s*out\s*sale|moving\s*sale|for\s+sale|selling)\b', re.I)
# A line like "Sofa- 10000" or "Study table -6500" or "Bed : 5000".
_ITEM_PRICE_RE = re.compile(r'^.{0,40}?[-:]\s*\d{3,6}\s*$', re.M)


def looks_like_sale(text: str) -> bool:
    """High-confidence goods-sale detector. Fires on sale INTENT or several
    '<item> - <price>' lines — never on appliance nouns alone (a furnished flat
    lists those too)."""
    t = text or ""
    if _SALE_INTENT_RE.search(t):
        return True
    return len(_ITEM_PRICE_RE.findall(t)) >= 2


def regex_extract(text: str) -> dict:
    """Offline best-effort extraction. Unfillable fields are None.
    location, available_from, notes are not reliably regex-able -> None."""
    text = text or ""
    return {
        "bhk": normalize_bhk(parse_bhk(text)),
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
