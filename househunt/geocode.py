"""Geocode listing locations -> lat/lng/geo_precision in listings.db.

Deduped (each distinct location geocoded once, mapped to all its rows) and
resumable (only touches rows without coords; failed lookups are marked so they
aren't retried forever). Stdlib only.

Run:  GOOGLE_MAPS_API_KEY=... python -m househunt.geocode [--db listings.db] [--limit N]
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request


def geocode(addr: str, key: str) -> tuple[float, float, str] | None:
    """(lat, lng, precision) for an address, or None if not found.
    Raises SystemExit on quota/rate exhaustion so a run stops cleanly (resume later)."""
    q = urllib.parse.urlencode({"address": f"{addr}, Bengaluru, Karnataka, India", "key": key})
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{q}"
    try:
        d = json.load(urllib.request.urlopen(url, timeout=20))
    except Exception as e:  # noqa: BLE001 - network blip; treat as soft miss
        print(f"  err {addr[:40]}: {e}", file=sys.stderr)
        return None
    status = d.get("status")
    if status in ("OVER_QUERY_LIMIT", "OVER_DAILY_LIMIT", "REQUEST_DENIED"):
        sys.exit(f"geocoding stopped: {status} — {d.get('error_message', '')} (re-run to resume)")
    if status != "OK" or not d.get("results"):
        return None
    r = d["results"][0]
    loc = r["geometry"]["location"]
    return loc["lat"], loc["lng"], r["geometry"].get("location_type", "?")


def run(db_path: str, key: str, limit: int = 0) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout=5000")  # tolerate a stray reader
    # lat/lng/geo_precision live in db.py SCHEMA; no migration needed here.

    # Distinct locations with no coords and not yet marked failed.
    locs = [r[0] for r in conn.execute(
        "select distinct location from listings "
        "where location is not null and lat is null and geo_precision is null")]
    if limit:
        locs = locs[:limit]
    print(f"{len(locs)} distinct locations to geocode")

    located = 0
    for i, loc in enumerate(locs, 1):
        g = geocode(loc, key)
        if g:
            lat, lng, prec = g
            conn.execute(
                "update listings set lat=?, lng=?, geo_precision=? "
                "where location=? and lat is null",
                (lat, lng, prec, loc))
            located += 1
        else:
            # mark attempted so re-runs skip it (clear geo_precision to retry later)
            conn.execute(
                "update listings set geo_precision='FAILED' "
                "where location=? and geo_precision is null",
                (loc,))
        conn.commit()
        if i % 50 == 0:
            print(f"  ...{i}/{len(locs)} ({located} located)", file=sys.stderr)
        time.sleep(0.05)  # ponytail: gentle pacing; Google allows ~50 qps, no need to push it

    tot, have = conn.execute(
        "select count(*), count(lat) from listings where location is not null").fetchone()
    print(f"done. {have}/{tot} located rows now have coords "
          f"({located} new distinct locations this run)")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Geocode listing locations into listings.db")
    ap.add_argument("--db", default="listings.db")
    ap.add_argument("--limit", type=int, default=0,
                    help="geocode at most N distinct locations (0 = all). Use a small N to test first.")
    args = ap.parse_args(argv)
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        sys.exit("set GOOGLE_MAPS_API_KEY")
    run(args.db, key, args.limit)


if __name__ == "__main__":
    main()
