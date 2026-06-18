import json
import pathlib
from househunt import pipeline, db, dedup
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


# ---- extract_post (classification) ----------------------------------------

def test_extract_post_keys_match_columns(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    def fake(text, c, tracker=None):
        return {k: None for k in pipeline.llm.FIELD_KEYS} | {"post_kind": "offer", "rent": 30000}
    monkeypatch.setattr(pipeline.llm, "llm_extract", fake)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "2bhk 30k"}, cfg)
    assert rec is not None
    assert set(rec.keys()) <= set(db.COLUMNS)
    assert {"id", "url", "rent", "post_kind"} <= set(rec.keys())
    assert rec["rent"] == 30000


def test_extract_post_normalizes_llm_bhk(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")

    def fake_llm(text, c, tracker=None):
        return {"bhk": "2bhk", "rent": 30000, "deposit": None, "maintenance": None,
                "location": "HSR", "contact": None, "listing_type": "entire_flat",
                "furnishing": None, "available_from": None, "notes": None,
                "post_kind": "offer"}

    monkeypatch.setattr(pipeline.llm, "llm_extract", fake_llm)
    rec = pipeline.extract_post({"id": "p1", "url": "U", "text": "x"}, cfg)
    assert rec["bhk"] == "2 BHK"


def test_sale_post_skips_llm_and_tags_sale(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract",
                        lambda text, c, tracker=None: called.append(1) or {})
    rec = pipeline.extract_post({"id": "s1", "url": "U",
                                 "text": "Move out sale. Sofa 10000, fridge 5000"}, cfg)
    assert rec["post_kind"] == "sale"
    assert called == []


def test_normal_post_uses_llm_post_kind(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")

    def fake_llm(text, c, tracker=None):
        return {"bhk": "2 BHK", "rent": 30000, "deposit": None, "maintenance": None,
                "location": "HSR", "contact": None, "listing_type": "entire_flat",
                "furnishing": None, "available_from": None, "notes": None,
                "post_kind": "offer"}

    monkeypatch.setattr(pipeline.llm, "llm_extract", fake_llm)
    rec = pipeline.extract_post({"id": "n1", "url": "U", "text": "2bhk rent 30k"}, cfg)
    assert rec["post_kind"] == "offer"
    assert rec["listing_type"] == "entire_flat"


def test_extract_post_sale_has_null_fields(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract", lambda *a, **k: called.append(1) or {})
    rec = pipeline.extract_post({"id": "s", "url": "u",
                                 "text": "Move out sale. Sofa 10000, fridge 5000"}, cfg)
    assert rec["post_kind"] == "sale"
    assert rec["rent"] is None and rec["bhk"] is None and rec["location"] is None
    assert called == []


def test_extract_post_returns_none_on_llm_failure(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    def boom(text, c, tracker=None):
        raise RuntimeError("terminal")
    monkeypatch.setattr(pipeline.llm, "llm_extract", boom)
    assert pipeline.extract_post({"id": "x", "url": "u", "text": "2bhk 30k"}, cfg) is None


def test_extract_post_blank_text_tagged_other_no_llm(monkeypatch):
    cfg = Config("u", "key", "m", "d", "i")
    called = []
    monkeypatch.setattr(pipeline.llm, "llm_extract", lambda *a, **k: called.append(1) or {})
    for blank in ("", "   ", "\n\t "):
        rec = pipeline.extract_post({"id": "b", "url": "u", "text": blank}, cfg)
        assert rec is not None and rec["post_kind"] == "other"
        assert rec["rent"] is None and rec["bhk"] is None
    assert called == []


# ---- ingest stage (no LLM) -------------------------------------------------

def test_ingest_stores_raw_rows_without_llm(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    called = []
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    monkeypatch.setattr(pipeline.llm, "llm_extract", lambda *a, **k: called.append(1) or {})
    raw = str(tmp_path / "raw.json")
    json.dump(json.load(open(_FIXTURES / "sample_raw.json")), open(raw, "w"))
    assert pipeline.ingest(raw, cfg) == 2
    assert called == []  # ingest never touches the LLM
    rows = db.fetch_all(db.connect(cfg.db_path))
    assert len(rows) == 2
    assert all(r["post_kind"] is None for r in rows)  # not yet extracted


def test_ingest_is_resumable_by_id(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    calls = []
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: calls.append(pid) or [])
    raw = str(tmp_path / "raw.json")
    json.dump(json.load(open(_FIXTURES / "sample_raw.json")), open(raw, "w"))
    assert pipeline.ingest(raw, cfg) == 2
    assert sorted(calls) == ["p1", "p2"]
    calls.clear()
    assert pipeline.ingest(raw, cfg) == 0  # second run: nothing new, no downloads
    assert calls == []


def test_ingest_survives_one_failing_download(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)

    def flaky_dl(pid, urls, d):
        if pid == "bad":
            raise RuntimeError("download blew up")
        return []
    monkeypatch.setattr(pipeline, "download_images", flaky_dl)
    raw = str(tmp_path / "raw.json")
    json.dump([{"id": "ok1", "url": "u", "text": "x", "images": []},
               {"id": "bad", "url": "u", "text": "x", "images": []},
               {"id": "ok2", "url": "u", "text": "x", "images": []}], open(raw, "w"))
    assert pipeline.ingest(raw, cfg, workers=4) == 2
    assert {r["id"] for r in db.fetch_all(db.connect(cfg.db_path))} == {"ok1", "ok2"}


# ---- extract stage (LLM, after dedup) -------------------------------------

def test_extract_fills_canonical_and_is_resumable(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    monkeypatch.setattr(pipeline.llm, "llm_extract", _fake_llm_from_fixture)
    raw = str(tmp_path / "raw.json")
    json.dump(json.load(open(_FIXTURES / "sample_raw.json")), open(raw, "w"))
    pipeline.ingest(raw, cfg)
    assert pipeline.extract(cfg) == 2          # both filled (no dedup -> is_canonical NULL)
    conn = db.connect(cfg.db_path)
    assert {r["rent"] for r in db.fetch_all(conn)} == {30000, 12000}
    assert pipeline.extract(cfg) == 0          # resume: post_kind now set, nothing to do


def test_extract_skips_failed_then_fills_on_retry(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: [])
    raw = str(tmp_path / "raw.json")
    json.dump([{"id": "p1", "url": "u", "text": "2bhk 30k", "images": []}], open(raw, "w"))
    pipeline.ingest(raw, cfg)
    state = {"fail": True}
    def flaky(text, c, tracker=None):
        if state["fail"]:
            raise RuntimeError("429-ish")
        return {k: None for k in pipeline.llm.FIELD_KEYS} | {"post_kind": "offer", "rent": 30000}
    monkeypatch.setattr(pipeline.llm, "llm_extract", flaky)
    assert pipeline.extract(cfg) == 0          # LLM failed -> not filled
    assert db.fetch_all(db.connect(cfg.db_path))[0]["post_kind"] is None  # row still there, unfilled
    state["fail"] = False
    assert pipeline.extract(cfg) == 1
    assert db.fetch_all(db.connect(cfg.db_path))[0]["rent"] == 30000


def test_extract_skips_reposts(tmp_path, monkeypatch):
    """The cost win: dedup marks a repost is_canonical=0, extract must not LLM it."""
    cfg = _cfg(tmp_path)
    conn = db.connect(cfg.db_path)
    db.init_db(conn)
    # two rows pre-marked: one canonical, one repost (as dedup would leave them)
    for cid, canon in (("keep", 1), ("dupe", 0)):
        conn.execute("insert into listings (id, text, images, is_canonical, dup_group) "
                     "values (?, '2bhk 30k', '[]', ?, 'keep')", (cid, canon))
    conn.commit()
    seen = []
    def spy_llm(text, c, tracker=None):
        seen.append(1)
        return {k: None for k in pipeline.llm.FIELD_KEYS} | {"post_kind": "offer", "rent": 30000}
    monkeypatch.setattr(pipeline.llm, "llm_extract", spy_llm)
    assert pipeline.extract(cfg) == 1          # only the canonical row
    assert len(seen) == 1
    rows = {r["id"]: r for r in db.fetch_all(conn)}
    assert rows["keep"]["post_kind"] == "offer"
    assert rows["dupe"]["post_kind"] is None   # repost never extracted


def test_full_flow_ingest_dedup_extract(tmp_path, monkeypatch):
    """End-to-end staged order with one repost sharing 2 photos."""
    import numpy as np
    from PIL import Image
    for n, seed in (("a", 1), ("b", 2)):
        rng = np.random.default_rng(seed)
        Image.fromarray((rng.random((64, 64, 3)) * 255).astype("uint8")).save(tmp_path / f"{n}.png")
    cfg = _cfg(tmp_path)
    # real image download stub: just echo the fixed local files
    monkeypatch.setattr(pipeline, "download_images", lambda pid, urls, d: ["a.png", "b.png"])
    monkeypatch.setattr(pipeline.llm, "llm_extract", _fake_llm_from_fixture)
    raw = str(tmp_path / "raw.json")
    json.dump([{"id": "orig", "url": "u", "text": "2BHK 30k", "images": ["x", "y"]},
               {"id": "repost", "url": "u", "text": "2BHK 30k", "images": ["x", "y"]}], open(raw, "w"))
    assert pipeline.ingest(raw, cfg) == 2
    dedup.run(cfg.db_path, images_dir=str(tmp_path))
    n_filled = pipeline.extract(cfg)
    assert n_filled == 1                       # repost skipped -> half the LLM calls
    conn = db.connect(cfg.db_path)
    canon = [r for r in db.fetch_all(conn) if r["is_canonical"] == 1]
    assert len(canon) == 1 and canon[0]["post_kind"] == "offer"
