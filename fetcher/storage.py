"""
storage.py — Job storage using SQLite (via db.py).

Keeps the same add_new_jobs() interface so main.py needs no changes.
After inserting new jobs, re-exports data/jobs.json for the dashboard.
"""

from fetcher import db


def add_new_jobs(jobs: list[dict]) -> list[dict]:
    """
    Dedup and insert new jobs into SQLite.
    Re-exports jobs.json (including archived) after any additions.
    Returns only the newly added jobs.
    """
    new_jobs = db.add_new_jobs(jobs)
    if new_jobs:
        db.export_json()
    return new_jobs
