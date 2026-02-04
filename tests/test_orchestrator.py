from src.main import orchestrate


def test_orchestrator_dryrun():
    result = orchestrate(dry_run=True)
    assert isinstance(result, dict)
    assert "theme" in result
    assert "image_url" in result
    assert "video_url" in result
    assert "caption" in result
    assert "post_result" in result
    # dry run poster returns a status field
    assert result["post_result"].get("status") == "dry_run"
