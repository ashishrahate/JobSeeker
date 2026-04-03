"""
server.py — Local admin server for JobSeeker dashboard.

Run:   python server.py
Stop:  Ctrl+C

When running, the dashboard at https://ashishrahate.github.io/JobSeeker/
will detect it automatically and show the admin panel.

Requires .env with:
  GITHUB_TOKEN=<fine-grained PAT: Actions RW + Contents RW on this repo>
  GITHUB_OWNER=ashishrahate
  GITHUB_REPO=JobSeeker
"""

import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv(Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)  # allow all origins — server is local-only, no security risk

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = os.environ.get("GITHUB_OWNER")
REPO  = os.environ.get("GITHUB_REPO")

GH_HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
MUTE_PATH = "data/mute.flag"


def gh(method: str, path: str, **kwargs):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    return requests.request(method, url, headers=GH_HEADERS, timeout=15, **kwargs)


def cfg_ok():
    return bool(TOKEN and OWNER and REPO)


def cfg_error():
    missing = [k for k, v in {"GITHUB_TOKEN": TOKEN, "GITHUB_OWNER": OWNER, "GITHUB_REPO": REPO}.items() if not v]
    return f"Missing in .env: {', '.join(missing)}"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    sys.path.insert(0, str(Path(__file__).parent))
    from fetcher import db
    stats = db.get_stats()

    mute_resp = gh("GET", f"contents/{MUTE_PATH}")
    muted = mute_resp.status_code == 200

    return jsonify({
        "server": "online",
        "repo": f"{OWNER}/{REPO}",
        "db": stats,
        "muted": muted,
    })


@app.post("/api/fetch")
def trigger_fetch():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    resp = gh("POST", "actions/workflows/fetch_jobs.yml/dispatches",
              json={"ref": "main"})
    if resp.status_code == 204:
        return jsonify({"ok": True, "message": "Fetch triggered — data updates in ~1 min"})
    return jsonify({"error": f"GitHub API {resp.status_code}: {resp.text}"}), 502


@app.post("/api/archive")
def trigger_archive():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    days = str(request.json.get("days", 60))
    resp = gh("POST", "actions/workflows/manage_db.yml/dispatches",
              json={"ref": "main", "inputs": {"action": "archive", "days": days}})
    if resp.status_code == 204:
        return jsonify({"ok": True, "message": f"Archive triggered — jobs older than {days} days will be archived"})
    return jsonify({"error": f"GitHub API {resp.status_code}: {resp.text}"}), 502


@app.post("/api/purge")
def trigger_purge():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    resp = gh("POST", "actions/workflows/manage_db.yml/dispatches",
              json={"ref": "main", "inputs": {"action": "purge", "days": "0"}})
    if resp.status_code == 204:
        return jsonify({"ok": True, "message": "Purge triggered — archived jobs will be deleted"})
    return jsonify({"error": f"GitHub API {resp.status_code}: {resp.text}"}), 502


@app.post("/api/mute")
def mute():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    resp = gh("PUT", f"contents/{MUTE_PATH}", json={
        "message": "chore: mute notifications [skip ci]",
        "content": base64.b64encode(b"").decode(),
        "branch": "main",
    })
    if resp.status_code in (200, 201):
        return jsonify({"ok": True, "muted": True})
    return jsonify({"error": f"GitHub API {resp.status_code}: {resp.text}"}), 502


@app.delete("/api/mute")
def unmute():
    if not cfg_ok():
        return jsonify({"error": cfg_error()}), 500

    get_resp = gh("GET", f"contents/{MUTE_PATH}")
    if get_resp.status_code == 404:
        return jsonify({"ok": True, "muted": False})

    sha = get_resp.json().get("sha")
    resp = gh("DELETE", f"contents/{MUTE_PATH}", json={
        "message": "chore: unmute notifications [skip ci]",
        "sha": sha,
        "branch": "main",
    })
    if resp.status_code == 200:
        return jsonify({"ok": True, "muted": False})
    return jsonify({"error": f"GitHub API {resp.status_code}: {resp.text}"}), 502


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not cfg_ok():
        print(f"\nERROR: {cfg_error()}")
        print("Add these to your .env file and try again.\n")
        sys.exit(1)
    print(f"\nJobSeeker admin server — http://localhost:5000")
    print(f"Repo: {OWNER}/{REPO}")
    print("Open your dashboard — admin panel appears automatically.")
    print("Stop with Ctrl+C\n")
    app.run(port=5000, debug=False)
