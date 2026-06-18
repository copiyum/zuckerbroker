import functools
import json
import re

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


@functools.lru_cache(maxsize=8)
def _client(base_url: str, api_key: str):
    """Cached OpenAI SDK client. max_retries handles 429/5xx with backoff + Retry-After."""
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url, max_retries=5)


def _use_responses(model: str) -> bool:
    """Codex models are served ONLY on /v1/responses, not /chat/completions."""
    return "codex" in model.lower()


def _usage(usage) -> tuple[int, int]:
    """(input_tokens, output_tokens) from an SDK usage object (chat or responses)."""
    if not usage:
        return 0, 0
    in_tok = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0) or 0
    return int(in_tok), int(out_tok)


def llm_extract(text: str, cfg: Config, tracker=None) -> dict:
    """Extract the field dict via the OpenAI SDK. Codex -> responses, else chat.
    The SDK retries 429/5xx with backoff. Raises on terminal failure (caller skips)."""
    client = _client(cfg.llm_base_url, cfg.llm_api_key)
    if _use_responses(cfg.llm_model):
        resp = client.responses.create(
            model=cfg.llm_model, instructions=SYSTEM_PROMPT, input=text or "",
            max_output_tokens=2000)  # reasoning + JSON must fit, else output truncates mid-JSON
        content = resp.output_text
    else:
        resp = client.chat.completions.create(
            model=cfg.llm_model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": text or ""}],
            temperature=0)
        content = resp.choices[0].message.content
    if tracker is not None:
        in_tok, out_tok = _usage(getattr(resp, "usage", None))
        tracker.add(cfg.llm_model, in_tok, out_tok)
    return _parse_content(content)
