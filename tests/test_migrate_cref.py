import json
import os
import sqlite3
import tempfile

from scripts.migrate_cref_json_to_sqlite import migrate


def test_migrate_json_to_sqlite(tmp_path):
    src = tmp_path / "cref.json"
    dst = tmp_path / "cref.db"

    data = {"aria": "cref_123", "sidekick": "cref_456"}
    with open(src, "w") as f:
        json.dump(data, f)

    migrated = migrate(str(src), str(dst), backup=True)
    assert migrated == 2

    # Verify sqlite content
    conn = sqlite3.connect(str(dst))
    cur = conn.execute("SELECT key, cref FROM crefs")
    rows = {k: v for k, v in cur.fetchall()}
    assert rows.get("aria") == "cref_123"
    assert rows.get("sidekick") == "cref_456"
