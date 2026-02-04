import os
from pathlib import Path

import pytest


def test_auto_migrate_runs_and_writes_marker(monkeypatch, tmp_path):
    # Ensure marker path is in tmp dir
    marker = tmp_path / "cref_auto_migrated"
    monkeypatch.setenv("AUTO_MIGRATE_MARKER_PATH", str(marker))
    monkeypatch.setenv("AUTO_MIGRATE_ON_START", "true")

    called = {"migrate": False}

    # Monkeypatch migrate function to simulate success
    def fake_migrate(src, dst, backup, dry_run, verify, rollback_on_fail):
        called["migrate"] = True
        return 1

    import importlib
    migrator = importlib.import_module("scripts.migrate_cref_json_to_sqlite")
    monkeypatch.setattr(migrator, "migrate", fake_migrate)

    # Ensure src.main uses our fake migrate (it may have imported earlier in the test session)
    main_mod = importlib.import_module("src.main")
    # Overwrite the bound reference in src.main if present
    if hasattr(main_mod, "migrate"):
        setattr(main_mod, "migrate", fake_migrate)
    # run with auto_migrate True
    res = main_mod.run(dry_run=True, auto_migrate=True)
    # ensure migrate was called and marker file written
    assert called["migrate"]
    assert marker.exists()

    # Running again should skip migration because marker exists
    called["migrate"] = False
    res2 = main_mod.run(dry_run=True, auto_migrate=True)
    assert not called["migrate"]
