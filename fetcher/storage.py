import json
import os
from datetime import datetime, timezone

JOBS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.json")


def load() -> dict:
    path = os.path.abspath(JOBS_FILE)
    if not os.path.exists(path):
        return {"jobs": [], "last_updated": None, "total_count": 0}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    path = os.path.abspath(JOBS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_new_jobs(new_jobs: list[dict]) -> list[dict]:
    """
    Loads existing jobs, deduplicates by id, appends new ones.
    Returns only the genuinely new jobs that were added.
    Saves updated data back to file.
    """
    data = load()
    existing_ids = {job["id"] for job in data["jobs"]}

    added = []
    for job in new_jobs:
        if job["id"] not in existing_ids:
            data["jobs"].append(job)
            existing_ids.add(job["id"])
            added.append(job)

    if added:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        data["total_count"] = len(data["jobs"])
        save(data)

    return added
