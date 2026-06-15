import os
from dataclasses import dataclass

# NOTE: confirm exact MiniMax base URL + model from your MiniMax dashboard.
# These defaults are the documented OpenAI-compatible endpoint; override via env.
DEFAULT_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MODEL = "MiniMax-Text-01"


@dataclass(frozen=True)
class Config:
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    db_path: str
    images_dir: str


def load_config() -> Config:
    return Config(
        llm_base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        llm_api_key=os.environ.get("LLM_API_KEY") or None,
        llm_model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        db_path=os.environ.get("HOUSEHUNT_DB", "listings.db"),
        images_dir=os.environ.get("HOUSEHUNT_IMAGES", "images"),
    )
