# Claude Context — JobSeeker Project

This file is for Claude to pick up context in future sessions.
Read this before making any changes or suggestions.

---

## Who the User Is

- Incoming master's student, joining fall 2026
- International student (F-1 visa) — OPT/CPT eligibility is a critical filter
- Looking for **Summer 2027 internships** in the US
- Target roles:
  1. **Salesforce Developer / Architect** (at companies using Salesforce — not only Salesforce the company)
  2. **AI Engineering** internships
  3. **Data Science / ML Engineering** internships
- Prefers: free tools, simple solutions, Telegram for notifications
- Does NOT want: paid services, overly complex architectures, mark-as-applied features in dashboard

---

## What Has Been Built (Layer 1 — Complete)

A fully functional internship tracker:

```
JobSeeker/
├── .github/workflows/fetch_jobs.yml   ← GitHub Actions cron (every 4h)
├── fetcher/
│   ├── greenhouse.py                  ← Greenhouse public JSON API fetcher
│   ├── lever.py                       ← Lever public JSON API fetcher
│   ├── storage.py                     ← dedup + read/write to data/jobs.json
│   ├── notifier.py                    ← Telegram bot (per-job + summary)
│   └── main.py                        ← orchestrator entry point
├── index.html                         ← GitHub Pages dashboard (vanilla HTML/CSS/JS)
├── data/jobs.json                     ← all captured job listings (flat file)
├── companies.json                     ← 53 companies: 47 Greenhouse, 6 Lever
├── requirements.txt                   ← requests, python-dotenv, streamlit, pandas
├── .env.example                       ← TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
├── .gitignore
├── .streamlit/secrets.toml.example   ← GITHUB_RAW_URL for Streamlit Cloud
├── SETUP_STEPS.md                     ← step-by-step user setup guide
└── Internship_Research_Master.md      ← full 100-company research database
```

### How it works
1. GitHub Actions runs `fetcher/main.py` every 4 hours (free tier)
2. Fetches all Greenhouse + Lever companies via their public JSON APIs (no scraping, no auth)
3. Filters: job title must contain internship terms AND match role keywords from `companies.json`
4. Deduplicates against existing `data/jobs.json` by job ID
5. Sends Telegram message for each new listing found
6. Commits updated `data/jobs.json` back to repo with `[skip ci]` to prevent loop
7. GitHub Pages serves `index.html` which fetches `data/jobs.json` from the same repo every 5 min
8. Dashboard has filters: role category, company, work auth, date range, keyword search; sortable columns

### Data storage
- **No database** — flat `data/jobs.json` file committed to the GitHub repo
- This was a deliberate choice: zero external dependencies, version history via git, free forever
- User explicitly declined Supabase and chose JSON file over any database option

---

## What Is NOT Built Yet (Layer 2 — Pending)

The system currently covers **47 Greenhouse + 6 Lever companies** via clean JSON APIs.

**Not yet covered** — companies using JS-heavy ATS systems that need browser rendering:

| ATS | Key Companies |
|---|---|
| Workday | Google (no — Phenom), Salesforce, Accenture, Deloitte, IBM, PwC, EY, KPMG, Adobe, Intel, AMD, Visa, Mastercard, Capital One, PayPal, Intuit, Fidelity |
| Phenom | Google, Meta, Microsoft, LinkedIn |
| Custom | Amazon, Apple, Jane Street, TikTok |
| iCIMS | Goldman Sachs, Cognizant, Wipro, UnitedHealth |
| Taleo | Morgan Stanley, Oracle |

**Planned approach for Layer 2:**
- Self-host `changedetection.io` (open-source: `dgtlmoon/changedetection.io`) via Docker
- Deploy on **Fly.io free tier** (always-on, 256MB RAM sufficient) or **Oracle Cloud Always Free VM**
- Uses Playwright browser mode to render JS-heavy Workday/Phenom pages
- Same Telegram bot for notifications
- User confirmed they want to use the open-source repo, not the hosted service

---

## Key Design Decisions (Do Not Reverse Without Asking)

| Decision | Reason |
|---|---|
| JSON file instead of database | User said "no" to Supabase and all DB options — wants zero external dependencies |
| No "mark as applied" feature | User explicitly said no |
| Telegram over email | User's preference |
| GitHub Actions over self-hosted cron | Free, no server needed, reliable |
| GitHub Pages (`index.html`) over Streamlit | Zero dependencies, no account needed, one file to maintain |
| Layer 1 first (Greenhouse/Lever) | Cleanest data source — covers ~50 companies with no scraping |

---

## Companies Configuration

`companies.json` has 53 companies total:
- 47 in `"greenhouse"` array
- 6 in `"lever"` array

Keywords are split into:
- `internship_terms`: used to confirm it's an internship posting
- `roles.salesforce`: Salesforce-specific keywords
- `roles.ai_eng`: AI engineering keywords
- `roles.ds_ml`: data science / ML keywords

A job must match BOTH an internship term AND at least one role keyword to be captured.

**Known slugs that may need verification** (could be 404):
- McKinsey (`mckinsey`) — large firm, may use custom portal
- D.E. Shaw (`deshaw`) — very secretive about job postings
- SpaceX (`spacex`) — ITAR restrictions, limited public postings
- ServiceNow (`servicenow`) — uses SmartRecruiters, not Greenhouse

---

## Research File

`Internship_Research_Master.md` contains:
- 100 companies with cohort sizes, app open/close dates, OPT/CPT status, ATS system, compensation, notes
- Summer 2027 month-by-month timeline
- OPT/CPT quick-reference matrix
- ATS systems breakdown
- Salesforce practice rankings
- Top ML/AI intern hirers by volume
- Architecture decision (Section 15)

This file is the source of truth for company research. Do not delete it.

---

## Secrets Required

| Secret | Where set | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | GitHub repo → Settings → Secrets → Actions | Send Telegram notifications |
| `TELEGRAM_CHAT_ID` | GitHub repo → Settings → Secrets → Actions | Which chat to notify |
| `GITHUB_RAW_URL` | Streamlit Cloud → App Settings → Secrets | Dashboard reads jobs.json |

Local development: copy `.env.example` to `.env` and fill in values.

---

## What to Do Next (Suggested Priorities)

### If user has completed SETUP_STEPS.md:
- Verify slugs that returned 404 during first run
- Add more companies to `companies.json` if needed
- Begin Layer 2: self-host `changedetection.io` for Workday companies

### If user wants to expand coverage:
- Add Workday companies via changedetection.io (Layer 2)
- Add LinkedIn job alerts as passive backup
- Add the SimplifyJobs GitHub repo as a tracked source

### If user wants to improve the fetcher:
- Add retry logic with exponential backoff in `greenhouse.py` and `lever.py`
- Add rate limiting between API calls (currently fires all requests with no delay)
- Add a `verify_slugs.py` script that checks all slugs and reports 404s

### If user wants to improve the dashboard:
- Add a timeline chart (jobs discovered over time)
- Add company logo display
- Add direct link to the company's full jobs board (not just individual listing)

---

## Timeline Context

- Current date: March 2026
- **Summer 2027 internship postings begin: July–August 2026** (Amazon and Databricks post first)
- **Peak posting window: September–October 2026**
- The fetcher will find nothing relevant until ~July 2026 — that is expected and normal
- User should confirm the system is working before July 2026 by running it manually and checking that the GitHub Actions workflow completes successfully
