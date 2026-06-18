import json
import types

import pytest

from househunt import llm
from househunt.config import Config


def _cfg():
    return Config("http://api.test/v1", "key", "model", "x.db", "images")


def _codex_cfg():
    return Config("http://api.test/v1", "key", "gpt-5.1-codex-mini", "x.db", "images")


class _Usage:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _fake_chat_client(content, usage=None):
    msg = types.SimpleNamespace(message=types.SimpleNamespace(content=content))
    resp = types.SimpleNamespace(choices=[msg], usage=usage)
    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: resp)),
        responses=types.SimpleNamespace(create=lambda **kw: (_ for _ in ()).throw(
            AssertionError("chat model must not hit responses"))),
    )
    return client


def _fake_responses_client(output_text, usage=None, capture=None):
    resp = types.SimpleNamespace(output_text=output_text, usage=usage)
    def create(**kw):
        if capture is not None:
            capture.update(kw)
        return resp
    client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=create),
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(
            create=lambda **kw: (_ for _ in ()).throw(
                AssertionError("codex model must not hit chat")))),
    )
    return client


def test_chat_extract_parses_and_records_usage(monkeypatch):
    payload = {"rent": 45000, "location": "HSR", "post_kind": "offer"}
    client = _fake_chat_client(json.dumps(payload), usage=_Usage(prompt_tokens=100, completion_tokens=20))
    monkeypatch.setattr(llm, "_client", lambda base, key: client)
    from househunt.cost import CostTracker
    t = CostTracker()
    out = llm.llm_extract("3bhk hsr 45k", _cfg(), tracker=t)
    assert out["rent"] == 45000 and out["location"] == "HSR" and out["post_kind"] == "offer"
    s = t.summary()
    assert s["input_tokens"] == 100 and s["output_tokens"] == 20


def test_chat_extract_strips_code_fence(monkeypatch):
    client = _fake_chat_client("```json\n{\"rent\": 10000}\n```")
    monkeypatch.setattr(llm, "_client", lambda base, key: client)
    assert llm.llm_extract("x", _cfg())["rent"] == 10000


def test_chat_extract_handles_preamble(monkeypatch):
    client = _fake_chat_client("Sure! Here:\n```json\n{\"rent\": 4500}\n```")
    monkeypatch.setattr(llm, "_client", lambda base, key: client)
    assert llm.llm_extract("x", _cfg())["rent"] == 4500


def test_codex_uses_responses_endpoint(monkeypatch):
    cap = {}
    client = _fake_responses_client('{"rent": 22000, "bhk": "1 BHK"}',
                                    usage=_Usage(input_tokens=200, output_tokens=50), capture=cap)
    monkeypatch.setattr(llm, "_client", lambda base, key: client)
    from househunt.cost import CostTracker
    t = CostTracker()
    out = llm.llm_extract("1bhk 22k", _codex_cfg(), tracker=t)
    assert out["rent"] == 22000 and out["bhk"] == "1 BHK"
    assert cap["instructions"] == llm.SYSTEM_PROMPT
    assert cap["input"] == "1bhk 22k"
    assert cap["max_output_tokens"] == 2000   # generous cap so JSON never truncates
    s = t.summary()
    assert s["input_tokens"] == 200 and s["output_tokens"] == 50


def test_llm_returns_post_kind_and_pg_hostel(monkeypatch):
    client = _fake_chat_client(json.dumps({"post_kind": "offer", "listing_type": "pg_hostel"}))
    monkeypatch.setattr(llm, "_client", lambda base, key: client)
    out = llm.llm_extract("pg 12k", _cfg())
    assert out["post_kind"] == "offer" and out["listing_type"] == "pg_hostel"
    assert "post_kind" in llm.FIELD_KEYS


def test_llm_extract_raises_on_sdk_error(monkeypatch):
    def boom(base, key):
        raise RuntimeError("network down")
    monkeypatch.setattr(llm, "_client", boom)
    with pytest.raises(RuntimeError):
        llm.llm_extract("x", _cfg())
