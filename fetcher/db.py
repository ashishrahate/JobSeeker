"""
db.py — SQLite operations for JobSeeker.

Database: data/jobs.db
Schema:   jobs table with archive support

CLI usage:
  python -m fetcher.db stats
  python -m fetcher.db archive --days 60
  python -m fetcher.db purge
  python -m fetcher.db export
  python -m fetcher.db migrate          # import existing jobs.json into DB (one-time)
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH   = Path(__file__).parent.parent / "data" / "jobs.db"
JSON_PATH = Path(__file__).parent.parent / "data" / "jobs.json"


# ── Connection ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id               TEXT PRIMARY KEY,
                source_id        TEXT,
                ats              TEXT,
                company_name     TEXT,
                company_slug     TEXT,
                title            TEXT,
                location         TEXT,
                department       TEXT,
                url              TEXT,
                posted_at        TEXT,
                discovered_at    TEXT NOT NULL,
                role_category    TEXT,
                keywords_matched TEXT,   -- JSON array as string
                opt_cpt          INTEGER, -- 1=true, 0=false, NULL=unknown
                archived         INTEGER NOT NULL DEFAULT 0,
                archived_at      TEXT,
                archive_reason   TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered ON jobs(discovered_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_archived   ON jobs(archived)")
        conn.commit()


# ── Write operations ──────────────────────────────────────────────────────────

def add_new_jobs(jobs: list[dict]) -> list[dict]:
    """
    Insert jobs not already in DB (dedup by primary key id).
    Returns only the newly inserted jobs.
    """
    init_db()
    new_jobs = []
    with get_conn() as conn:
        for job in jobs:
            exists = conn.execute(
                "SELECT 1 FROM jobs WHERE id = ?", (job["id"],)
            ).fetchone()
            if exists:
                continue
            conn.execute("""
                INSERT INTO jobs (
                    id, source_id, ats, company_name, company_slug,
                    title, location, department, url, posted_at,
                    discovered_at, role_category, keywords_matched, opt_cpt,
                    archived
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
            """, (
                job["id"],
                job.get("source_id"),
                job.get("ats"),
                job.get("company_name"),
                job.get("company_slug"),
                job.get("title"),
                job.get("location"),
                job.get("department"),
                job.get("url"),
                job.get("posted_at"),
                job.get("discovered_at"),
                job.get("role_category"),
                json.dumps(job.get("keywords_matched", [])),
                _bool_to_int(job.get("opt_cpt")),
            ))
            new_jobs.append(job)
        conn.commit()
    return new_jobs


def archive_old_jobs(days: int, reason: str = "auto") -> int:
    """
    Mark active jobs discovered more than `days` ago as archived.
    Returns number of rows updated.
    """
    init_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    now    = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE jobs
               SET archived = 1, archived_at = ?, archive_reason = ?
             WHERE archived = 0 AND discovered_at < ?
        """, (now, reason, cutoff))
        conn.commit()
        return cur.rowcount


def purge_archived() -> int:
    """Hard-delete all archived jobs. Returns number of rows deleted."""
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM jobs WHERE archived = 1")
        conn.commit()
        return cur.rowcount


# ── Read operations ───────────────────────────────────────────────────────────

def get_all_jobs(include_archived: bool = True) -> list[dict]:
    """Return jobs as list of dicts, newest first."""
    init_db()
    with get_conn() as conn:
        if include_archived:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY discovered_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE archived = 0 ORDER BY discovered_at DESC"
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_stats() -> dict:
    """Return a dict of DB statistics."""
    init_db()
    with get_conn() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM jobs WHERE archived=0").fetchone()[0]
        archived = conn.execute("SELECT COUNT(*) FROM jobs WHERE archived=1").fetchone()[0]
        oldest   = conn.execute(
            "SELECT MIN(discovered_at) FROM jobs WHERE archived=0"
        ).fetchone()[0]
        newest   = conn.execute(
            "SELECT MAX(discovered_at) FROM jobs WHERE archived=0"
        ).fetchone()[0]
    return {
        "total": total,
        "active": active,
        "archived": archived,
        "oldest_active": oldest,
        "newest_active": newest,
    }


# ── JSON export ───────────────────────────────────────────────────────────────

def export_json(include_archived: bool = True) -> None:
    """
    Write data/jobs.json from DB.
    Includes archived jobs by default so the dashboard can show/hide them.
    """
    jobs = get_all_jobs(include_archived=include_archived)
    now  = datetime.now(timezone.utc).isoformat()
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"jobs": jobs, "last_updated": now, "total_count": len(jobs)}, f, indent=2)
    print(f"Exported {len(jobs)} jobs to {JSON_PATH}")


# ── Migration: jobs.json → SQLite (one-time) ─────────────────────────────────

def migrate_from_json() -> int:
    """
    Import any jobs in data/jobs.json into the DB.
    Safe to run multiple times (deduplicates by id).
    Returns number of jobs imported.
    """
    if not JSON_PATH.exists():
        print("No jobs.json found — nothing to migrate.")
        return 0
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    jobs = data.get("jobs", [])
    if not jobs:
        print("jobs.json is empty — nothing to migrate.")
        return 0
    added = add_new_jobs(jobs)
    print(f"Migrated {len(added)} new jobs from jobs.json into SQLite.")
    return len(added)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bool_to_int(val):
    if val is True:  return 1
    if val is False: return 0
    return None


def _int_to_bool(val):
    if val == 1:  return True
    if val == 0:  return False
    return None


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["opt_cpt"]          = _int_to_bool(d.get("opt_cpt"))
    d["archived"]         = bool(d.get("archived", 0))
    kw = d.get("keywords_matched")
    d["keywords_matched"] = json.loads(kw) if kw else []
    return d


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="JobSeeker DB management")
    sub    = parser.add_subparsers(dest="cmd", required=True)

    # stats
    sub.add_parser("stats", help="Show DB statistics")

    # archive
    p_arc = sub.add_parser("archive", help="Archive jobs older than N days")
    p_arc.add_argument("--days",   type=int, default=60,   help="Age threshold in days (default: 60)")
    p_arc.add_argument("--reason", default="auto",         help="Archive reason label")

    # purge
    sub.add_parser("purge", help="Hard-delete all archived jobs from DB")

    # export
    p_exp = sub.add_parser("export", help="Re-export jobs.json from DB")
    p_exp.add_argument("--no-archived", action="store_true", help="Exclude archived jobs from export")

    # migrate
    sub.add_parser("migrate", help="Import existing jobs.json into SQLite (one-time)")

    args = parser.parse_args()

    if args.cmd == "stats":
        s = get_stats()
        print(f"Total:         {s['total']}")
        print(f"Active:        {s['active']}")
        print(f"Archived:      {s['archived']}")
        print(f"Oldest active: {s['oldest_active'] or 'N/A'}")
        print(f"Newest active: {s['newest_active'] or 'N/A'}")

    elif args.cmd == "archive":
        n = archive_old_jobs(args.days, args.reason)
        print(f"Archived {n} jobs (older than {args.days} days).")
        export_json()

    elif args.cmd == "purge":
        n = purge_archived()
        print(f"Purged {n} archived jobs from DB.")
        export_json(include_archived=False)

    elif args.cmd == "export":
        export_json(include_archived=not args.no_archived)

    elif args.cmd == "migrate":
        migrate_from_json()
        export_json()
