"""
Simple JSON-file storage engine.

Each "collection" (users, categories, menu_items, tables, orders) lives in
its own .json file as a plain list of dicts — no ORM, no database server.

Concurrency: every read-modify-write operation takes an exclusive OS-level
file lock (fcntl.flock) on a shared lock file before touching any of the
JSON files. flock() locks are tied to the open file description, so this
correctly serializes access both between threads in one process AND between
separate processes (e.g. multiple gunicorn workers) — a plain
threading.Lock would only protect the former.

This is intentionally simple and fine for a single small restaurant's
traffic. It is not a substitute for a real database at high concurrency —
see the README for when to graduate back to one.
"""

import os
import json
import fcntl
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))

COLLECTIONS = ["users", "categories", "menu_items", "tables", "orders"]


class FileLock:
    """Exclusive lock shared by all collections. Simple and safe; the data
    volume for a restaurant is small enough that a single global lock isn't
    a real bottleneck."""

    def __enter__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._fh = open(DATA_DIR / ".lock", "w")
        fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        fcntl.flock(self._fh, fcntl.LOCK_UN)
        self._fh.close()


def _path(name):
    return DATA_DIR / f"{name}.json"


def init_storage():
    """Create the data directory and empty collection files if missing."""
    with FileLock():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for name in COLLECTIONS:
            p = _path(name)
            if not p.exists():
                p.write_text("[]", encoding="utf-8")
        counters_path = DATA_DIR / "counters.json"
        if not counters_path.exists():
            counters_path.write_text(json.dumps({name: 0 for name in COLLECTIONS}), encoding="utf-8")


def _read_raw(name):
    p = _path(name)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else []


def _write_raw(name, data):
    """Atomic write: write to a temp file then rename, so a crash mid-write
    never leaves a half-written JSON file behind."""
    p = _path(name)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, p)


def next_id(name):
    with FileLock():
        counters_path = DATA_DIR / "counters.json"
        counters = json.loads(counters_path.read_text(encoding="utf-8")) if counters_path.exists() else {}
        counters[name] = counters.get(name, 0) + 1
        counters_path.write_text(json.dumps(counters), encoding="utf-8")
        return counters[name]


def get_all(name):
    with FileLock():
        return _read_raw(name)


def get_by_id(name, item_id):
    with FileLock():
        items = _read_raw(name)
    return next((x for x in items if x.get("id") == item_id), None)


def find_one(name, **filters):
    with FileLock():
        items = _read_raw(name)
    return next((x for x in items if all(x.get(k) == v for k, v in filters.items())), None)


def find(name, **filters):
    with FileLock():
        items = _read_raw(name)
    return [x for x in items if all(x.get(k) == v for k, v in filters.items())]


def insert(name, record):
    with FileLock():
        items = _read_raw(name)
        record.setdefault("created_at", datetime.utcnow().isoformat())
        items.append(record)
        _write_raw(name, items)
    return record


def update(name, item_id, fields):
    with FileLock():
        items = _read_raw(name)
        updated = None
        for x in items:
            if x.get("id") == item_id:
                x.update(fields)
                x["updated_at"] = datetime.utcnow().isoformat()
                updated = x
                break
        if updated is not None:
            _write_raw(name, items)
        return updated


def delete(name, item_id):
    with FileLock():
        items = _read_raw(name)
        remaining = [x for x in items if x.get("id") != item_id]
        if len(remaining) == len(items):
            return False
        _write_raw(name, remaining)
        return True
