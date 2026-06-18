import sqlite3

COLUMNS = [
    "id", "url", "text", "bhk", "rent", "deposit", "maintenance",
    "location", "contact", "listing_type", "post_kind", "furnishing",
    "available_from", "notes", "images", "scraped_at", "lat", "lng", "geo_precision",
    "audience",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
  id TEXT PRIMARY KEY,
  url TEXT, text TEXT,
  bhk TEXT, rent INTEGER, deposit INTEGER, maintenance INTEGER,
  location TEXT, contact TEXT,
  listing_type TEXT, post_kind TEXT, furnishing TEXT, available_from TEXT, notes TEXT,
  images TEXT,
  scraped_at TEXT, lat REAL, lng REAL, geo_precision TEXT,
  dup_group TEXT, is_canonical INTEGER, rent_min INTEGER, rent_max INTEGER,
  audience TEXT
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def exists(conn: sqlite3.Connection, post_id: str) -> bool:
    cur = conn.execute("SELECT 1 FROM listings WHERE id = ?", (post_id,))
    return cur.fetchone() is not None


def upsert_listing(conn: sqlite3.Connection, record: dict) -> bool:
    """INSERT OR IGNORE keyed on id. Returns True if a new row was inserted."""
    placeholders = ", ".join("?" for _ in COLUMNS)
    cols = ", ".join(COLUMNS)
    values = [record.get(c) for c in COLUMNS]
    cur = conn.execute(
        f"INSERT OR IGNORE INTO listings ({cols}) VALUES ({placeholders})", values
    )
    conn.commit()
    return cur.rowcount > 0


def fetch_all(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute("SELECT * FROM listings ORDER BY scraped_at DESC")
    return [dict(row) for row in cur.fetchall()]
