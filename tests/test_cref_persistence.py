import json
import os

from src.image_gen import ImageGenerator


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_cref_is_persisted_and_reused(tmp_path, monkeypatch):
    store_path = tmp_path / "cref_store.json"
    monkeypatch.setenv("CREF_STORE_PATH", str(store_path))
    monkeypatch.setenv("IMAGE_PROVIDER", "gork")
    monkeypatch.setenv("IMAGE_API_URL", "https://proxy/gork/v1/generate")
    monkeypatch.setenv("CHARACTER_KEY", "aria_test")

    # First response includes a cref which should be stored
    fake_cref = "gork_cref_001"
    fake_url = "https://gork.example/content/first.png"

    calls = []

    def fake_post_first(url, json=None, headers=None, timeout=None):
        # First call: provider returns a 'cref'
        calls.append(json)
        return DummyResp({"data": [{"url": fake_url, "cref": fake_cref}]})

    monkeypatch.setattr("requests.post", fake_post_first)

    gen = ImageGenerator(api_key="fake", api_url="https://proxy/gork/v1/generate", dry_run=False, provider="gork")
    out1 = gen.generate_from_prompt("Aria initial prompt")
    assert out1 == fake_url

    # Ensure store file exists and contains the cref
    with open(store_path, "r") as f:
        data = json.load(f)
    assert data.get("aria_test") == fake_cref

    # Second call: ensure the sent payload includes the stored cref
    def fake_post_second(url, json=None, headers=None, timeout=None):
        # Should receive the stored cref in payload
        assert json.get("cref") == fake_cref
        return DummyResp({"data": [{"url": "https://gork.example/content/second.png"}]})

    monkeypatch.setattr("requests.post", fake_post_second)

    out2 = gen.generate_from_prompt("Aria followup prompt")
    assert "second.png" in out2
