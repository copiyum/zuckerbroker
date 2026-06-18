"""Image-anchored duplicate detection for listings.db.

Brokers repost the same flat many times (often at different advertised rents/BHKs)
with the SAME photos. We collapse those into clusters keyed on perceptual-hash
(pHash) matches between their images.

Two-tier merge rule (derived from real Kadubeesanahalli data):
  - >=2 shared near-dup photos  -> merge unconditionally (deliberate price-varied spam)
  - exactly 1 shared photo       -> merge only if same BHK and rent within 10%
                                    (one shared photo is often a generic building/amenity
                                     shot reused across genuinely different units)
Listings with no photos are never merged here -- that needs a separate text pass.

Resumable: pHashes are cached in an image_phash table, so re-runs only hash new images.

Writes to listings: dup_group (canonical id of the cluster), is_canonical (0/1),
rent_min, rent_max (range seen across the cluster).

Run:  .venv/bin/python -m househunt.dedup [--db listings.db] [--images images] [--thresh 6]
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict

import imagehash
import numpy as np
from PIL import Image

THRESH = 6            # max pHash Hamming distance counted as a near-dup photo
RENT_TOL = 0.10       # weak-edge (1 shared photo) rent agreement window


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # dup_group/is_canonical/rent_min/rent_max live in db.py SCHEMA. image_phash is
    # dedup-private (a hash cache), so it's created here.
    conn.execute("create table if not exists image_phash (path TEXT PRIMARY KEY, h TEXT)")
    conn.commit()


def _phash_hex(path: str) -> str | None:
    try:
        return str(imagehash.phash(Image.open(path)))
    except Exception:  # noqa: BLE001 - missing/corrupt file; skip
        return None


def _hash_missing(conn: sqlite3.Connection, paths: set[str], images_dir: str) -> None:
    """pHash any referenced image not already cached. Resumable."""
    done = {r[0] for r in conn.execute("select path from image_phash")}
    todo = sorted(paths - done)
    if not todo:
        return
    print(f"hashing {len(todo)} new images...", file=sys.stderr)
    for i, p in enumerate(todo, 1):
        h = _phash_hex(os.path.join(images_dir, os.path.basename(p)))
        conn.execute("insert or replace into image_phash (path, h) values (?, ?)", (p, h))
        if i % 500 == 0:
            conn.commit()
            print(f"  ...{i}/{len(todo)}", file=sys.stderr)
    conn.commit()


def _shared_counts(listing_imgs: dict[str, list[str]],
                   hashes: dict[str, int], thresh: int) -> dict[tuple, int]:
    """For every pair of listings, count near-dup photo matches between them.
    Vectorised pHash Hamming via numpy popcount (scales to ~tens of thousands of images)."""
    flat_ids, flat_h = [], []
    for lid, paths in listing_imgs.items():
        for p in paths:
            h = hashes.get(p)
            if h is not None:
                flat_ids.append(lid)
                flat_h.append(h)
    if not flat_h:
        return {}
    arr = np.array(flat_h, dtype=np.uint64)
    owner = flat_ids
    n = len(arr)
    shared: dict[tuple, int] = defaultdict(int)
    for i in range(n - 1):
        rest = arr[i + 1:] ^ arr[i]
        dist = np.unpackbits(rest.view(np.uint8)).reshape(rest.shape[0], 64).sum(1)
        for off in np.nonzero(dist <= thresh)[0]:
            a, b = owner[i], owner[i + 1 + int(off)]
            if a != b:
                shared[(a, b) if a < b else (b, a)] += 1
    return shared


# fields that signal "completeness" when picking a cluster's canonical row
_INFO_FIELDS = ("rent", "deposit", "maintenance", "bhk", "furnishing",
                "available_from", "contact", "location", "lat")


def run(db_path: str, images_dir: str = "images", thresh: int = THRESH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=5000")
    _ensure_schema(conn)
    conn.row_factory = sqlite3.Row

    # all rows: dedup runs BEFORE LLM extraction (pre-LLM there is no post_kind yet).
    rows = {r["id"]: r for r in conn.execute("select * from listings")}
    listing_imgs = {}
    all_paths: set[str] = set()
    for lid, r in rows.items():
        try:
            imgs = json.loads(r["images"] or "[]")
        except Exception:
            imgs = []
        listing_imgs[lid] = imgs
        all_paths.update(imgs)

    _hash_missing(conn, all_paths, images_dir)
    raw = dict(conn.execute("select path, h from image_phash where h is not null"))
    hashes = {p: int(h, 16) for p, h in raw.items()}

    shared = _shared_counts(listing_imgs, hashes, thresh)

    # union-find with the two-tier rule
    parent = {lid: lid for lid in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def attrs_agree(a, b):
        ra, rb = rows[a]["rent"], rows[b]["rent"]
        if ra is None or rb is None:
            return False  # no rent yet (pre-LLM) -> can't confirm a 1-photo weak edge
        if rows[a]["bhk"] != rows[b]["bhk"]:
            return False
        return abs(ra - rb) <= RENT_TOL * max(ra, rb)

    for (a, b), n_match in shared.items():
        if n_match >= 2 or (n_match == 1 and attrs_agree(a, b)):
            union(a, b)

    clusters = defaultdict(list)
    for lid in parent:
        clusters[find(lid)].append(lid)

    def completeness(lid):
        r = rows[lid]
        n = sum(1 for f in _INFO_FIELDS if r[f] is not None)
        return (n, r["scraped_at"] or "")  # tiebreak: newest scraped_at

    n_dupes = 0
    for members in clusters.values():
        canon = max(members, key=completeness)
        rents = [rows[m]["rent"] for m in members if rows[m]["rent"] is not None]
        rmin, rmax = (min(rents), max(rents)) if rents else (None, None)
        if len(members) > 1:
            n_dupes += len(members) - 1
        for m in members:
            conn.execute(
                "update listings set dup_group=?, is_canonical=?, rent_min=?, rent_max=? where id=?",
                (canon, 1 if m == canon else 0, rmin, rmax, m))
    conn.commit()

    n_clusters = sum(1 for v in clusters.values() if len(v) > 1)
    print(f"{len(rows)} offers -> {len(clusters)} unique "
          f"({n_clusters} dup-clusters absorbing {n_dupes} reposts)")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Image-anchored dedup for listings.db")
    ap.add_argument("--db", default="listings.db")
    ap.add_argument("--images", default="images")
    ap.add_argument("--thresh", type=int, default=THRESH)
    a = ap.parse_args(argv)
    run(a.db, a.images, a.thresh)


if __name__ == "__main__":
    main()
