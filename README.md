# zuckerbroker

Scrapes rental posts out of Facebook groups, makes an LLM read the messy bilingual
chaos, and files everything into a tidy SQLite database with the photos attached.

## How it works

```
Facebook group  →  scrape.py   →  raw.json   →  pipeline.py  →  listings.db + images/
 (you scroll,     (Playwright,    (this run's    (LLM reads it,   (deduped, keyed,
  legally-ish)     your cookies)   posts)         regex if broke)  photos on disk)
```

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
python -m househunt.scrape --minutes 5    # first run: log in by hand in the window
python -m househunt.pipeline raw.json     # extract + store → listings.db + images/
```

Run it as often as you like — it only adds posts it hasn't seen before (deduped by
Facebook's post id), so re-running is cheap and never makes duplicates.

## A word from legal (there is no legal)

This scrapes Facebook, which Facebook would prefer you didn't. Use a throwaway account
in `fb-profile/`, **never your real one**. Cookies = your account.
