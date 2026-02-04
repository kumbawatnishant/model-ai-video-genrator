from pathlib import Path
from pathlib import Path

from src.main import orchestrate
from src.instagram_poster import InstagramPoster


def test_orchestrator_local_video_dryrun(monkeypatch, tmp_path):
    # Patch InstagramPoster.upload_video_file to inspect the incoming local file
    uploaded = {}

    def fake_upload(self, file_path, caption, chunk_size=4 * 1024 * 1024):
        uploaded['path'] = file_path
        uploaded['caption'] = caption
        return {"id": "dryrun_uploaded", "status": "dry_run"}

    monkeypatch.setattr(InstagramPoster, "upload_video_file", fake_upload)

    # Run orchestrator in dry-run (it will create a small local mp4 and call upload)
    result = orchestrate(dry_run=True)

    assert result["post_result"]["status"] == "dry_run"
    assert "path" in uploaded
    # Ensure the file exists and looks like an mp4 placeholder
    assert Path(uploaded['path']).exists()
    assert uploaded['path'].endswith('.mp4')