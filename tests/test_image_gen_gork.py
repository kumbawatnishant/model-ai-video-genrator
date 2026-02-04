import json

import pytest

from src.image_gen import ImageGenerator


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_gork_parsing(monkeypatch):
    # Prepare a realistic gork-like response
    fake_url = "https://gork.example/content/abcdef1234.png"
    fake_response = {"data": [{"url": fake_url, "meta": {"provider": "gork"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url  # basic sanity
        return DummyResp(fake_response)

    monkeypatch.setattr("requests.post", fake_post)

    gen = ImageGenerator(api_key="fake", api_url="https://proxy/gork/v1/generate", dry_run=False, provider="gork")
    out = gen.generate_from_prompt("Aria smiling in golden hour", cref="aria_cref_001")
    assert out == fake_url
