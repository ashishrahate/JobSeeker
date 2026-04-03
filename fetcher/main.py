"""
main.py — Entry point for the internship fetcher.

Run manually:   python fetcher/main.py
Scheduled via:  .github/workflows/fetch_jobs.yml (every 4 hours)

Requires env vars (set in GitHub Actions secrets or local .env):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

import json
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from fetcher import ...` works
# regardless of how this script is invoked (python fetcher/main.py or -m fetcher.main)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env locally if it exists (not needed in GitHub Actions)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from fetcher import greenhouse, lever, notifier, storage

COMPANIES_FILE = Path(__file__).parent.parent / "companies.json"


def load_config() -> dict:
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run() -> None:
    config = load_config()
    keywords = config["keywords"]

    all_found: list[dict] = []

    # --- Greenhouse ---
    print(f"\nFetching from Greenhouse ({len(config['greenhouse'])} companies)...")
    for company in config["greenhouse"]:
        jobs = greenhouse.fetch(company, keywords)
        if jobs:
            print(f"  {company['name']}: {len(jobs)} match(es)")
        all_found.extend(jobs)

    # --- Lever ---
    print(f"\nFetching from Lever ({len(config['lever'])} companies)...")
    for company in config["lever"]:
        jobs = lever.fetch(company, keywords)
        if jobs:
            print(f"  {company['name']}: {len(jobs)} match(es)")
        all_found.extend(jobs)

    print(f"\nTotal matched across all sources: {len(all_found)}")

    # Dedup + save — only returns genuinely new jobs
    added = storage.add_new_jobs(all_found)
    print(f"New (not seen before): {len(added)}")

    if not added:
        print("Nothing new. Exiting.")
        return

    # Send individual Telegram alerts for each new job
    for job in added:
        notifier.send(job)

    # Send a summary if more than 3 new jobs
    if len(added) > 3:
        notifier.send_summary(added)

    print(f"\nDone. {len(added)} new job(s) saved and notified.")


if __name__ == "__main__":
    run()
