from househunt import config


def test_defaults_when_env_unset(monkeypatch):
    for k in ("LLM_BACKEND", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
              "MINIMAX_API_KEY", "HOUSEHUNT_DB", "HOUSEHUNT_IMAGES"):
        monkeypatch.delenv(k, raising=False)
    cfg = config.load_config()
    assert cfg.llm_backend == "mlx"
    assert cfg.llm_base_url.startswith("http")
    assert cfg.llm_api_key is None
    assert cfg.db_path == "listings.db"
    assert cfg.images_dir == "images"


def test_minimax_key_autodetects_openai(monkeypatch):
    for k in ("LLM_BACKEND", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "mk-test")
    cfg = config.load_config()
    assert cfg.llm_backend == "openai"
    assert cfg.llm_api_key == "mk-test"
    assert cfg.llm_model == "MiniMax-Text-01"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("HOUSEHUNT_DB", "x.db")
    cfg = config.load_config()
    assert cfg.llm_api_key == "secret"
    assert cfg.llm_model == "custom-model"
    assert cfg.db_path == "x.db"
