from __future__ import annotations

import sqlite3
from pathlib import Path

from evalh.models import ConfigSpec, ProviderResponse, ResultRow

DB_PATH = Path(__file__).resolve().parent.parent / "results.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    dataset_hash TEXT NOT NULL,
    git_commit TEXT,
    started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS configs (
    config_hash TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_file TEXT NOT NULL,
    params_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    run_id TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    example_id TEXT NOT NULL,
    output_raw TEXT,
    output_parsed TEXT,
    correct INTEGER NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms REAL NOT NULL,
    error TEXT,
    PRIMARY KEY (run_id, config_hash, example_id)
);

CREATE TABLE IF NOT EXISTS cache (
    config_hash TEXT NOT NULL,
    example_id TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (config_hash, example_id)
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA)
    return conn


def start_run(conn: sqlite3.Connection, *, run_id: str, task: str, dataset_hash: str,
              git_commit: str | None, started_at: str) -> None:
    conn.execute(
        "INSERT INTO runs (run_id, task, dataset_hash, git_commit, started_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, task, dataset_hash, git_commit, started_at),
    )
    conn.commit()


def upsert_config(conn: sqlite3.Connection, *, config_hash: str, spec: ConfigSpec) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO configs "
        "(config_hash, name, provider, model, prompt_file, params_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (config_hash, spec.name, spec.provider, spec.model, spec.prompt_file, spec.params_json()),
    )
    conn.commit()


def save_result(conn: sqlite3.Connection, row: ResultRow) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO results "
        "(run_id, config_hash, example_id, output_raw, output_parsed, correct, "
        " tokens_in, tokens_out, cost_usd, latency_ms, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row.run_id,
            row.config_hash,
            row.example_id,
            row.output_raw,
            row.output_parsed,
            int(row.correct),
            row.tokens_in,
            row.tokens_out,
            row.cost_usd,
            row.latency_ms,
            row.error,
        ),
    )
    conn.commit()


def get_cached(
    conn: sqlite3.Connection, *, config_hash: str, example_id: str
) -> ProviderResponse | None:
    cur = conn.execute(
        "SELECT response_json FROM cache WHERE config_hash = ? AND example_id = ?",
        (config_hash, example_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return ProviderResponse.model_validate_json(row[0])


def save_cache(conn: sqlite3.Connection, *, config_hash: str, example_id: str,
               response: ProviderResponse, created_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO cache (config_hash, example_id, response_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        (config_hash, example_id, response.model_dump_json(), created_at),
    )
    conn.commit()


def fetch_results(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    cur = conn.execute(
        "SELECT r.*, c.name AS config_name FROM results r "
        "JOIN configs c ON c.config_hash = r.config_hash "
        "WHERE r.run_id = ?",
        (run_id,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def latest_run_id(conn: sqlite3.Connection, task: str) -> str | None:
    cur = conn.execute(
        "SELECT run_id FROM runs WHERE task = ? ORDER BY started_at DESC LIMIT 1", (task,)
    )
    row = cur.fetchone()
    return row[0] if row else None
