import json
import os
import sqlite3

from scripts.migrate_cref_json_to_sqlite import compare_json_vs_db, migrate


def test_migrate_dryrun(tmp_path):
    src = tmp_path / "cref.json"
    dst = tmp_path / "cref.db"

    # prepare JSON with 3 keys
    data = {"a": "1", "b": "2", "c": "3"}
    with open(src, "w") as f:
        json.dump(data, f)

    # create sqlite with one overlapping key b but different value, and one extra key x
    conn = sqlite3.connect(str(dst))
    conn.execute("CREATE TABLE crefs (key TEXT PRIMARY KEY, cref TEXT NOT NULL)")
    conn.execute("INSERT INTO crefs (key, cref) VALUES (?, ?)", ("b", "old"))
    conn.execute("INSERT INTO crefs (key, cref) VALUES (?, ?)", ("x", "99"))
    conn.commit()
    conn.close()

    summary = compare_json_vs_db(str(src), str(dst))
    assert summary["total_json"] == 3
    assert summary["total_db"] == 2
    assert set(summary["to_add"]) == {"a", "c"}
    assert summary["to_overwrite"] == ["b"]

    # ensure migrate with dry_run doesn't write
    rc = migrate(str(src), str(dst), backup=False, dry_run=True)
    assert rc == 0

    # Verify DB unchanged (b still 'old', x still '99')
    conn = sqlite3.connect(str(dst))
    cur = conn.execute("SELECT key, cref FROM crefs")
    rows = {k: v for k, v in cur.fetchall()}
    conn.close()
    assert rows.get("b") == "old"
    assert rows.get("x") == "99"
