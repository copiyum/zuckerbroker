import pathlib
import sys
import requests


def download_images(post_id: str, urls: list[str], images_dir: str) -> list[str]:
    """Download each URL to <images_dir>/<post_id>_<n>.<ext>, keyed by post id.
    Skips files already on disk. Returns list of relative paths actually present."""
    out_dir = pathlib.Path(images_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i, url in enumerate(urls or []):
        ext = ".png" if ".png" in url.lower() else ".jpg"
        dest = out_dir / f"{post_id}_{i}{ext}"
        if dest.exists():
            paths.append(str(dest))
            continue
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            paths.append(str(dest))
        except Exception as e:  # noqa: BLE001 - best-effort; one bad image must not abort
            print(f"  img fail {url[:60]}: {e}", file=sys.stderr)
    return paths
