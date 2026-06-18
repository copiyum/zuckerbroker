from househunt import images


class _FakeResp:
    def __init__(self, data=b"\xff\xd8\xff_fake_jpeg"):
        self._data = data
    def read(self):
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_downloads_and_keys_by_post_id(tmp_path, monkeypatch):
    calls = []

    def fake_open(req, timeout=None):
        calls.append(req.full_url)
        return _FakeResp()

    monkeypatch.setattr(images.urllib.request, "urlopen", fake_open)
    paths = images.download_images("p1", ["http://x/a.jpg", "http://x/b.png"], str(tmp_path))
    assert paths == [f"{tmp_path}/p1_0.jpg", f"{tmp_path}/p1_1.png"]
    assert (tmp_path / "p1_0.jpg").read_bytes().startswith(b"\xff\xd8")
    assert len(calls) == 2


def test_skips_existing_file(tmp_path, monkeypatch):
    (tmp_path / "p1_0.jpg").write_bytes(b"already")
    calls = []
    monkeypatch.setattr(images.urllib.request, "urlopen", lambda *a, **k: calls.append(1))
    paths = images.download_images("p1", ["http://x/a.jpg"], str(tmp_path))
    assert paths == [f"{tmp_path}/p1_0.jpg"]
    assert calls == []  # no download attempted


def test_failed_download_skipped(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network")
    monkeypatch.setattr(images.urllib.request, "urlopen", boom)
    paths = images.download_images("p1", ["http://x/a.jpg"], str(tmp_path))
    assert paths == []
