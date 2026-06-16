import argparse
import json
import sys
from datetime import datetime, timezone

from . import db, llm
from .config import Config, load_config
from .cost import CostTracker
from .extractors import normalize_bhk, regex_extract
from .images import download_images


def extract_post(post: dict, cfg: Config, tracker: CostTracker | None = None) -> dict:
    """Build a full DB record from a raw post. LLM if key present, else regex;
    LLM errors fall back to regex for that post (batch never aborts)."""
    text = post.get("text") or ""
    fields = None
    if cfg.llm_api_key:
        try:
            fields = llm.llm_extract(text, cfg, tracker=tracker)
        except Exception as e:  # noqa: BLE001
            print(f"  llm fail {post.get('id')}: {e}; using regex", file=sys.stderr)
    if fields is None:
        fields = regex_extract(text)

    record = {
        "id": str(post.get("id")),
        "url": post.get("url"),
        "text": text.strip(),
        "images": "[]",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }
    record.update(fields)
    record["bhk"] = normalize_bhk(record.get("bhk"))
    return record


def run(raw_path: str, cfg: Config) -> int:
    """Process raw.json into the DB. Returns count of new listings inserted."""
    with open(raw_path) as f:
        posts = json.load(f)
    conn = db.connect(cfg.db_path)
    db.init_db(conn)

    tracker = CostTracker()
    new_count = 0
    for post in posts:
        pid = str(post.get("id"))
        if db.exists(conn, pid):
            continue  # already stored; skip extraction + image download
        record = extract_post(post, cfg, tracker=tracker)
        paths = download_images(pid, post.get("images") or [], cfg.images_dir)
        record["images"] = json.dumps(paths)
        if db.upsert_listing(conn, record):
            new_count += 1
    print(f"{new_count} new listings -> {cfg.db_path} (total posts seen: {len(posts)})")
    print(tracker.format(), file=sys.stderr)
    return new_count


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Extract raw FB posts into listings.db")
    ap.add_argument("raw", nargs="?", default="raw.json")
    ap.add_argument("--db")
    ap.add_argument("--images")
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.db:
        cfg = Config(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model, args.db, cfg.images_dir)
    if args.images:
        cfg = Config(cfg.llm_base_url, cfg.llm_api_key, cfg.llm_model, cfg.db_path, args.images)
    run(args.raw, cfg)


if __name__ == "__main__":
    main()
