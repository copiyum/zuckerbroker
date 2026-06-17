import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from . import db, llm
from .config import Config, load_config
from .cost import CostTracker
from .extractors import looks_like_sale, normalize_bhk
from .images import download_images


def extract_post(post: dict, cfg: Config, tracker: CostTracker | None = None) -> dict | None:
    """Build a DB record. Sale posts are tagged without an LLM call. Otherwise the
    LLM classifies+extracts (SDK retries 429s); on terminal failure return None so
    the caller SKIPS the post (resume retries it next run — no corrupt rows)."""
    text = post.get("text") or ""
    record = {
        "id": str(post.get("id")),
        "url": post.get("url"),
        "text": text.strip(),
        "images": "[]",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    if looks_like_sale(text):
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


def run(raw_path: str, cfg: Config, workers: int = 4) -> int:
    """Process raw.json into the DB concurrently. Workers do the LLM call + image
    download; the main thread is the sole SQLite writer. Returns new listings count."""
    with open(raw_path) as f:
        posts = json.load(f)
    conn = db.connect(cfg.db_path)
    db.init_db(conn)

    if not cfg.llm_api_key:
        sys.exit("LLM key required: set LLM_API_KEY (regex fallback was removed)")

    # Resume: skip posts already stored (no re-extraction, no re-download).
    todo = [p for p in posts if not db.exists(conn, str(p.get("id")))]
    tracker = CostTracker()

    def work(post: dict) -> dict:
        pid = str(post.get("id"))
        record = extract_post(post, cfg, tracker=tracker)
        paths = download_images(pid, post.get("images") or [], cfg.images_dir)
        if record is not None:
            record["images"] = json.dumps(paths)
        return record

    new_count = 0
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, p): str(p.get("id")) for p in todo}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                record = fut.result()
            except Exception as e:  # noqa: BLE001 - one bad post must not kill the batch
                print(f"  post {pid} failed: {e}; skipped", file=sys.stderr)
                continue
            if record is None:
                continue  # LLM failed terminally — leave unstored so resume retries
            if db.upsert_listing(conn, record):  # main thread = sole writer
                new_count += 1
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{len(todo)} processed", file=sys.stderr)

    print(f"{new_count} new listings -> {cfg.db_path} "
          f"(total posts seen: {len(posts)}, already-had: {len(posts) - len(todo)})")
    print(tracker.format(), file=sys.stderr)
    return new_count


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Extract raw FB posts into listings.db")
    ap.add_argument("raw", nargs="?", default="raw.json")
    ap.add_argument("--db")
    ap.add_argument("--images")
    ap.add_argument("--workers", type=int, default=4, help="parallel LLM workers")
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.db:
        cfg = Config(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model, args.db, cfg.images_dir)
    if args.images:
        cfg = Config(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model, cfg.db_path, args.images)
    run(args.raw, cfg, workers=args.workers)


if __name__ == "__main__":
    main()
