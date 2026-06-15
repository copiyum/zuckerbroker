import json
import re
import requests

from .config import Config

FIELD_KEYS = ["bhk", "rent", "deposit", "maintenance", "location", "contact",
              "listing_type", "furnishing", "available_from", "notes"]

SYSTEM_PROMPT = (
    "You extract structured rental-listing data from messy Facebook group posts "
    "(often bilingual English/Hindi/regional). Return ONLY a JSON object with these keys: "
    + ", ".join(FIELD_KEYS) + ". Rules: rent/deposit/maintenance are integer rupees per month "
    "(convert '32k' -> 32000), or null if absent. listing_type is one of "
    "'entire_flat', 'flatmate', 'private_room', or null. contact is a phone number string or null. "
    "Use null for any field not present. Do not invent values."
)

_FENCED_RE = re.compile(r'```(?:json)?\s*\n(.*?)\n\s*```', re.I | re.DOTALL)
_BARE_OBJ_RE = re.compile(r'\{.*\}', re.DOTALL)


def _parse_content(content: str) -> dict:
    # Try to extract from a ```json ... ``` (or ``` ... ```) fence anywhere in the string.
    m = _FENCED_RE.search(content)
    if m:
        raw = m.group(1)
    else:
        # Fall back to the first bare {...} block in the response.
        m = _BARE_OBJ_RE.search(content)
        if not m:
            raise ValueError(f"No JSON found in LLM response: {content!r}")
        raw = m.group(0)
    data = json.loads(raw)
    return {k: data.get(k) for k in FIELD_KEYS}


def llm_extract(text: str, cfg: Config) -> dict:
    """Call an OpenAI-compatible chat endpoint; return the field dict.
    Raises on HTTP error or unparseable content (caller handles fallback)."""
    resp = requests.post(
        f"{cfg.llm_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.llm_api_key}",
                 "Content-Type": "application/json"},
        json={
            "model": cfg.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text or ""},
            ],
            "temperature": 0,
        },
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_content(content)
