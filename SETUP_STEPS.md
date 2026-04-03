# JobSeeker — Setup Steps

Complete these in order. Estimated time: 20–30 minutes.

---

## Step 1 — Install Python dependencies locally

```bash
cd "C:\Users\ashis\OneDrive\Desktop\AI Projects\JobSeeker"
pip install -r requirements.txt
```

---

## Step 2 — Create your Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow prompts — give it any name (e.g. `JobSeekerBot`) and username (e.g. `my_jobseeker_bot`)
4. BotFather gives you a **token** — looks like `7123456789:AAFxxxxxx` — copy it
5. Now open your new bot in Telegram and send it any message (e.g. "hello")
6. In your browser, visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Replace `<YOUR_TOKEN>` with the token from step 4
7. In the response JSON, find `"chat"` → `"id"` — that is your **Chat ID** (a number like `987654321`)

Keep both values handy for the next steps.

---

## Step 3 — Test the fetcher locally

1. Copy the env example file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your values:
   ```
   TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxx
   TELEGRAM_CHAT_ID=987654321
   ```
3. Run the fetcher:
   ```bash
   python fetcher/main.py
   ```
4. Check your Telegram — you should receive messages for any live internship matches
5. Check `data/jobs.json` — it should now have entries

If a company logs `404 — verify slug`, see Step 8 below.

---

## Step 4 — Push to GitHub

1. Go to [github.com](https://github.com) and create a **new repository**
   - Name it anything, e.g. `jobseeker`
   - Set it to **Private** (recommended — keeps your jobs data personal)
   - Do NOT initialize with README (you already have files)

2. In your terminal:
   ```bash
   cd "C:\Users\ashis\OneDrive\Desktop\AI Projects\JobSeeker"
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```
   Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual values.

---

## Step 5 — Add secrets to GitHub Actions

1. On GitHub, go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add these two:

   | Name | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | Your bot token from Step 2 |
   | `TELEGRAM_CHAT_ID` | Your chat ID from Step 2 |

---

## Step 6 — Trigger the workflow manually (verify it works)

1. On GitHub, go to your repo → **Actions** tab
2. Click **Fetch Internship Listings** in the left panel
3. Click **Run workflow** → **Run workflow** (green button)
4. Watch it run — should take 1–2 minutes
5. After it completes, check:
   - Your Telegram for any new job alerts
   - `data/jobs.json` in the repo — it should be updated with a commit message `chore: update job listings`

After this, it runs automatically every 4 hours forever.

---

## Step 7 — Enable the GitHub Pages dashboard

The dashboard is a single `index.html` file in the repo root — no accounts, no secrets, no extra setup beyond flipping one switch on GitHub.

1. On GitHub, go to your repo → **Settings** → **Pages**
2. Under **Build and deployment**, set:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` → Folder: `/ (root)`
3. Click **Save**
4. Wait ~1 minute — your dashboard is live at:
   ```
   https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
   ```

That's it. The dashboard fetches `data/jobs.json` directly from the same repo and refreshes every 5 minutes automatically. No secrets to configure.

> **Note:** GitHub Pages requires the repo to be **public** for the free plan. If you want to keep the repo private, you'll need GitHub Pro — or just bookmark the raw URL for local use by opening `index.html` directly in your browser (it will fall back to `./data/jobs.json` locally).

> **Private repo workaround:** Open `index.html` locally in any browser — it reads `data/jobs.json` from the local folder. Run `git pull` whenever you want the latest data.

---

## Step 8 — Fix any 404 slugs (if needed)

If the fetcher logs something like:
```
[greenhouse] McKinsey: slug 'mckinsey' not found (404) — verify slug
```

Fix it by:
1. Open your browser and visit:
   ```
   https://boards-api.greenhouse.io/v1/boards/mckinsey/jobs
   ```
2. If you get a JSON response with jobs → slug is correct (might have been a network blip)
3. If you get a 404 → search for the correct slug:
   - Go to the company's careers page
   - Look for a URL like `boards.greenhouse.io/SLUG` — the SLUG is what you need
   - Update `companies.json` with the correct slug

For Lever companies, test at:
```
https://api.lever.co/v0/postings/SLUG?mode=json
```

---

## Step 9 — Add more companies (optional, anytime)

Open `companies.json` and add to either the `"greenhouse"` or `"lever"` array:

```json
{ "name": "Company Name", "slug": "their-greenhouse-slug", "categories": ["ds_ml"], "opt_cpt": true }
```

Valid categories: `"salesforce"`, `"ai_eng"`, `"ds_ml"`

Valid `opt_cpt` values: `true`, `false`, `null` (unknown)

Push to GitHub → the next scheduled run picks it up automatically.

---

## Quick Reference — What's Running Where

| Component | Where | Cost |
|---|---|---|
| Fetcher (runs every 4h) | GitHub Actions | Free |
| Job data storage | `data/jobs.json` in your GitHub repo | Free |
| Telegram notifications | Your Telegram app | Free |
| Interactive dashboard | GitHub Pages (`index.html`) | Free |

**Total cost: $0/month, forever.**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No Telegram messages | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are correct in GitHub Secrets |
| GitHub Actions failing | Go to Actions tab → click the failed run → read the error log |
| Dashboard shows no data | Make sure GitHub Pages is enabled (Step 7) and the repo is public; or open `index.html` locally |
| `404` for a company slug | See Step 8 above |
| Fetcher finds nothing | Postings for Summer 2027 likely haven't opened yet — check back Aug–Sep 2026 |
