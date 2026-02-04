import os

from src.main import orchestrate
from src.gemini_client import GeminiClient
from src.instagram_poster import InstagramPoster


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_full_gork_flow(monkeypatch):
    # Configure env for gork + video proxy
    monkeypatch.setenv("IMAGE_PROVIDER", "gork")
    monkeypatch.setenv("IMAGE_API_URL", "https://proxy/gork/v1/generate")
    monkeypatch.setenv("IMAGE_API_KEY", "fake_image_key")
    monkeypatch.setenv("VIDEO_API_URL", "https://proxy/video/v1/animate")
    monkeypatch.setenv("VIDEO_API_KEY", "fake_video_key")

    fake_image_url = "https://gork.example/content/abcdef1234.png"
    fake_video_url = "https://videos.example/content/aria_clip.mp4"

    # Patch Gemini methods to avoid outbound Gemini calls
    monkeypatch.setattr(GeminiClient, "generate_concept", lambda self: ("Sunday Morning", "Aria prompt"))
    monkeypatch.setattr(GeminiClient, "draft_caption_and_hashtags", lambda self, theme, prompt: ("Caption text", ["#aria"]))

    # Patch requests.post to simulate image and video provider responses
    def fake_post(url, json=None, headers=None, timeout=None):
        if "gork" in url:
            return DummyResp({"data": [{"url": fake_image_url}]})
        if "video" in url:
            return DummyResp({"video_url": fake_video_url})
        # Fallback: return empty json
        return DummyResp({})

    monkeypatch.setattr("requests.post", fake_post)

    # Patch InstagramPoster.post_video to avoid calling real Graph API
    monkeypatch.setattr(InstagramPoster, "post_video", lambda self, video_url, caption, share_to_feed=True: {"id": "sim123", "status": "posted"})

    # Run orchestrator without dry-run (we've patched network interactions)
    result = orchestrate(dry_run=False)

    assert result["image_url"] == fake_image_url
    assert result["video_url"] == fake_video_url
    assert result["post_result"]["status"] == "posted"
