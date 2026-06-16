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


def _headers(cfg: Config) -> dict:
    return {"Authorization": f"Bearer {cfg.llm_api_key}", "Content-Type": "application/json"}


def _use_responses(model: str) -> bool:
    """Codex models are served ONLY on /v1/responses, not /chat/completions."""
    return "codex" in model.lower()


def _chat_extract(text: str, cfg: Config) -> str:
    """OpenAI-compatible /chat/completions. Returns the raw message content."""
    resp = requests.post(
        f"{cfg.llm_base_url}/chat/completions",
        headers=_headers(cfg),
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
    return resp.json()["choices"][0]["message"]["content"]


def _responses_output_text(data: dict) -> str:
    """Pull the assistant text out of a /v1/responses payload.
    Prefers the aggregated `output_text`, else concatenates output_text segments
    from message items (ignoring reasoning items that codex models emit)."""
    if isinstance(data.get("output_text"), str) and data["output_text"]:
        return data["output_text"]
    parts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    parts.append(c.get("text", ""))
    return "".join(parts)


def _responses_extract(text: str, cfg: Config) -> str:
    """OpenAI /v1/responses (codex models). System prompt → `instructions`,
    user text → `input`. No `temperature` (codex/reasoning models reject it)."""
    resp = requests.post(
        f"{cfg.llm_base_url}/responses",
        headers=_headers(cfg),
        json={
            "model": cfg.llm_model,
            "instructions": SYSTEM_PROMPT,
            "input": text or "",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return _responses_output_text(resp.json())


def llm_extract(text: str, cfg: Config) -> dict:
    """Extract the field dict via the LLM. Routes codex models to /v1/responses,
    everything else to /chat/completions. Raises on HTTP/parse error so the
    caller can fall back to regex."""
    content = _responses_extract(text, cfg) if _use_responses(cfg.llm_model) else _chat_extract(text, cfg)
    return _parse_content(content)
