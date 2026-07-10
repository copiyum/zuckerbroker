import os
from dataclasses import dataclass

# NOTE: confirm exact MiniMax base URL + model from your MiniMax dashboard.
# These defaults are the documented OpenAI-compatible endpoint; override via env.
DEFAULT_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MODEL = "MiniMax-Text-01"
# Local on-device MLX model (4-bit). Cloned to ./Qwen2.5-3B-Instruct-4bit.
DEFAULT_MLX_MODEL = "Qwen2.5-3B-Instruct-4bit"
# Vertex AI defaults (Google Cloud)
DEFAULT_VERTEX_MODEL = "gemini-2.5-flash"
DEFAULT_VERTEX_LOCATION = "us-central1"


@dataclass(frozen=True)
class Config:
    llm_base_url: str
    llm_api_key: str | None
    llm_model: str
    db_path: str
    images_dir: str
    # "mlx" -> local on-device Qwen via mlx_lm;
    # "openai" -> remote OpenAI-compatible SDK (MiniMax, ollama, OpenAI, etc.);
    # "vertex" -> Vertex AI via google-genai SDK (Gemini models, service account auth).
    # Defaults to "openai" so direct Config(...) construction in tests hits the mocked SDK
    # path; load_config() defaults a real run to "mlx".
    llm_backend: str = "openai"
    # Vertex AI-specific fields (only used when llm_backend == "vertex")
    vertex_project_id: str | None = None
    vertex_location: str = DEFAULT_VERTEX_LOCATION


def load_config() -> Config:
    # Explicit backend always wins. Otherwise auto-detect in priority order:
    #   - LLM_MODEL with a colon (e.g. "qwen2.5:3b") is an ollama tag -> openai path
    #   - MINIMAX_API_KEY in env -> remote MiniMax via openai-compatible SDK
    #   - GOOGLE_GENAI_USE_VERTEXAI or (GOOGLE_APPLICATION_CREDENTIALS + VERTEX_PROJECT_ID)
    #     -> Vertex AI via google-genai
    #   - else -> on-device MLX
    model_env = os.environ.get("LLM_MODEL")
    if os.environ.get("LLM_BACKEND"):
        backend = os.environ.get("LLM_BACKEND")
    elif model_env and ":" in model_env:
        backend = "openai"
    elif os.environ.get("MINIMAX_API_KEY") or os.environ.get("LLM_API_KEY"):
        backend = "openai"
    elif (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "true"
          or (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
              and os.environ.get("VERTEX_PROJECT_ID"))):
        backend = "vertex"
    else:
        backend = "mlx"
    return Config(
        llm_base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        llm_api_key=(os.environ.get("LLM_API_KEY")
                     or os.environ.get("MINIMAX_API_KEY") or None),
        llm_model=os.environ.get(
            "LLM_MODEL",
            (DEFAULT_VERTEX_MODEL if backend == "vertex"
             else DEFAULT_MLX_MODEL if backend == "mlx"
             else DEFAULT_MODEL)),
        db_path=os.environ.get("HOUSEHUNT_DB", "listings.db"),
        images_dir=os.environ.get("HOUSEHUNT_IMAGES", "images"),
        llm_backend=backend,
        vertex_project_id=os.environ.get("VERTEX_PROJECT_ID"),
        vertex_location=os.environ.get("VERTEX_LOCATION", DEFAULT_VERTEX_LOCATION),
    )
