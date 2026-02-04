import json
import os
from typing import Optional
from urllib.parse import urlparse

try:
    from sqlalchemy import (create_engine, MetaData, Table, Column, String, select, text)
except Exception:  # pragma: no cover - handled at runtime
    create_engine = None


class _JSONCrefStore:
    def __init__(self, path: str):
        self.path = path
        # ensure file exists
        if not os.path.exists(self.path):
            try:
                with open(self.path, "w") as f:
                    json.dump({}, f)
            except Exception:
                pass

    def _read(self) -> dict:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, data: dict):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def get(self, key: str) -> Optional[str]:
        data = self._read()
        return data.get(key)

    def set(self, key: str, cref: str):
        data = self._read()
        data[key] = cref
        self._write(data)


class _SQLAlchemyCrefStore:
    """SQLAlchemy-backed CrefStore. Accepts any DB URL supported by SQLAlchemy.

    Example URLs:
      sqlite:///absolute/path.db
      sqlite:///:memory:
      postgresql+psycopg2://user:pass@host/dbname
      mysql+pymysql://user:pass@host/dbname
    """

    def __init__(self, db_url: str):
        if create_engine is None:
            raise RuntimeError("sqlalchemy is required for SQL DB support. Please install the extras in requirements.txt")

        # Normalize sqlite file paths provided like '/path/to/file.db'
        parsed = urlparse(db_url)
        if not parsed.scheme or (parsed.scheme == "file" and db_url.endswith(".db")):
            # Treat as sqlite file path if user passed a bare file path
            db_url = f"sqlite:///{db_url}"

        self.engine = create_engine(db_url, future=True)
        self.metadata = MetaData()
        self.crefs = Table(
            "crefs",
            self.metadata,
            Column("key", String, primary_key=True),
            Column("cref", String, nullable=False),
        )
        self.metadata.create_all(self.engine)

    def get(self, key: str) -> Optional[str]:
        with self.engine.connect() as conn:
            stmt = select(self.crefs.c.cref).where(self.crefs.c.key == key)
            res = conn.execute(stmt).fetchone()
            return res[0] if res else None

    def set(self, key: str, cref: str):
        # Use dialect-aware upsert where possible; fallback to update/insert
        dialect = self.engine.dialect.name
        with self.engine.begin() as conn:
            if dialect in ("sqlite", "postgresql"):
                # both sqlite (>=3.24) and postgresql support ON CONFLICT
                conn.execute(
                    text(
                        "INSERT INTO crefs (key, cref) VALUES (:k, :c) ON CONFLICT(key) DO UPDATE SET cref = :c"
                    ),
                    {"k": key, "c": cref},
                )
            else:
                # Generic: try update then insert if no rows updated
                upd = self.crefs.update().where(self.crefs.c.key == key).values(cref=cref)
                res = conn.execute(upd)
                if res.rowcount == 0:
                    conn.execute(self.crefs.insert().values(key=key, cref=cref))


class CrefStore:
    """Flexible CrefStore: JSON file backend (if path ends with .json) or SQL backend.

    Selection rules:
    - If env `CREF_DB_URL` is set -> SQL backend via SQLAlchemy.
    - Else if env `CREF_STORE_PATH` points to a .json file -> JSON backend.
    - Else if env `CREF_STORE_PATH` points to a .db file or starts with 'sqlite' -> SQLite backend via SQLAlchemy.
    - Otherwise default to a JSON file `.cref_store.json` in cwd.
    """

    def __init__(self, path: Optional[str] = None):
        env_path = path or os.getenv("CREF_STORE_PATH")
        db_url = os.getenv("CREF_DB_URL") or os.getenv("CREF_DB_PATH")

        # Prefer explicit DB URL
        if db_url:
            # If db_url looks like a bare file path, SQLAlchemy wrapper will normalize
            self._impl = _SQLAlchemyCrefStore(db_url)
            return

        if env_path:
            env_path = str(env_path)
            if env_path.endswith(".json"):
                self._impl = _JSONCrefStore(env_path)
                return
            if env_path.endswith(".db") or env_path.startswith("sqlite"):
                # treat this as a sqlite DB URL or path
                if env_path.startswith("sqlite"):
                    self._impl = _SQLAlchemyCrefStore(env_path)
                else:
                    self._impl = _SQLAlchemyCrefStore(f"sqlite:///{env_path}")
                return
            # fallback to JSON
            self._impl = _JSONCrefStore(env_path)
            return

        # default
        default = os.path.join(os.getcwd(), ".cref_store.json")
        self._impl = _JSONCrefStore(default)

    def get(self, key: str) -> Optional[str]:
        return self._impl.get(key)

    def set(self, key: str, cref: str):
        return self._impl.set(key, cref)
