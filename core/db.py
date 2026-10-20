"""SQLite persistence for QFin Lab.

Stores progress, quiz and code scores, lab runs, lab reports, notes, oral
("Defend it") rounds, spaced-repetition cards and learner settings.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("QFIN_DB", ROOT / "user_data" / "qfin_lab.sqlite"))


def _db_path() -> Path:
    return Path(os.environ.get("QFIN_DB", ROOT / "user_data" / "qfin_lab.sqlite"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS module_status (
    module_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'locked',      -- locked | open | mastered | tested_out
    started_on TEXT,
    mastered_on TEXT
);
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, kind TEXT,                   -- quiz | placement
    score REAL, n_questions INTEGER,
    detail TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS code_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, exercise_id TEXT,
    score REAL, passed INTEGER, total INTEGER,
    code TEXT, detail TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS lab_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, lab_id TEXT,
    seed INTEGER, record TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS lab_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, lab_id TEXT,
    report TEXT, scores TEXT, total REAL, passed INTEGER,
    feedback TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS oral_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, persona TEXT,
    score REAL, transcript TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS notes (
    module_id TEXT PRIMARY KEY,
    body TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS cards (
    card_id TEXT PRIMARY KEY,
    module_id TEXT, front TEXT, back TEXT, kind TEXT,
    easiness REAL DEFAULT 2.5, interval INTEGER DEFAULT 0,
    repetitions INTEGER DEFAULT 0, due TEXT, last_review TEXT,
    lapses INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS card_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT, quality INTEGER, reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS study_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, minutes REAL, logged_on TEXT
);
CREATE TABLE IF NOT EXISTS tutor_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT, role TEXT, content TEXT, created_at TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return date.today().isoformat()


@contextmanager
def conn():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


# ---------- settings ----------
def get_setting(key: str, default=None):
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return row["value"]


def set_setting(key: str, value) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )


# ---------- module status ----------
def get_status(module_id: str) -> str | None:
    with conn() as c:
        row = c.execute("SELECT status FROM module_status WHERE module_id=?", (module_id,)).fetchone()
    return row["status"] if row else None


def all_status() -> dict[str, dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM module_status").fetchall()
    return {r["module_id"]: dict(r) for r in rows}


def set_status(module_id: str, status: str) -> None:
    with conn() as c:
        existing = c.execute("SELECT * FROM module_status WHERE module_id=?", (module_id,)).fetchone()
        started = existing["started_on"] if existing else None
        mastered = existing["mastered_on"] if existing else None
        if status == "open" and not started:
            started = today()
        if status in ("mastered", "tested_out") and not mastered:
            mastered = today()
            started = started or today()
        c.execute(
            "INSERT INTO module_status(module_id,status,started_on,mastered_on) VALUES(?,?,?,?) "
            "ON CONFLICT(module_id) DO UPDATE SET status=excluded.status, "
            "started_on=excluded.started_on, mastered_on=excluded.mastered_on",
            (module_id, status, started, mastered),
        )


# ---------- generic inserts / queries ----------
def insert(table: str, **fields) -> int:
    fields.setdefault("created_at", now())
    cols = ",".join(fields)
    qs = ",".join("?" for _ in fields)
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in fields.values()]
    with conn() as c:
        cur = c.execute(f"INSERT INTO {table}({cols}) VALUES({qs})", vals)
        return cur.lastrowid


def query(sql: str, params: tuple = ()) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def best_quiz(module_id: str) -> float | None:
    rows = query("SELECT MAX(score) AS s FROM quiz_attempts WHERE module_id=? AND kind='quiz'", (module_id,))
    return rows[0]["s"] if rows and rows[0]["s"] is not None else None


def best_code(module_id: str) -> float | None:
    rows = query("SELECT MAX(score) AS s FROM code_attempts WHERE module_id=?", (module_id,))
    return rows[0]["s"] if rows and rows[0]["s"] is not None else None


def has_passing_report(module_id: str) -> bool:
    rows = query("SELECT COUNT(*) AS n FROM lab_reports WHERE module_id=? AND passed=1", (module_id,))
    return bool(rows and rows[0]["n"])


def best_report(module_id: str) -> float | None:
    rows = query("SELECT MAX(total) AS s FROM lab_reports WHERE module_id=?", (module_id,))
    return rows[0]["s"] if rows and rows[0]["s"] is not None else None


def best_oral(module_id: str) -> float | None:
    rows = query("SELECT MAX(score) AS s FROM oral_rounds WHERE module_id=?", (module_id,))
    return rows[0]["s"] if rows and rows[0]["s"] is not None else None


def get_note(module_id: str) -> str:
    rows = query("SELECT body FROM notes WHERE module_id=?", (module_id,))
    return rows[0]["body"] if rows else ""


def save_note(module_id: str, body: str) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO notes(module_id,body,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(module_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
            (module_id, body, now()),
        )


def log_study(module_id: str, minutes: float) -> None:
    with conn() as c:
        c.execute("INSERT INTO study_log(module_id,minutes,logged_on) VALUES(?,?,?)", (module_id, minutes, today()))
