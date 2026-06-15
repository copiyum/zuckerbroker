import argparse
import json
import random
import re
import sys
import time

POST_ID_RES = [
    re.compile(r'/posts/(\d+)'),
    re.compile(r'/permalink/(\d+)'),
    re.compile(r'multi_permalinks=(\d+)'),
    re.compile(r'[?&]story_fbid=(\d+)'),
]


def parse_post_id(href: str) -> str | None:
    for rx in POST_ID_RES:
        m = rx.search(href or "")
        if m:
            return m.group(1)
    return None


def read_groups(path: str) -> list[str]:
    lines = []
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


# --- JS evaluated in-page to pull posts after scrolling. ---
# Selectors are FB-fragile by nature; isolated here so they are the ONE place to fix.
_EXTRACT_JS = r"""
() => {
  const out = [];
  const articles = document.querySelectorAll('div[role="article"]');
  for (const a of articles) {
    let url = null;
    for (const link of a.querySelectorAll('a[href]')) {
      const h = link.getAttribute('href') || '';
      if (/\/posts\/\d+|\/permalink\/\d+|multi_permalinks=\d+|story_fbid=\d+/.test(h)) { url = h; break; }
    }
    const text = (a.innerText || '').trim();
    const imgs = [...a.querySelectorAll('img')]
      .map(i => i.src)
      .filter(s => s && s.startsWith('http') && !s.includes('static.xx'));  // drop UI icons
    out.push({ url, text, images: imgs });
  }
  return out;
}
"""


def scrape(groups: list[str], minutes: float, profile_dir: str, out_path: str,
           headless: bool = False) -> int:
    """Scroll each group for `minutes`, collect posts, dedup within run, write out_path.
    Returns number of posts written. Requires: playwright install chromium."""
    from playwright.sync_api import sync_playwright

    seen: dict[str, dict] = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(profile_dir, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # auth gate: if redirected to login, pause for manual login
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        if "login" in page.url:
            input("Not logged in. Log in in the browser window, then press Enter...")

        for url in groups:
            print(f"scraping {url}", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded")
            deadline = time.monotonic() + minutes * 60
            idle_cycles = 0
            while time.monotonic() < deadline:
                before = len(seen)
                for raw in page.evaluate(_EXTRACT_JS):
                    pid = parse_post_id(raw.get("url") or "")
                    if pid and pid not in seen:
                        seen[pid] = {
                            "id": pid,
                            "url": "https://www.facebook.com" + raw["url"]
                                   if raw["url"] and raw["url"].startswith("/") else raw["url"],
                            "text": raw.get("text", ""),
                            "images": raw.get("images", []),
                        }
                if len(seen) == before:
                    idle_cycles += 1
                    if idle_cycles >= 3:
                        break  # no new posts for 3 consecutive cycles; stop this group early
                else:
                    idle_cycles = 0
                page.mouse.wheel(0, 4000)
                time.sleep(random.uniform(1.0, 3.0))  # ponytail: fixed jitter, not a behavior model

        ctx.close()

    with open(out_path, "w") as fh:
        json.dump(list(seen.values()), fh, ensure_ascii=False, indent=2)
    print(f"{len(seen)} posts -> {out_path}", file=sys.stderr)
    return len(seen)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Scrape FB group posts into raw.json")
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--groups", default="groups.txt")
    ap.add_argument("--out", default="raw.json")
    ap.add_argument("--profile", default="fb-profile")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args(argv)
    groups = read_groups(args.groups)
    if not groups:
        sys.exit(f"no group URLs in {args.groups}")
    scrape(groups, args.minutes, args.profile, args.out, args.headless)


if __name__ == "__main__":
    main()
