import argparse
import json
import logging
import random
import re
import sys
import time

log = logging.getLogger("zuckerbroker.scrape")

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


def _logged_in(ctx) -> bool:
    """True once Facebook has set the `c_user` cookie (i.e. authenticated)."""
    return any(c.get("name") == "c_user" for c in ctx.cookies())


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

# --- Diagnostic JS: page state, used purely for telemetry (does not affect scraping). ---
_DIAG_JS = r"""
() => ({
  url: location.href,
  title: document.title,
  articleCount: document.querySelectorAll('div[role="article"]').length,
  feedCount: document.querySelectorAll('div[role="feed"]').length,
  imgCount: document.querySelectorAll('img').length,
  bodyLen: (document.body && document.body.innerText ? document.body.innerText.length : 0),
  joinWall: /\bjoin group\b|\bjoin this group\b|\byou.?re not a member\b/i.test(
    document.body ? document.body.innerText : ''),
  loginWall: /\blog in\b|\blog into facebook\b/i.test(
    (document.body ? document.body.innerText.slice(0, 400) : '')),
})
"""


def scrape(groups: list[str], minutes: float, profile_dir: str, out_path: str,
           headless: bool = False, login_wait: float = 120) -> int:
    """Scroll each group for `minutes`, collect posts, dedup within run, write out_path.
    Returns number of posts written. Requires: playwright install chromium."""
    from playwright.sync_api import sync_playwright

    run_start = time.monotonic()
    log.info("scrape start | groups=%d minutes=%.1f headless=%s profile=%s login_wait=%.0fs",
             len(groups), minutes, headless, profile_dir, login_wait)

    seen: dict[str, dict] = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(profile_dir, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        log.debug("browser launched | existing_pages=%d", len(ctx.pages))

        # auth gate: wait up to `login_wait` seconds for a real login.
        # Detect via the `c_user` cookie (only set when authenticated) — the URL
        # is NOT a reliable signal (the logged-out page sits at facebook.com/).
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        log.info("opened facebook home | url=%s logged_in=%s", page.url, _logged_in(ctx))
        login_deadline = time.monotonic() + login_wait
        while not _logged_in(ctx) and time.monotonic() < login_deadline:
            remaining = int(login_deadline - time.monotonic())
            log.info("waiting for login... %ds left (log in in the browser window)", remaining)
            time.sleep(3)
        if not _logged_in(ctx):
            log.warning("still not logged in after %.0fs; continuing anyway (will likely get nothing)", login_wait)
        else:
            cookies = {c.get("name") for c in ctx.cookies()}
            log.info("logged in ✓ | c_user present, %d cookies set", len(cookies))

        for gi, url in enumerate(groups, 1):
            group_start = time.monotonic()
            group_before = len(seen)
            log.info("[group %d/%d] navigating → %s", gi, len(groups), url)
            try:
                page.goto(url, wait_until="domcontentloaded")
            except Exception as e:  # noqa: BLE001 - one bad group must not kill the run
                log.error("[group %d/%d] goto FAILED: %s", gi, len(groups), e)
                continue

            # one-shot page diagnostics right after navigation
            try:
                diag = page.evaluate(_DIAG_JS)
                log.info("[group %d/%d] landed | url=%s title=%r articles=%d feeds=%d imgs=%d bodyLen=%d joinWall=%s loginWall=%s",
                         gi, len(groups), diag.get("url"), (diag.get("title") or "")[:60],
                         diag.get("articleCount"), diag.get("feedCount"), diag.get("imgCount"),
                         diag.get("bodyLen"), diag.get("joinWall"), diag.get("loginWall"))
                if diag.get("joinWall"):
                    log.warning("[group %d/%d] JOIN WALL detected — you may not be a member; feed likely empty", gi, len(groups))
                if diag.get("articleCount", 0) == 0:
                    log.warning("[group %d/%d] 0 article nodes on landing — feed may not have rendered yet, or selector is stale", gi, len(groups))
            except Exception as e:  # noqa: BLE001
                log.error("[group %d/%d] diagnostic eval failed: %s", gi, len(groups), e)

            deadline = time.monotonic() + minutes * 60
            idle_cycles = 0
            cycle = 0
            exit_reason = "deadline"
            while time.monotonic() < deadline:
                cycle += 1
                before = len(seen)
                try:
                    raw_posts = page.evaluate(_EXTRACT_JS)
                except Exception as e:  # noqa: BLE001
                    log.error("[group %d/%d] cycle %d extract eval failed: %s", gi, len(groups), cycle, e)
                    raw_posts = []
                n_articles = len(raw_posts)
                n_with_url = sum(1 for r in raw_posts if r.get("url"))
                n_with_id = 0
                n_no_id_but_url = 0
                for raw in raw_posts:
                    pid = parse_post_id(raw.get("url") or "")
                    if pid:
                        n_with_id += 1
                        if pid not in seen:
                            seen[pid] = {
                                "id": pid,
                                "url": "https://www.facebook.com" + raw["url"]
                                       if raw["url"] and raw["url"].startswith("/") else raw["url"],
                                "text": raw.get("text", ""),
                                "images": raw.get("images", []),
                            }
                    elif raw.get("url"):
                        n_no_id_but_url += 1
                new_this_cycle = len(seen) - before
                log.debug("[group %d/%d] cycle %d | articles=%d with_url=%d with_id=%d unparsed_url=%d new=%d total_seen=%d idle=%d",
                          gi, len(groups), cycle, n_articles, n_with_url, n_with_id,
                          n_no_id_but_url, new_this_cycle, len(seen), idle_cycles)
                if len(seen) == before:
                    idle_cycles += 1
                    if idle_cycles >= 3:
                        exit_reason = f"idle (no new posts {idle_cycles} cycles; last articles={n_articles})"
                        break  # no new posts for 3 consecutive cycles; stop this group early
                else:
                    idle_cycles = 0
                page.mouse.wheel(0, 4000)
                time.sleep(random.uniform(1.0, 3.0))  # ponytail: fixed jitter, not a behavior model

            group_new = len(seen) - group_before
            log.info("[group %d/%d] done | new_posts=%d cycles=%d duration=%.1fs exit=%s",
                     gi, len(groups), group_new, cycle, time.monotonic() - group_start, exit_reason)
            if group_new == 0:
                log.warning("[group %d/%d] collected ZERO posts — check joinWall/articles/loginWall above", gi, len(groups))

        ctx.close()

    with open(out_path, "w") as fh:
        json.dump(list(seen.values()), fh, ensure_ascii=False, indent=2)
    log.info("scrape done | total_posts=%d duration=%.1fs → %s",
             len(seen), time.monotonic() - run_start, out_path)
    return len(seen)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Scrape FB group posts into raw.json")
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--groups", default="groups.txt")
    ap.add_argument("--out", default="raw.json")
    ap.add_argument("--profile", default="fb-profile")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--login-wait", type=float, default=120,
                    help="seconds to wait for manual login before scraping")
    ap.add_argument("--debug", action="store_true", help="verbose per-cycle logging")
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    groups = read_groups(args.groups)
    if not groups:
        sys.exit(f"no group URLs in {args.groups}")
    scrape(groups, args.minutes, args.profile, args.out, args.headless, args.login_wait)


if __name__ == "__main__":
    main()
