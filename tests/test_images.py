from househunt import images


def test_downloads_and_keys_by_post_id(tmp_path, monkeypatch):
    calls = []

    class FakeResp:
        content = b"\xff\xd8\xff_fake_jpeg"
        def raise_for_status(self): pass

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return FakeResp()

    monkeypatch.setattr(images.requests, "get", fake_get)
    paths = images.download_images("p1", ["http://x/a.jpg", "http://x/b.png"], str(tmp_path))
    assert paths == [f"{tmp_path}/p1_0.jpg", f"{tmp_path}/p1_1.png"]
    assert (tmp_path / "p1_0.jpg").read_bytes().startswith(b"\xff\xd8")
    assert len(calls) == 2


def test_skips_existing_file(tmp_path, monkeypatch):
    (tmp_path / "p1_0.jpg").write_bytes(b"already")
    calls = []
    monkeypatch.setattr(images.requests, "get",
                        lambda *a, **k: calls.append(1))
    paths = images.download_images("p1", ["http://x/a.jpg"], str(tmp_path))
    assert paths == [f"{tmp_path}/p1_0.jpg"]
    assert calls == []  # no download attempted


def test_failed_download_skipped(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network")
    monkeypatch.setattr(images.requests, "get", boom)
    paths = images.download_images("p1", ["http://x/a.jpg"], str(tmp_path))
    assert paths == []
