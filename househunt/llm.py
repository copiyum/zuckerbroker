import json
import re
import requests

from .config import Config

FIELD_KEYS = ["bhk", "rent", "deposit", "maintenance", "location", "contact",
              "listing_type", "post_kind", "furnishing", "available_from", "notes"]

SYSTEM_PROMPT = (
    "You extract structured rental-listing data from messy Facebook group posts "
    "(often bilingual English/Hindi/regional). Return ONLY a JSON object with these keys: "
    + ", ".join(FIELD_KEYS) + ". Rules: rent/deposit/maintenance are integer rupees per month "
    "(convert '32k' -> 32000, '1L'/'1 lakh' -> 100000), or null if absent. "
    "listing_type is one of 'entire_flat', 'flatmate', 'private_room', 'pg_hostel', or null; "
    "if the post seeks a flatmate/roommate or offers a room within a shared flat, use 'flatmate'; "
    "use 'pg_hostel' for paying-guest or hostel listings. "
    "post_kind is one of 'offer' (someone offering a place to rent or a PG), "
    "'wanted' (someone seeking a place to live), 'sale' (selling goods/furniture/electronics), "
    "or 'other' (complaints, ads, discussion, anything not a rental). "
    "Return bhk as 'N BHK' (e.g. '2 BHK'), '1 RK', or 'Studio'. "
    "contact is a phone number string or null. "
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


def _usage(data: dict) -> tuple[int, int]:
    """(input_tokens, output_tokens) from a chat OR responses payload, 0 if absent."""
    u = data.get("usage") or {}
    in_tok = u.get("prompt_tokens", u.get("input_tokens", 0)) or 0
    out_tok = u.get("completion_tokens", u.get("output_tokens", 0)) or 0
    return int(in_tok), int(out_tok)


def _chat_extract(text: str, cfg: Config) -> tuple[str, tuple[int, int]]:
    """OpenAI-compatible /chat/completions. Returns (content, (in_tok, out_tok))."""
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
    data = resp.json()
    return data["choices"][0]["message"]["content"], _usage(data)


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


def _responses_extract(text: str, cfg: Config) -> tuple[str, tuple[int, int]]:
    """OpenAI /v1/responses (codex models). System prompt → `instructions`,
    user text → `input`. No `temperature` (codex/reasoning models reject it).
    Returns (content, (in_tok, out_tok))."""
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
    data = resp.json()
    return _responses_output_text(data), _usage(data)


def llm_extract(text: str, cfg: Config, tracker=None) -> dict:
    """Extract the field dict via the LLM. Routes codex models to /v1/responses,
    everything else to /chat/completions. If `tracker` (cost.CostTracker) is given,
    records token usage. Raises on HTTP/parse error so the caller can fall back."""
    if _use_responses(cfg.llm_model):
        content, usage = _responses_extract(text, cfg)
    else:
        content, usage = _chat_extract(text, cfg)
    if tracker is not None:
        tracker.add(cfg.llm_model, usage[0], usage[1])
    return _parse_content(content)
