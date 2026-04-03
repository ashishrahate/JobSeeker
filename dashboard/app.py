"""
Streamlit dashboard for JobSeeker internship tracker.

Deploy free on: https://streamlit.io/cloud
Connect to your GitHub repo — it reads jobs.json directly from the repo.

Set in Streamlit Cloud secrets (or locally in .streamlit/secrets.toml):
  GITHUB_RAW_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/data/jobs.json"
"""

import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="JobSeeker — Internship Tracker",
    page_icon="🎯",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "salesforce": "Salesforce Dev/Arch",
    "ai_eng":     "AI Engineering",
    "ds_ml":      "Data Science / ML",
}
OPT_LABELS = {
    True:  "✅ OPT/CPT",
    False: "❌ No OPT",
    None:  "❓ Unknown",
}
CATEGORY_COLORS = {
    "Salesforce Dev/Arch": "#0070D2",
    "AI Engineering":      "#9B59B6",
    "Data Science / ML":   "#27AE60",
}


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Refresh every 5 minutes
def load_jobs() -> pd.DataFrame:
    # Try Streamlit secrets first (deployed), fall back to local file
    raw_url = st.secrets.get("GITHUB_RAW_URL", None)

    if raw_url:
        try:
            resp = requests.get(raw_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Failed to fetch jobs from GitHub: {e}")
            return pd.DataFrame()
    else:
        # Local development — read from file
        import os
        local_path = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.json")
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            st.warning("No jobs.json found. Run `python fetcher/main.py` first.")
            return pd.DataFrame()

    jobs = data.get("jobs", [])
    if not jobs:
        return pd.DataFrame()

    df = pd.DataFrame(jobs)

    # Normalize columns
    df["role_category"] = df["role_category"].map(CATEGORY_LABELS).fillna(df["role_category"])
    df["opt_cpt"] = df["opt_cpt"].map(OPT_LABELS)
    df["discovered_at"] = pd.to_datetime(df["discovered_at"], utc=True, errors="coerce")
    df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True, errors="coerce")
    df["posted_date"] = df["posted_at"].dt.strftime("%Y-%m-%d").fillna("Unknown")
    df["discovered_date"] = df["discovered_at"].dt.strftime("%Y-%m-%d %H:%M UTC")
    df["keywords_matched"] = df["keywords_matched"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else x
    )

    return df


def get_last_updated(df: pd.DataFrame) -> str:
    if df.empty or "discovered_at" not in df.columns:
        return "Never"
    latest = df["discovered_at"].max()
    if pd.isna(latest):
        return "Never"
    return latest.strftime("%b %d, %Y at %H:%M UTC")


# ── Layout ────────────────────────────────────────────────────────────────────
st.title("🎯 JobSeeker — Internship Tracker")
st.caption("Tracking Salesforce, AI Engineering, and Data Science / ML internships across 50+ companies.")

df = load_jobs()

# ── Metrics row ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

now = datetime.now(tz=timezone.utc)
today_cutoff = now - timedelta(hours=24)

if not df.empty:
    new_today = len(df[df["discovered_at"] >= today_cutoff]) if "discovered_at" in df.columns else 0
    sf_count   = len(df[df["role_category"] == CATEGORY_LABELS["salesforce"]])
    ai_count   = len(df[df["role_category"] == CATEGORY_LABELS["ai_eng"]])
    ml_count   = len(df[df["role_category"] == CATEGORY_LABELS["ds_ml"]])
else:
    new_today = sf_count = ai_count = ml_count = 0

col1.metric("Total Listings",     len(df) if not df.empty else 0)
col2.metric("New (Last 24h)",     new_today)
col3.metric("Salesforce",         sf_count)
col4.metric("AI Engineering",     ai_count)
col5.metric("Data Science / ML",  ml_count)

st.caption(f"Last updated: {get_last_updated(df)}")
st.divider()

if df.empty:
    st.info("No jobs found yet. The fetcher runs every 4 hours via GitHub Actions.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")

# Role category
all_categories = sorted(df["role_category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Role Category",
    options=all_categories,
    default=all_categories,
)

# Company
all_companies = sorted(df["company_name"].dropna().unique().tolist())
selected_companies = st.sidebar.multiselect(
    "Company",
    options=all_companies,
    default=[],
    placeholder="All companies",
)

# OPT/CPT
opt_options = sorted(df["opt_cpt"].dropna().unique().tolist())
selected_opt = st.sidebar.multiselect(
    "Work Authorization",
    options=opt_options,
    default=opt_options,
)

# Date range
date_filter = st.sidebar.selectbox(
    "Discovered within",
    options=["All time", "Last 24 hours", "Last 7 days", "Last 30 days"],
    index=0,
)

# Keyword search
search = st.sidebar.text_input("Search title / keywords", placeholder="e.g. Apex, LLM, NLP")

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()

if selected_categories:
    filtered = filtered[filtered["role_category"].isin(selected_categories)]

if selected_companies:
    filtered = filtered[filtered["company_name"].isin(selected_companies)]

if selected_opt:
    filtered = filtered[filtered["opt_cpt"].isin(selected_opt)]

if date_filter != "All time" and "discovered_at" in filtered.columns:
    delta_map = {"Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30}
    cutoff = now - timedelta(days=delta_map[date_filter])
    filtered = filtered[filtered["discovered_at"] >= cutoff]

if search:
    mask = (
        filtered["title"].str.contains(search, case=False, na=False) |
        filtered["keywords_matched"].str.contains(search, case=False, na=False) |
        filtered["company_name"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

# ── Results ───────────────────────────────────────────────────────────────────
st.subheader(f"Listings ({len(filtered)} results)")

if filtered.empty:
    st.warning("No listings match your current filters.")
else:
    # Sort newest first
    filtered = filtered.sort_values("discovered_at", ascending=False)

    display_cols = {
        "company_name":    "Company",
        "title":           "Title",
        "role_category":   "Category",
        "location":        "Location",
        "posted_date":     "Posted",
        "opt_cpt":         "Work Auth",
        "keywords_matched":"Keywords",
        "url":             "Apply Link",
        "discovered_date": "Discovered",
    }

    display_df = filtered[list(display_cols.keys())].rename(columns=display_cols)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Apply Link": st.column_config.LinkColumn("Apply Link", display_text="Apply"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="medium"),
            "Keywords": st.column_config.TextColumn("Keywords", width="medium"),
        },
    )

# ── Breakdown chart ───────────────────────────────────────────────────────────
st.divider()
st.subheader("Breakdown by Company")

if not filtered.empty:
    company_counts = (
        filtered.groupby(["company_name", "role_category"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    st.bar_chart(
        company_counts.pivot(index="company_name", columns="role_category", values="count").fillna(0),
        use_container_width=True,
    )
