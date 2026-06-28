"""Two-stage processing of scraped posts, so dedup can run between them:

  ingest   raw.json -> DB rows (download images, NO LLM)   [cheap]
  (dedup)  mark is_canonical from shared photos             [househunt.dedup]
  extract  LLM-classify ONLY canonical rows -> fill fields  [costs tokens]

Splitting image-download from LLM extraction means the LLM only runs on the ~half
of posts that survive dedup. Both stages are resumable: ingest skips ids already in
the DB; extract skips rows that already have a post_kind.

Run:
  .venv/bin/python -m househunt.pipeline ingest raw.json
  .venv/bin/python -m househunt.dedup
  .venv/bin/python -m househunt.pipeline extract
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import db, llm
from .config import Config, load_config
from .cost import CostTracker
from .extractors import classify_audience, looks_like_sale, normalize_bhk
from .images import download_images


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_post(post: dict, cfg: Config, tracker: CostTracker | None = None) -> dict | None:
    """Classify+extract one post into a DB record (LLM fields only; no images here).
    Sale/blank posts are tagged without an LLM call. On terminal LLM failure return
    None so the caller SKIPS it (retried next run — no half-written fields)."""
    text = post.get("text") or ""
    record = {
        "id": str(post.get("id")),
        "url": post.get("url"),
        "text": text.strip(),
        "scraped_at": _now(),
    }
    if not text.strip():
        # Blank post (image-only / body didn't render). Permanently un-extractable —
        # tag 'other' WITHOUT the LLM so it's done, not retried forever.
        record.update({k: None for k in llm.FIELD_KEYS})
        record["post_kind"] = "other"
    elif looks_like_sale(text):
        record.update({k: None for k in llm.FIELD_KEYS})
        record["post_kind"] = "sale"
    else:
        try:
            fields = llm.llm_extract(text, cfg, tracker=tracker)
        except Exception as e:  # noqa: BLE001 - terminal LLM failure -> skip, retry next run
            print(f"  llm fail {post.get('id')}: {e}; SKIPPED (will retry next run)", file=sys.stderr)
            return None
        record.update(fields)
        record["bhk"] = normalize_bhk(record.get("bhk"))
    return record


def ingest(raw_path: str, cfg: Config, workers: int = 8) -> int:
    """Stage 1: raw.json -> DB rows with images downloaded, NO LLM. Returns new rows."""
    with open(raw_path) as f:
        posts = json.load(f)
    conn = db.connect(cfg.db_path)
    db.init_db(conn)
    todo = [p for p in posts if not db.exists(conn, str(p.get("id")))]

    def work(post: dict) -> dict:
        pid = str(post.get("id"))
        text = (post.get("text") or "").strip()
        imgs = download_images(pid, post.get("images") or [], cfg.images_dir)
        return {"id": pid, "url": post.get("url"), "text": text,
                "images": json.dumps(imgs), "scraped_at": _now(),
                "audience": classify_audience(text)}

    new_count = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, p): str(p.get("id")) for p in todo}
        for fut in as_completed(futures):
            try:
                record = fut.result()
            except Exception as e:  # noqa: BLE001 - one bad post must not kill the batch
                print(f"  ingest {futures[fut]} failed: {e}; skipped", file=sys.stderr)
                continue
            if db.upsert_listing(conn, record):  # LLM cols default to NULL
                new_count += 1
    print(f"ingested {new_count} new rows -> {cfg.db_path} "
          f"(seen {len(posts)}, already-had {len(posts) - len(todo)})")
    return new_count


def extract(cfg: Config, workers: int = 4) -> int:
    """Stage 3 (after dedup): LLM-fill canonical rows that have no post_kind yet.
    Reposts (is_canonical=0) are skipped, so the LLM never sees them. Returns rows filled."""
    if cfg.llm_backend != "mlx" and not cfg.llm_api_key:
        sys.exit("LLM key required: set LLM_API_KEY (regex fallback was removed)")
    conn = db.connect(cfg.db_path)
    db.init_db(conn)
    # canonical (or not-yet-deduped) rows still missing extraction
    todo = conn.execute(
        "select id, url, text from listings "
        "where post_kind is null and (is_canonical is null or is_canonical = 1)").fetchall()
    tracker = CostTracker()

    def work(row) -> dict | None:
        return extract_post({"id": row["id"], "url": row["url"], "text": row["text"]}, cfg, tracker)

    cols = llm.FIELD_KEYS  # includes post_kind
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    filled = 0
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, r): r["id"] for r in todo}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                rec = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  extract {pid} failed: {e}; skipped", file=sys.stderr)
                continue
            if rec is None:
                continue  # LLM failed terminally — leave post_kind NULL so it retries
            conn.execute(f"update listings set {set_clause} where id = ?",
                         [rec.get(c) for c in cols] + [pid])
            conn.commit()  # main thread = sole writer
            filled += 1
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{len(todo)} extracted", file=sys.stderr)
    print(f"extracted {filled}/{len(todo)} canonical rows")
    print(tracker.format(), file=sys.stderr)
    return filled


def _apply_overrides(cfg: Config, db_path: str | None, images: str | None) -> Config:
    return Config(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model,
                  db_path or cfg.db_path, images or cfg.images_dir, cfg.llm_backend)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Ingest/extract FB posts (dedup runs in between)")
    sub = ap.add_subparsers(dest="stage", required=True)
    pi = sub.add_parser("ingest", help="raw.json -> DB rows + images (no LLM)")
    pi.add_argument("raw", nargs="?", default="raw.json")
    pi.add_argument("--db")
    pi.add_argument("--images")
    pi.add_argument("--workers", type=int, default=8)
    pe = sub.add_parser("extract", help="LLM-fill canonical rows (run after dedup)")
    pe.add_argument("--db")
    pe.add_argument("--images")
    pe.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    cfg = _apply_overrides(load_config(), args.db, getattr(args, "images", None))
    if args.stage == "ingest":
        ingest(args.raw, cfg, workers=args.workers)
    else:
        extract(cfg, workers=args.workers)


if __name__ == "__main__":
    main()
