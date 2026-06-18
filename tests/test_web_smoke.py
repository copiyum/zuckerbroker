import http.server, socketserver, threading, os, subprocess, contextlib, pathlib
import pytest
from househunt import export_web

PORT = 8231


@contextlib.contextmanager
def serve(root):
    cwd = os.getcwd(); os.chdir(root)
    srv = socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{PORT}/"
    finally:
        srv.shutdown(); os.chdir(cwd)


def test_site_smoke(tmp_path):
    pytest.importorskip("playwright.sync_api")
    repo = pathlib.Path(__file__).resolve().parent.parent
    if not (repo / "listings.db").exists():
        pytest.skip("listings.db not present")
    export_web.export(str(repo / "listings.db"), str(repo / "web" / "static" / "listings.json"),
                      images_src=str(repo / "images"), images_dst=str(repo / "web" / "static" / "images"))
    subprocess.run(["npm", "run", "build"], cwd=str(repo / "web"), check=True)
    from playwright.sync_api import sync_playwright
    with serve(str(repo / "web" / "build")) as url, sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url); pg.wait_for_timeout(7000)
        info = pg.evaluate("""() => ({
          canvas: document.querySelectorAll('#map canvas').length,
          items: document.querySelectorAll('.sidebar .item').length,
          hasRent: !!document.querySelector('.sidebar .item .rent'),
          chips: document.querySelectorAll('.chip').length,
        })""")
        # clicking a sidebar item selects it (sel class) — Svelte re-renders async, so wait then check
        pg.evaluate("() => document.querySelector('.sidebar .item').click()")
        pg.wait_for_timeout(500)
        sel = pg.evaluate("() => !!document.querySelector('.sidebar .item.sel')")
        b.close()
    assert not errs, errs
    assert info["canvas"] >= 1
    assert info["items"] > 0
    assert info["hasRent"]
    assert info["chips"] == 5
    assert sel is True
