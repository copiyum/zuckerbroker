import re

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


_SALE_INTENT_RE = re.compile(
    r'\b(move\s*out\s*sale|moving\s*out\s*sale|moving\s*sale|for\s+sale|selling)\b', re.I)
# A line like "Sofa- 10000" or "Study table -6500" or "Bed : 5000".
_ITEM_PRICE_RE = re.compile(r'^.{0,40}?[-:]\s*\d{3,6}\s*$', re.M)
# Rental-finance labels: "Rent: 15000" / "Deposit - 50000" are NOT goods-for-sale lines.
# Without this, any flatmate post listing rent+deposit got mis-tagged 'sale' and skipped the LLM.
_RENT_LABEL_RE = re.compile(
    r'\b(rent|deposit|dep|advance|adv|maint\w*|brokerage|token|security|budget|sq\.?\s?ft|carpet)\b',
    re.I)


def looks_like_sale(text: str) -> bool:
    """High-confidence goods-sale detector. Fires on sale INTENT or several
    '<item> - <price>' lines — never on appliance nouns alone (a furnished flat
    lists those too), and never on rent/deposit lines (those are listing terms)."""
    t = text or ""
    if _SALE_INTENT_RE.search(t):
        return True
    item_lines = [ln for ln in _ITEM_PRICE_RE.findall(t) if not _RENT_LABEL_RE.search(ln)]
    return len(item_lines) >= 2


# Female-restricted listing signals (broker phrasing varies wildly).
_FEMALE_ONLY_RE = re.compile(
    r'female\s+(flat\s?mate|room\s?mate|replacement|tenant|candidate|preferred)'
    r'|(?:females?|girls?|ladies|women)\s+only'
    r'|only\s+(?:females?|girls?|ladies)'
    r'|for\s+females?\b'
    r'|female\s+preferr?ed', re.I)
# Overrides that mean the listing is open to anyone.
_ANY_GENDER_RE = re.compile(
    r'\b(male\s*/?\s*&?\s*female|female\s*/?\s*&?\s*male|any\s+gender|gender\s+no\s+bar'
    r'|boys?\s+(?:and|&|or)\s+girls?|girls?\s+(?:and|&|or)\s+boys?'
    r'|male\s+or\s+female|female\s+or\s+male)\b', re.I)


def classify_audience(text: str | None) -> str:
    """'female_only' if the post restricts to women (and isn't explicitly open to all),
    else 'any'. Used to let users filter out listings they can't take."""
    t = text or ""
    if _FEMALE_ONLY_RE.search(t) and not _ANY_GENDER_RE.search(t):
        return "female_only"
    return "any"
