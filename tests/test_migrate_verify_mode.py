import json
import os
import sqlite3
import tempfile

from scripts.migrate_cref_json_to_sqlite import migrate, compare_json_vs_db


def test_migrate_with_verify_success(tmp_path):
    src = tmp_path / "cref.json"
    dst = tmp_path / "cref.db"

    data = {"aria": "cref_1", "sidekick": "cref_2"}
    with open(src, "w") as f:
        json.dump(data, f)

    migrated = migrate(str(src), str(dst), backup=True, dry_run=False, verify=True, rollback_on_fail=False)
    assert migrated == 2

    # verify summary should be all identical
    summary = compare_json_vs_db(str(src), str(dst))
    assert summary["total_json"] == 2
    assert summary["total_db"] == 2
    assert summary["to_add"] == []
    assert summary["to_overwrite"] == []
