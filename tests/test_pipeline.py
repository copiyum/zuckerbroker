import json
import pathlib
from househunt import pipeline, db
from househunt.config import Config

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _cfg(tmp_path):
    return Config("http://api.test/v1", "key", "model",
                  str(tmp_path / "t.db"), str(tmp_path / "imgs"))


def _fake_llm_from_fixture(text, c, tracker=None):
    """Minimal LLM stub for fixture posts (p1=2bhk 30k, p2=flatmate 12k)."""
    if "30k" in text or "2BHK" in text:
        return {"bhk": "2 BHK", "rent": 30000, "deposit": 60000, "maintenance": None,
                "location": None, "contact": "9876543210", "listing_type": "entire_flat",
                "furnishing": "furnished", "available_from": None, "notes": None,
                "post_kind": "offer"}
    return {"bhk": None, "rent": 12000, "deposit": None, "maintenance": None,
            "location": None, "contact": None, "listing_type": "flatmate",
            "furnishing": None, "available_from": None, "notes": None,
            "post_kind": "offer"}


def test_extract_post_keys_match_columns(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    def fake(text, c, tracker=None):
        return {k: None for k in pipeline.llm.FIELD_KEYS} | {"post_kind": "offer", "rent": 30000}
    monkeypatch.setattr(pipeline.llm, "llm_extract", fake)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "2bhk 30k", "images": []}, cfg)
    assert rec is not None
    # extract_post produces a subset of columns; the geocoder fills lat/lng/geo_precision later.
    assert set(rec.keys()) <= set(db.COLUMNS)
    assert {"id", "url", "rent", "post_kind"} <= set(rec.keys())
    assert rec["rent"] == 30000


def test_extract_post_normalizes_llm_bhk(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")  # has key -> llm path

    def fake_llm(text, c, tracker=None):
        return {"bhk": "2bhk", "rent": 30000, "deposit": None, "maintenance": None,
                "location": "HSR", "contact": None, "listing_type": "entire_flat",
                "furnishing": None, "available_from": None, "notes": None,
                "post_kind": "offer"}

    monkeypatch.setattr(pipeline.llm, "llm_extract", fake_llm)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "x", "images": []}, cfg)
    assert rec["bhk"] == "2 BHK"   # normalized, not "2bhk"


def test_sale_post_skips_llm_and_tags_sale(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")  # has key, but sale should skip LLM
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract",
                        lambda text, c, tracker=None: called.append(1) or {})
    post = {"id": "s1", "url": "U", "text": "Move out sale. Sofa 10000, fridge 5000", "images": []}
    rec = pipeline.extract_post(post, cfg)
    assert rec["post_kind"] == "sale"
    assert called == []  # LLM never called for an obvious sale


def test_normal_post_uses_llm_post_kind(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")

    def fake_llm(text, c, tracker=None):
        return {"bhk": "2 BHK", "rent": 30000, "deposit": None, "maintenance": None,
                "location": "HSR", "contact": None, "listing_type": "entire_flat",
                "furnishing": None, "available_from": None, "notes": None,
                "post_kind": "offer"}

    monkeypatch.setattr(pipeline.llm, "llm_extract", fake_llm)
    rec = pipeline.extract_post({"id": "n1", "url": "U", "text": "2bhk rent 30k", "images": []}, cfg)
    assert rec["post_kind"] == "offer"
    assert rec["listing_type"] == "entire_flat"


def test_extract_post_sale_has_null_fields(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract", lambda *a, **k: called.append(1) or {})
    rec = pipeline.extract_post({"id": "s", "url": "u",
                                 "text": "Move out sale. Sofa 10000, fridge 5000", "images": []}, cfg)
    assert rec["post_kind"] == "sale"
    assert rec["rent"] is None and rec["bhk"] is None and rec["location"] is None
    assert called == []


def test_extract_post_returns_none_on_llm_failure(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    def boom(text, c, tracker=None):
        raise RuntimeError("terminal")
    monkeypatch.setattr(pipeline.llm, "llm_extract", boom)
    assert pipeline.extract_post({"id": "x", "url": "u", "text": "2bhk 30k", "images": []}, cfg) is None


def test_run_skips_failed_posts_then_stores_on_retry(tmp_path, monkeypatch):
    cfg = Config("u", "key", "m", str(tmp_path / "t.db"), str(tmp_path / "i"))
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    raw = str(tmp_path / "raw.json")
    json.dump([{"id": "p1", "url": "u", "text": "2bhk 30k", "images": []}], open(raw, "w"))
    state = {"fail": True}
    def flaky(text, c, tracker=None):
        if state["fail"]:
            raise RuntimeError("429-ish")
        return {k: None for k in pipeline.llm.FIELD_KEYS} | {"post_kind": "offer", "rent": 30000}
    monkeypatch.setattr(pipeline.llm, "llm_extract", flaky)
    assert pipeline.run(raw, cfg, workers=2) == 0
    conn = db.connect(cfg.db_path)
    assert len(db.fetch_all(conn)) == 0
    state["fail"] = False
    assert pipeline.run(raw, cfg, workers=2) == 1
    conn = db.connect(cfg.db_path)
    assert db.fetch_all(conn)[0]["rent"] == 30000


def test_run_inserts_then_dedups(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    monkeypatch.setattr(pipeline.llm, "llm_extract", _fake_llm_from_fixture)
    raw = str(tmp_path / "raw.json")
    fixture = json.load(open(_FIXTURES / "sample_raw.json"))
    json.dump(fixture, open(raw, "w"))

    new1 = pipeline.run(raw, cfg)
    assert new1 == 2
    new2 = pipeline.run(raw, cfg)  # same data again
    assert new2 == 0  # all deduped

    conn = db.connect(cfg.db_path)
    rows = db.fetch_all(conn)
    assert len(rows) == 2


def test_run_only_downloads_images_for_new_posts(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    calls = []
    monkeypatch.setattr(pipeline, "download_images",
                        lambda pid, urls, d: calls.append(pid) or [])
    monkeypatch.setattr(pipeline.llm, "llm_extract", _fake_llm_from_fixture)
    raw = str(tmp_path / "raw.json")
    json.dump(json.load(open(_FIXTURES / "sample_raw.json")), open(raw, "w"))
    pipeline.run(raw, cfg)
    assert sorted(calls) == ["p1", "p2"]
    calls.clear()
    pipeline.run(raw, cfg)  # second run: nothing new
    assert calls == []


def test_run_parallel_stores_all_then_dedups(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    monkeypatch.setattr(pipeline.llm, "llm_extract", _fake_llm_from_fixture)
    raw = str(tmp_path / "raw.json")
    fixture = json.load(open(_FIXTURES / "sample_raw.json"))
    fixture = fixture + [{"id": "p3", "url": "https://fb.com/p3",
                          "text": "1 BHK rent 18k entire flat", "images": []}]
    json.dump(fixture, open(raw, "w"))

    assert pipeline.run(raw, cfg, workers=4) == 3
    assert pipeline.run(raw, cfg, workers=4) == 0  # resume/dedup
    conn = db.connect(cfg.db_path)
    assert len(db.fetch_all(conn)) == 3


def test_run_parallel_survives_one_failing_post(tmp_path, monkeypatch):
    cfg = Config("u", "key", "m", str(tmp_path / "t.db"), str(tmp_path / "imgs"))
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])

    def ok_llm(text, c, tracker=None):
        return {"bhk": None, "rent": 1, "deposit": None, "maintenance": None,
                "location": None, "contact": None, "listing_type": None,
                "furnishing": None, "available_from": None, "notes": None,
                "post_kind": "offer"}
    monkeypatch.setattr(pipeline.llm, "llm_extract", ok_llm)

    real_extract = pipeline.extract_post
    def maybe_raise(post, c, tracker=None):
        if post.get("id") == "bad":
            raise RuntimeError("worker blew up")
        return real_extract(post, c, tracker=tracker)
    monkeypatch.setattr(pipeline, "extract_post", maybe_raise)

    raw = str(tmp_path / "raw.json")
    json.dump([{"id": "ok1", "url": "u", "text": "x", "images": []},
               {"id": "bad", "url": "u", "text": "x", "images": []},
               {"id": "ok2", "url": "u", "text": "x", "images": []}], open(raw, "w"))
    n = pipeline.run(raw, cfg, workers=4)
    assert n == 2
    conn = db.connect(cfg.db_path)
    assert {r["id"] for r in db.fetch_all(conn)} == {"ok1", "ok2"}


def test_extract_post_blank_text_tagged_other_no_llm(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract", lambda *a, **k: called.append(1) or {})
    for blank in ("", "   ", "\n\t "):
        rec = pipeline.extract_post({"id": "b", "url": "u", "text": blank, "images": []}, cfg)
        assert rec is not None and rec["post_kind"] == "other"
        assert rec["rent"] is None and rec["bhk"] is None
    assert called == []  # blank posts never hit the LLM (no 400, never retried)
