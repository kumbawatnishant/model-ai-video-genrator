import os
import io
import json
import tempfile
import pytest

from src.instagram_poster import InstagramPoster

import os
import pytest

from src.instagram_poster import InstagramPoster


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")


def test_upload_video_file_flow(monkeypatch, tmp_path):
    # Create a small temp file (~1MB)
    file_path = tmp_path / "video.mp4"
    data = b"0" * (1024 * 1024 + 100)  # 1MB + 100 bytes
    file_path.write_bytes(data)

    poster = InstagramPoster(ig_user_id="12345", access_token="FAKE", dry_run=False)

    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append((url, data, files))
        # Determine phase from data
        phase = (data or {}).get("upload_phase")
        if phase == "start":
            # simulate start, return session id and offsets
            return DummyResponse({
                "upload_session_id": "sess-1",
                "video_id": "vid-1",
                "start_offset": "0",
                "end_offset": str(len(data) if data else 0),
            })
        if phase == "transfer":
            # mimic transfer: advance start_offset to end (simulate single chunk)
            return DummyResponse({
                "start_offset": str(int(data.get("start_offset", 0)) + (4 * 1024 * 1024)),
                "end_offset": str(len(open(file_path, 'rb').read())),
            })
        if phase == "finish":
            return DummyResponse({"success": True, "id": "vid-1"})
        # media creation
        if url.endswith("/media"):
            return DummyResponse({"id": "creation-1"})
        if url.endswith("/media_publish"):
            return DummyResponse({"id": "published-1"})
        raise RuntimeError("Unexpected call: %s" % url)

    monkeypatch.setattr("requests.post", fake_post)

    result = poster.upload_video_file(str(file_path), caption="Hello world", chunk_size=512 * 1024)
    assert result.get("id") == "published-1"
    # ensure start, transfer, finish, media, publish called
    urls = [c[0] for c in calls]
    assert any("/videos" in u for u in urls)
    assert any(u.endswith("/media") for u in urls)


def test_upload_video_file_dry_run(tmp_path):
    file_path = tmp_path / "video.mp4"
    file_path.write_bytes(b"0" * 1000)
    poster = InstagramPoster(ig_user_id="12345", access_token="FAKE", dry_run=True)
    res = poster.upload_video_file(str(file_path), caption="dry run")
    assert res["status"] == "dry_run"