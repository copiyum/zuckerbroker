"""Tests for image-anchored dedup. Fake photos are tiny deterministic-noise PNGs:
same seed -> identical pHash (a shared photo); different seed -> far-apart pHash."""
import json

import numpy as np
from PIL import Image

from househunt import db, dedup


def _img(path, seed):
    # deterministic noise: same seed -> identical pHash, different seed -> far apart
    # (solid colours all pHash alike, so they can't model "distinct photos")
    rng = np.random.default_rng(seed)
    Image.fromarray((rng.random((64, 64, 3)) * 255).astype("uint8")).save(path)


def _conn(tmp_path):
    c = db.connect(str(tmp_path / "t.db"))
    db.init_db(c)
    return c


def _add(conn, id, rent, bhk, imgs, lt="flatmate", scraped="2026-06-01"):
    conn.execute(
        "insert into listings (id, post_kind, rent, bhk, listing_type, images, scraped_at) "
        "values (?, 'offer', ?, ?, ?, ?, ?)",
        (id, rent, bhk, lt, json.dumps(imgs), scraped))
    conn.commit()


def _groups(conn):
    return {r["id"]: r["dup_group"] for r in conn.execute("select id, dup_group from listings")}


def test_identical_photoset_merges_across_rents(tmp_path):
    # Sobha case: same 2 photos, different advertised rent -> merge
    for n, seed in (("a", 1), ("b", 2)):
        _img(tmp_path / f"{n}.png", seed)
    _add(conn := _conn(tmp_path), "L1", 52000, "2 BHK", ["a.png", "b.png"])
    _add(conn, "L2", 38000, "1 BHK", ["a.png", "b.png"])  # 2 shared photos
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    g = _groups(conn)
    assert g["L1"] == g["L2"]


def test_single_shared_photo_with_rent_mismatch_splits(tmp_path):
    # ORR case: one shared generic photo, very different rent -> stay separate
    _img(tmp_path / "shared.png", 10)
    _img(tmp_path / "x.png", 20)
    _img(tmp_path / "y.png", 30)
    _add(conn := _conn(tmp_path), "H", 60000, "3 BHK", ["shared.png", "x.png"])
    _add(conn, "L", 25000, "3 BHK", ["shared.png", "y.png"])  # only 'shared.png' matches
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    g = _groups(conn)
    assert g["H"] != g["L"]


def test_single_shared_photo_with_close_rent_merges(tmp_path):
    # ORR ₹60k trio: one shared photo + same BHK + equal rent -> merge
    _img(tmp_path / "shared.png", 10)
    _img(tmp_path / "x.png", 20)
    _img(tmp_path / "y.png", 30)
    _add(conn := _conn(tmp_path), "A", 60000, "3 BHK", ["shared.png", "x.png"])
    _add(conn, "B", 60000, "3 BHK", ["shared.png", "y.png"])
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    g = _groups(conn)
    assert g["A"] == g["B"]


def test_canonical_is_most_complete_and_rent_range(tmp_path):
    for n, seed in (("a", 1), ("b", 2)):
        _img(tmp_path / f"{n}.png", seed)
    conn = _conn(tmp_path)
    _add(conn, "sparse", 52000, "2 BHK", ["a.png", "b.png"])
    # richer row: also has deposit/furnishing/location
    conn.execute("insert into listings (id, post_kind, rent, bhk, listing_type, images, "
                 "scraped_at, deposit, furnishing, location) values "
                 "(?, 'offer', ?, ?, 'flatmate', ?, ?, ?, ?, ?)",
                 ("rich", 50000, "2 BHK", json.dumps(["a.png", "b.png"]),
                  "2026-06-01", 80000, "furnished", "Sobha"))
    conn.commit()
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    rows = {r["id"]: r for r in conn.execute("select * from listings")}
    assert rows["rich"]["is_canonical"] == 1
    assert rows["sparse"]["is_canonical"] == 0
    assert rows["sparse"]["dup_group"] == "rich"
    assert rows["rich"]["rent_min"] == 50000 and rows["rich"]["rent_max"] == 52000


def test_no_photo_listings_stay_separate(tmp_path):
    conn = _conn(tmp_path)
    _add(conn, "N1", 14000, "3 BHK", [])
    _add(conn, "N2", 14000, "3 BHK", [])
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    g = _groups(conn)
    assert g["N1"] != g["N2"]  # image-anchored only; text pass is separate


def test_resumable_hash_cache(tmp_path):
    _img(tmp_path / "a.png", 1)
    _add(conn := _conn(tmp_path), "L1", 10000, "1 BHK", ["a.png"])
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))
    n1 = conn.execute("select count(*) from image_phash").fetchone()[0]
    dedup.run(str(tmp_path / "t.db"), images_dir=str(tmp_path))  # re-run
    n2 = conn.execute("select count(*) from image_phash").fetchone()[0]
    assert n1 == n2 == 1
