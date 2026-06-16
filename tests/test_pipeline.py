import json
import pathlib
from househunt import pipeline, db
from househunt.config import Config

_FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _cfg(tmp_path):
    return Config("http://api.test/v1", None, "model",  # no api key -> regex path
                  str(tmp_path / "t.db"), str(tmp_path / "imgs"))


def test_extract_post_regex_path_builds_full_record():
    cfg = Config("u", None, "m", "d", "i")  # no key
    post = {"id": "p1", "url": "U", "text": "2bhk rent 30k entire flat", "images": []}
    rec = pipeline.extract_post(post, cfg)
    assert rec["id"] == "p1"
    assert rec["url"] == "U"
    assert rec["rent"] == 30000
    assert rec["listing_type"] == "entire_flat"
    assert rec["scraped_at"]  # set
    # all db columns present
    assert set(rec.keys()) == set(db.COLUMNS)


def test_extract_post_llm_failure_falls_back_to_regex(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")  # has key -> tries llm first
    def boom(text, c):
        raise RuntimeError("api down")
    monkeypatch.setattr(pipeline.llm, "llm_extract", boom)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "rent 9k", "images": []}, cfg)
    assert rec["rent"] == 9000  # regex fallback worked


def test_run_inserts_then_dedups(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    # stub image download to avoid network
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
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
    raw = str(tmp_path / "raw.json")
    json.dump(json.load(open(_FIXTURES / "sample_raw.json")), open(raw, "w"))
    pipeline.run(raw, cfg)
    assert sorted(calls) == ["p1", "p2"]
    calls.clear()
    pipeline.run(raw, cfg)  # second run: nothing new
    assert calls == []


def test_extract_post_normalizes_llm_bhk(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")  # has key -> llm path

    def fake_llm(text, c, tracker=None):
        return {"bhk": "2bhk", "rent": 30000, "deposit": None, "maintenance": None,
                "location": "HSR", "contact": None, "listing_type": "entire_flat",
                "furnishing": None, "available_from": None, "notes": None}

    monkeypatch.setattr(pipeline.llm, "llm_extract", fake_llm)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "x", "images": []}, cfg)
    assert rec["bhk"] == "2 BHK"   # normalized, not "2bhk"
