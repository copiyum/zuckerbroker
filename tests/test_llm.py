import json
from househunt import llm
from househunt.config import Config


def _cfg():
    return Config("http://api.test/v1", "key", "model", "x.db", "images")


def test_llm_extract_parses_json_content(monkeypatch):
    payload = {"bhk": "3 BHK", "rent": 45000, "deposit": 90000,
               "maintenance": 3000, "location": "HSR", "contact": "9876543210",
               "listing_type": "entire_flat", "furnishing": "semi_furnished",
               "available_from": "2026-07-01", "notes": "no brokers"}

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["auth"] = headers["Authorization"]
        return FakeResp()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    out = llm.llm_extract("3bhk hsr 45k", _cfg())
    assert out["rent"] == 45000
    assert out["location"] == "HSR"
    assert captured["url"] == "http://api.test/v1/chat/completions"
    assert captured["auth"] == "Bearer key"


def test_llm_extract_strips_code_fence(monkeypatch):
    fenced = "```json\n{\"rent\": 10000}\n```"

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": fenced}}]}

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    out = llm.llm_extract("x", _cfg())
    assert out["rent"] == 10000


def test_llm_extract_handles_preamble_before_fence(monkeypatch):
    content = "Sure! Here you go:\n```json\n{\"rent\": 45000}\n```"

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    out = llm.llm_extract("x", _cfg())
    assert out["rent"] == 45000


def test_llm_extract_handles_bare_json(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"rent": 7000}'}}]}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    out = llm.llm_extract("x", _cfg())
    assert out["rent"] == 7000


def _codex_cfg():
    return Config("http://api.test/v1", "key", "gpt-5.1-codex-mini", "x.db", "images")


def test_codex_model_uses_responses_endpoint(monkeypatch):
    # Responses API shape: output is a list of items; text is in output_text segments.
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"output": [
                {"type": "reasoning", "content": []},
                {"type": "message", "content": [
                    {"type": "output_text", "text": '{"rent": 22000, "bhk": "1 BHK"}'}]},
            ]}

    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["body"] = json
        captured["auth"] = headers["Authorization"]
        return FakeResp()

    monkeypatch.setattr(llm.requests, "post", fake_post)
    out = llm.llm_extract("1bhk 22k", _codex_cfg())
    assert out["rent"] == 22000
    assert out["bhk"] == "1 BHK"
    assert captured["url"] == "http://api.test/v1/responses"   # NOT /chat/completions
    assert captured["auth"] == "Bearer key"
    assert captured["body"]["instructions"] == llm.SYSTEM_PROMPT
    assert captured["body"]["input"] == "1bhk 22k"
    assert "messages" not in captured["body"]          # responses shape, not chat


def test_codex_responses_output_text_convenience_field(monkeypatch):
    # Some responses payloads include a top-level aggregated `output_text`.
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"output_text": '{"rent": 9000}', "output": []}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    out = llm.llm_extract("x", _codex_cfg())
    assert out["rent"] == 9000


def test_llm_extract_records_chat_usage_to_tracker(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": '{"rent": 1}'}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20}}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    from househunt.cost import CostTracker
    t = CostTracker()
    llm.llm_extract("x", _cfg(), tracker=t)
    s = t.summary()
    assert s["calls"] == 1 and s["input_tokens"] == 100 and s["output_tokens"] == 20


def test_llm_extract_records_responses_usage_to_tracker(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"output_text": '{"rent": 1}',
                    "usage": {"input_tokens": 200, "output_tokens": 50}}
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    from househunt.cost import CostTracker
    t = CostTracker()
    llm.llm_extract("x", _codex_cfg(), tracker=t)
    s = t.summary()
    assert s["input_tokens"] == 200 and s["output_tokens"] == 50


def test_llm_returns_post_kind(monkeypatch):
    payload = {"post_kind": "offer", "listing_type": "pg_hostel", "rent": 12000}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps(payload)}}]}

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: FakeResp())
    out = llm.llm_extract("pg available 12k", _cfg())
    assert out["post_kind"] == "offer"
    assert out["listing_type"] == "pg_hostel"
    assert "post_kind" in llm.FIELD_KEYS
