import requests
from datetime import datetime, timezone

BASE_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"


def fetch(company: dict, keywords: dict) -> list[dict]:
    """
    Fetch jobs from Lever API for a single company.
    Returns list of matched job dicts. Empty list on error or no match.
    """
    slug = company["slug"]
    url = BASE_URL.format(slug=slug)

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            print(f"[lever] {company['name']}: slug '{slug}' not found (404) — verify slug")
            return []
        resp.raise_for_status()
        postings = resp.json()
    except Exception as e:
        print(f"[lever] {company['name']}: request failed — {e}")
        return []

    matched = []
    for job in postings:
        title = job.get("text", "")
        categories = job.get("categories", {})
        department = categories.get("department", "") or categories.get("team", "")
        searchable = f"{title} {department}".lower()

        if not _is_internship(searchable, keywords["internship_terms"]):
            continue

        category, matched_kws = _match_role(searchable, keywords["roles"], company["categories"])
        if not category:
            continue

        # Lever timestamps are Unix ms
        created_ms = job.get("createdAt")
        posted_at = (
            datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
            if created_ms else None
        )

        matched.append({
            "id": f"lever_{job['id']}",
            "source_id": job["id"],
            "ats": "lever",
            "company_name": company["name"],
            "company_slug": slug,
            "title": title,
            "location": categories.get("location", ""),
            "department": department,
            "url": job.get("hostedUrl", ""),
            "posted_at": posted_at,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "role_category": category,
            "keywords_matched": matched_kws,
            "opt_cpt": company.get("opt_cpt"),
        })

    return matched


def _is_internship(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def _match_role(text: str, role_keywords: dict, allowed_categories: list[str]) -> tuple[str | None, list[str]]:
    for category in allowed_categories:
        kws = role_keywords.get(category, [])
        hits = [kw for kw in kws if kw in text]
        if hits:
            return category, hits
    return None, []
