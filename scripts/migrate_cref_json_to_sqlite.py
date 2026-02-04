"""One-time migration tool: move CREF entries from a JSON file to a SQLite DB.

Usage:
  python scripts/migrate_cref_json_to_sqlite.py --from /path/to/cref.json --to /path/to/cref.db [--backup]

If `--from` is omitted the script will look at env `CREF_STORE_PATH` (defaults to .cref_store.json).
If `--to` is omitted the script will use env `CREF_DB_PATH` or `.cref_store.db` in cwd.

The script will create the SQLite DB if needed and insert or update keys.
It supports a `--backup` flag which writes a timestamped copy of the JSON file before modifying anything.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from typing import Dict


def load_json(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        print(f"JSON source not found: {path}")
        return {}
    with open(path, "r") as f:
        try:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("JSON store must be an object mapping keys->cref")
            return data
        except Exception as e:
            print(f"Failed to read JSON store: {e}")
            return {}


def ensure_sqlite_db(path: str):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS crefs (key TEXT PRIMARY KEY, cref TEXT NOT NULL)")
    conn.commit()
    return conn


def _get_db_map(sqlite_path: str) -> dict:
    if not os.path.exists(sqlite_path):
        return {}
    conn = sqlite3.connect(sqlite_path)
    cur = conn.execute("SELECT key, cref FROM crefs")
    rows = {k: v for k, v in cur.fetchall()}
    conn.close()
    return rows


def compare_json_vs_db(json_path: str, sqlite_path: str) -> dict:
    """Compare JSON store against sqlite DB and return a summary dict.

    Summary keys:
      - total_json: number of entries in JSON
      - total_db: number of entries in DB
      - to_add: keys present in JSON but not in DB
      - to_overwrite: keys present in both but value differs
      - identical: keys present in both with same value
    """
    data = load_json(json_path)
    db = _get_db_map(sqlite_path)

    to_add = []
    to_overwrite = []
    identical = []

    for k, v in data.items():
        if k not in db:
            to_add.append(k)
        else:
            if db.get(k) == v:
                identical.append(k)
            else:
                to_overwrite.append(k)

    return {
        "total_json": len(data),
        "total_db": len(db),
        "to_add": to_add,
        "to_overwrite": to_overwrite,
        "identical": identical,
    }


def migrate(json_path: str, sqlite_path: str, backup: bool = False, dry_run: bool = False, verify: bool = False, rollback_on_fail: bool = False) -> int:
    print(f"Migrating from JSON: {json_path} -> SQLite: {sqlite_path}")
    data = load_json(json_path)
    if not data:
        print("No data to migrate.")
        return 0

    # If dry_run, only compare and print summary
    if dry_run:
        summary = compare_json_vs_db(json_path, sqlite_path)
        print("Dry-run summary:")
        print(f" JSON entries: {summary['total_json']}")
        print(f" DB entries: {summary['total_db']}")
        print(f" To add: {len(summary['to_add'])} -> {summary['to_add']}")
        print(f" To overwrite: {len(summary['to_overwrite'])} -> {summary['to_overwrite']}")
        print(f" Identical: {len(summary['identical'])} -> {summary['identical']}")
        return 0

    # If rollback requested but no explicit backup flag, create a JSON backup to allow restore
    created_backup_path = None
    if rollback_on_fail and not backup:
        backup = True

    if backup:
        ts = int(time.time())
        bak = f"{json_path}.bak.{ts}"
        shutil.copy2(json_path, bak)
        created_backup_path = bak
        print(f"Backup written to {bak}")

    # Optional DB-file snapshot (for sqlite) — this provides a byte-for-byte restore
    created_db_snapshot = None
    if rollback_on_fail and os.path.exists(sqlite_path):
        try:
            ts = int(time.time())
            db_snap = f"{sqlite_path}.snapshot.{ts}"
            shutil.copy2(sqlite_path, db_snap)
            created_db_snapshot = db_snap
            print(f"DB snapshot written to {db_snap}")
        except Exception as e:
            print(f"Warning: failed to create DB snapshot: {e}")

    conn = ensure_sqlite_db(sqlite_path)
    cur = conn.cursor()
    migrated = 0
    for k, v in data.items():
        cur.execute(
            "INSERT INTO crefs (key, cref) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET cref=excluded.cref",
            (k, v),
        )
        migrated += 1
    conn.commit()
    conn.close()
    print(f"Migrated {migrated} keys.")

    # If verify requested, compare JSON vs DB now
    if verify:
        summary = compare_json_vs_db(json_path, sqlite_path)
        ok = len(summary.get("to_add", [])) == 0 and len(summary.get("to_overwrite", [])) == 0
        if ok:
            print("Verify: OK — DB matches JSON.")
            return migrated
        else:
            print("Verify: FAILED — DB does not match JSON after migration.")
            print(f"To add: {summary.get('to_add')}")
            print(f"To overwrite: {summary.get('to_overwrite')}")
            # Attempt rollback if requested and we have a backup
            if rollback_on_fail:
                # Prefer DB snapshot restore if available
                if created_db_snapshot and os.path.exists(created_db_snapshot):
                    try:
                        print("Attempting DB-file snapshot rollback...")
                        shutil.copy2(created_db_snapshot, sqlite_path)
                        print("DB-file snapshot restored.")
                        return -1
                    except Exception as e:
                        print(f"DB snapshot rollback failed: {e}")

                # Fallback to JSON-based restore if snapshot not available
                if created_backup_path and os.path.exists(created_backup_path):
                    print("Attempting rollback from JSON backup...")
                    # restore DB from backup JSON
                    migrated_restore = migrate(created_backup_path, sqlite_path, backup=False, dry_run=False, verify=False, rollback_on_fail=False)
                    print(f"Rollback migrated {migrated_restore} keys from backup.")
                    return -1
                else:
                    print("Rollback requested but no backup or snapshot available. No action taken.")
                    return -1
            return -1

    return migrated


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="src", help="Path to JSON source file")
    parser.add_argument("--to", dest="dst", help="Path to sqlite DB target file")
    parser.add_argument("--backup", action="store_true", help="Create a backup of the JSON before migrating")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do not write; only compare JSON vs DB and print a summary")
    parser.add_argument("--verify", dest="verify", action="store_true", help="After migrating, verify DB matches JSON")
    parser.add_argument("--rollback-on-fail", dest="rollback_on_fail", action="store_true", help="If verify fails, attempt to rollback using the JSON backup")
    args = parser.parse_args(argv)

    src = args.src or os.getenv("CREF_STORE_PATH") or os.path.join(os.getcwd(), ".cref_store.json")
    dst = args.dst or os.getenv("CREF_DB_PATH") or os.path.join(os.getcwd(), ".cref_store.db")

    migrated = migrate(src, dst, backup=args.backup, dry_run=args.dry_run, verify=args.verify, rollback_on_fail=args.rollback_on_fail)
    if args.dry_run:
        # dry-run always returns 0
        return 0

    if args.verify and migrated == -1:
        print("Migration failed verification.")
        return 2

    if migrated and migrated > 0:
        print("Migration completed successfully.")
        return 0
    else:
        print("Nothing migrated.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
