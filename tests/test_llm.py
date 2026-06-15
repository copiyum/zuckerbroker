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
