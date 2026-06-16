"""LLM cost accounting.

PRICES are USD per 1,000,000 tokens, as (input, output). VERIFY against each
provider's pricing page — they change often. An unknown model still has its
tokens tracked; only its dollar cost is reported as unknown.
"""

import threading

# ponytail: a plain dict, not a config file or API lookup. Edit here when prices move.
PRICES: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-5.1-codex-mini": (0.25, 2.00),
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-4.1-nano": (0.10, 0.40),
    # MiniMax (approx — verify on the MiniMax dashboard)
    "MiniMax-Text-01": (0.20, 1.10),
}


def price_for(model: str) -> tuple[float, float] | None:
    """(input, output) USD per 1M tokens for `model`, or None if unpriced."""
    if model in PRICES:
        return PRICES[model]
    lower = {k.lower(): v for k, v in PRICES.items()}
    return lower.get((model or "").lower())


def cost_usd(model: str, in_tok: int, out_tok: int) -> float | None:
    p = price_for(model)
    if p is None:
        return None
    return in_tok / 1_000_000 * p[0] + out_tok / 1_000_000 * p[1]


class CostTracker:
    """Accumulates token usage and dollar cost across many LLM calls."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_usd = 0.0
        self.unpriced_calls = 0
        self.models: set[str] = set()
        self._lock = threading.Lock()

    def add(self, model: str, in_tok: int, out_tok: int) -> None:
        c = cost_usd(model, int(in_tok or 0), int(out_tok or 0))
        with self._lock:
            self.calls += 1
            self.input_tokens += int(in_tok or 0)
            self.output_tokens += int(out_tok or 0)
            self.models.add(model)
            if c is None:
                self.unpriced_calls += 1
            else:
                self.cost_usd += c

    def summary(self) -> dict:
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 4),
            "unpriced_calls": self.unpriced_calls,
            "models": sorted(self.models),
        }

    def format(self) -> str:
        s = self.summary()
        unpriced = f" ({s['unpriced_calls']} unpriced — model not in PRICES)" if s["unpriced_calls"] else ""
        return (f"LLM cost | calls={s['calls']} in={s['input_tokens']} out={s['output_tokens']} "
                f"models={','.join(s['models']) or '-'} → ${s['cost_usd']:.4f}{unpriced}")
