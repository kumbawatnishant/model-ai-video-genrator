import json
import os
import sqlite3

from scripts.migrate_cref_json_to_sqlite import migrate


def test_db_snapshot_rollback(tmp_path):
    # prepare original DB
    db_path = tmp_path / "cref.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE crefs (key TEXT PRIMARY KEY, cref TEXT NOT NULL)")
    conn.execute("INSERT INTO crefs (key, cref) VALUES (?, ?)", ("keep", "original"))
    conn.commit()
    conn.close()

    # prepare JSON that will overwrite 'keep' with a different value to cause verify mismatch
    src = tmp_path / "cref.json"
    data = {"keep": "new_value"}
    with open(src, "w") as f:
        json.dump(data, f)

    # Monkeypatch compare to force a verification failure after migration so rollback path is exercised
    import scripts.migrate_cref_json_to_sqlite as migrator

    def fake_compare(a, b):
        return {"total_json": 1, "total_db": 1, "to_add": [], "to_overwrite": ["keep"], "identical": []}

    migrator.compare_json_vs_db_backup = migrator.compare_json_vs_db
    migrator.compare_json_vs_db = fake_compare

    # Run migrate with verify and rollback_on_fail; snapshot should be created and used
    rc = migrate(str(src), str(db_path), backup=False, dry_run=False, verify=True, rollback_on_fail=True)
    # migrate returns -1 on verify failure (and attempted rollback)
    assert rc == -1

    # Restore the original compare function
    migrator.compare_json_vs_db = migrator.compare_json_vs_db_backup

    # After rollback, DB should still contain original value
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute("SELECT key, cref FROM crefs")
    rows = {k: v for k, v in cur.fetchall()}
    conn.close()
    assert rows.get("keep") == "original"
