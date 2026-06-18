"""Build step: dump listings.db -> web/static/listings.json (offers with coords, card fields only,
no long `text`) + copy referenced images -> web/static/images. Run after each scrape.
Run: .venv/bin/python -m househunt.export_web
"""
import argparse, json, os, shutil, sqlite3

FIELDS = ["id", "url", "rent", "deposit", "maintenance", "bhk", "listing_type",
          "furnishing", "available_from", "location", "contact", "geo_precision", "lat", "lng"]


def export(db_path, out_path, images_src="images", images_dst="web/static/images"):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "select * from listings where post_kind='offer' and lat is not null and lng is not null").fetchall()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    os.makedirs(images_dst, exist_ok=True)
    out = []
    for r in rows:
        rec = {k: r[k] for k in FIELDS}
        try:
            imgs = json.loads(r["images"] or "[]")
        except Exception:
            imgs = []
        web_imgs = []
        for p in imgs:
            base = os.path.basename(p)
            src = os.path.join(images_src, base)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(images_dst, base))
            web_imgs.append("images/" + base)
        rec["images"] = web_imgs
        out.append(rec)
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out)} offers -> {out_path} ({os.path.getsize(out_path)//1024} KB)")
    return len(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export listings.db -> web/static/listings.json")
    ap.add_argument("--db", default="listings.db")
    ap.add_argument("--out", default="web/static/listings.json")
    ap.add_argument("--images-src", default="images")
    ap.add_argument("--images-dst", default="web/static/images")
    a = ap.parse_args(argv)
    export(a.db, a.out, a.images_src, a.images_dst)


if __name__ == "__main__":
    main()
