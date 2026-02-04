import pytest
from unittest.mock import patch, MagicMock
from src.youtube_poster import YouTubePoster

@pytest.fixture
def youtube_poster():
    with patch('src.youtube_poster.InstalledAppFlow.from_client_secrets_file') as mock_flow:
        with patch('src.youtube_poster.build') as mock_build:
            # Mock the flow and build to avoid actual authentication
            mock_flow.return_value = MagicMock()
            mock_build.return_value = MagicMock()
            poster = YouTubePoster(
                client_secrets_file="client_secrets.json",
                credentials_file="youtube_credentials.json",
                dry_run=True
            )
            yield poster

def test_upload_video_dry_run(youtube_poster, capsys):
    file_path = "test_video.mp4"
    title = "Test Title"
    description = "Test Description"

    result = youtube_poster.upload_video(file_path, title, description)

    assert result["status"] == "dry_run"
    captured = capsys.readouterr()
    assert f"[DRY RUN] Would upload video: {file_path}" in captured.out
    assert f"  Title: {title}" in captured.out
    assert f"  Description: {description}" in captured.out
