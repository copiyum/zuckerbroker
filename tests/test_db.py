from househunt import db


def _record(id="p1", **over):
    rec = {
        "id": id, "url": "u", "text": "t", "bhk": "2 BHK", "rent": 30000,
        "deposit": 60000, "maintenance": 2000, "location": "Koramangala",
        "contact": "9999999999", "listing_type": "entire_flat",
        "post_kind": "offer", "furnishing": "furnished", "available_from": None, "notes": None,
        "images": "[]", "scraped_at": "2026-06-16T00:00:00",
    }
    rec.update(over)
    return rec


def test_init_and_upsert_inserts_new(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_db(conn)
    assert db.upsert_listing(conn, _record()) is True
    rows = db.fetch_all(conn)
    assert len(rows) == 1
    assert rows[0]["rent"] == 30000


def test_upsert_ignores_duplicate_id(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_db(conn)
    db.upsert_listing(conn, _record(rent=30000))
    assert db.upsert_listing(conn, _record(rent=99999)) is False  # same id
    rows = db.fetch_all(conn)
    assert len(rows) == 1
    assert rows[0]["rent"] == 30000  # original kept


def test_exists(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_db(conn)
    assert db.exists(conn, "p1") is False
    db.upsert_listing(conn, _record(id="p1"))
    assert db.exists(conn, "p1") is True


def test_post_kind_column_roundtrips(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_db(conn)
    assert "post_kind" in db.COLUMNS
    rec = _record(id="pk1", post_kind="sale")
    db.upsert_listing(conn, rec)
    rows = db.fetch_all(conn)
    assert rows[0]["post_kind"] == "sale"
