import os
from pathlib import Path

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MUTE_FLAG    = Path(__file__).parent.parent / "data" / "mute.flag"


def is_muted() -> bool:
    return MUTE_FLAG.exists()

CATEGORY_LABEL = {
    "salesforce": "Salesforce Dev/Arch",
    "ai_eng":     "AI Engineering",
    "ds_ml":      "Data Science / ML",
}

OPT_LABEL = {
    True:  "OPT/CPT",
    False: "No OPT",
    None:  "OPT unknown",
}


def send(job: dict) -> None:
    if is_muted():
        print(f"[notifier] Muted — skipping notification for: {job['title']} @ {job['company_name']}")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(f"[notifier] Skipping Telegram — env vars not set. Job: {job['title']} @ {job['company_name']}")
        return

    category = CATEGORY_LABEL.get(job["role_category"], job["role_category"])
    opt = OPT_LABEL.get(job["opt_cpt"])
    location = job.get("location") or "Location not listed"
    posted = (job.get("posted_at") or "")[:10]  # YYYY-MM-DD

    text = (
        f"New Internship Posted\n\n"
        f"Company: {job['company_name']}\n"
        f"Role: {job['title']}\n"
        f"Category: {category}\n"
        f"Location: {location}\n"
        f"Posted: {posted}\n"
        f"Work Auth: {opt}\n"
        f"Apply: {job['url']}"
    )

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token),
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"[notifier] Sent: {job['title']} @ {job['company_name']}")
    except Exception as e:
        print(f"[notifier] Failed to send Telegram message: {e}")


def send_summary(added: list[dict]) -> None:
    """Send a single summary message if many jobs were found at once."""
    if is_muted():
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id or not added:
        return

    counts = {}
    for job in added:
        label = CATEGORY_LABEL.get(job["role_category"], job["role_category"])
        counts[label] = counts.get(label, 0) + 1

    breakdown = "\n".join(f"  {label}: {n}" for label, n in counts.items())
    text = (
        f"Internship Scan Complete\n\n"
        f"{len(added)} new listing(s) found:\n{breakdown}\n\n"
        f"Individual alerts sent above."
    )

    try:
        requests.post(
            TELEGRAM_API.format(token=token),
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception as e:
        print(f"[notifier] Failed to send summary: {e}")
