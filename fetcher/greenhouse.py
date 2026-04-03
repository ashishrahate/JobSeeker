import requests
from datetime import datetime, timezone

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch(company: dict, keywords: dict) -> list[dict]:
    """
    Fetch jobs from Greenhouse API for a single company.
    Returns list of matched job dicts. Empty list on error or no match.
    """
    slug = company["slug"]
    url = BASE_URL.format(slug=slug)

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            print(f"[greenhouse] {company['name']}: slug '{slug}' not found (404) — verify slug")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[greenhouse] {company['name']}: request failed — {e}")
        return []

    matched = []
    for job in data.get("jobs", []):
        title = job.get("title", "")
        departments = " ".join(d.get("name", "") for d in job.get("departments", []))
        searchable = f"{title} {departments}".lower()

        if not _is_internship(searchable, keywords["internship_terms"]):
            continue

        category, matched_kws = _match_role(searchable, keywords["roles"], company["categories"])
        if not category:
            continue

        matched.append({
            "id": f"greenhouse_{job['id']}",
            "source_id": str(job["id"]),
            "ats": "greenhouse",
            "company_name": company["name"],
            "company_slug": slug,
            "title": title,
            "location": job.get("location", {}).get("name", ""),
            "department": departments.strip(),
            "url": job.get("absolute_url", ""),
            "posted_at": job.get("updated_at"),
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
