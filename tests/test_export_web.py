import json, sqlite3
from househunt import export_web, db as dbm


def _seed(db):
    conn = sqlite3.connect(db); dbm.init_db(conn)
    base = dict(maintenance=None, contact=None, notes=None, available_from=None, scraped_at="t")
    dbm.upsert_listing(conn, {**base, "id": "a", "url": "u", "text": "DROP ME", "bhk": "2 BHK",
        "rent": 30000, "deposit": 100000, "location": "HSR", "listing_type": "entire_flat",
        "post_kind": "offer", "furnishing": "Fully furnished", "images": '["images/a_0.jpg"]',
        "lat": 12.9, "lng": 77.6, "geo_precision": "ROOFTOP"})
    dbm.upsert_listing(conn, {**base, "id": "b", "url": "u", "text": "x", "bhk": "1 BHK", "rent": 12000,
        "deposit": None, "location": "Nowhere", "listing_type": "flatmate", "post_kind": "offer",
        "furnishing": None, "images": "[]", "lat": None, "lng": None, "geo_precision": None})
    dbm.upsert_listing(conn, {**base, "id": "c", "url": "u", "text": "sofa", "bhk": None, "rent": None,
        "deposit": None, "location": "HSR", "listing_type": None, "post_kind": "sale", "furnishing": None,
        "images": "[]", "lat": 12.9, "lng": 77.6, "geo_precision": "APPROXIMATE"})
    conn.close()


def test_export(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    out = tmp_path / "listings.json"
    n = export_web.export(db, str(out), images_src=str(tmp_path / "noimg"), images_dst=str(tmp_path / "wimg"))
    data = json.loads(out.read_text())
    assert n == 1 and len(data) == 1
    rec = data[0]
    assert rec["id"] == "a" and "text" not in rec
    assert rec["lat"] == 12.9 and rec["images"] == ["images/a_0.jpg"]
