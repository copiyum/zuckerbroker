# zuckerbroker

scrapes rental posts out of Facebook groups, makes an LLM read the messy bilingual
chaos, and files everything into a tidy SQLite database with the photos attached.

## How it works

```
Facebook group → scrape → ingest → dedup → extract → geocode → export → website
 (you scroll)    raw.json  rows +   mark    LLM reads  lat/lng   listings  map
                          images   reposts  CANONICAL           .json
                                            only (½ the cost)
```

Dedup runs *before* the LLM on purpose: brokers repost the same flat (same photos)
many times, so we collapse photo-identical reposts first and only pay for the LLM on
the ~half that survive.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp groups.txt.example groups.txt   # paste your rental group URLs
```

## Teaching it to read (optional, recommended)

Point it at any OpenAI-compatible endpoint (default: MiniMax — confirm the exact base
URL + model in your dashboard):

```bash
export LLM_API_KEY=...
export LLM_BASE_URL=https://api.minimax.io/v1
export LLM_MODEL=MiniMax-Text-01
```

## Run it

```bash
python -m househunt.scrape --minutes 5         # first run: log in by hand in the window
python -m househunt.pipeline ingest raw.json   # download images + store raw rows (no LLM)
python -m househunt.dedup                      # mark photo-identical reposts (is_canonical)
python -m househunt.pipeline extract           # LLM reads ONLY canonical rows
GOOGLE_MAPS_API_KEY=... python -m househunt.geocode   # locations → lat/lng
python -m househunt.export_web                 # → web/static/listings.json
```

Run it as often as you like — every stage is resumable. `ingest` only adds posts it
hasn't seen (by Facebook post id); `extract` only LLMs rows without a `post_kind`;
`dedup` only hashes new images. Re-running is cheap and never makes duplicates.

## A word from legal (there is no legal)

This scrapes Facebook, which Facebook would prefer you didn't. Use a throwaway account
in `fb-profile/`, **never your real one**. Cookies = your account.
