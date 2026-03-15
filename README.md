# 🧑‍💻 Daily Fresher Software Jobs Scraper

Scrapes **LinkedIn, Indeed, Naukri & Internshala** every day at **9:00 AM IST**
for fresher software jobs in India + Remote, and emails you a clean Excel sheet.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `scraper.py` | Main scraper + Excel builder + email sender |
| `.github/workflows/daily_jobs.yml` | GitHub Actions schedule (runs daily at 9 AM IST) |

---

## 🚀 Setup (One-time, ~10 minutes)

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) → **New repository**
2. Name it anything e.g. `fresher-jobs-bot`
3. Set it to **Private**
4. Upload both files: `scraper.py` and `.github/workflows/daily_jobs.yml`

---

### Step 2 — Get your Apify API key

1. Sign in at [apify.com](https://apify.com)
2. Go to **Settings → Integrations → API tokens**
3. Copy your **Personal API token**

> ⚠️ Make sure your Apify account has enough credits. Each daily run uses ~4 actor calls.

---

### Step 3 — Set up Gmail App Password

> You need a **Gmail App Password** (not your regular Gmail password)

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already)
3. Search for **"App Passwords"** → Create one for "Mail"
4. Copy the 16-character password shown

---

### Step 4 — Add secrets to GitHub

In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these 4 secrets:

| Secret Name | Value |
|-------------|-------|
| `APIFY_API_KEY` | Your Apify API token |
| `EMAIL_SENDER` | Your Gmail address (e.g. `you@gmail.com`) |
| `EMAIL_PASSWORD` | Your Gmail App Password (16 chars) |
| `EMAIL_RECIPIENT` | Email where you want to receive jobs |

---

### Step 5 — Test it manually

1. Go to your repo → **Actions** tab
2. Click **"Daily Fresher Jobs Scraper"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Wait ~15–20 minutes
5. Check your inbox! ✅

---

## 📊 Excel Output Format

The emailed `.xlsx` file has 2 sheets:

### Sheet 1: Fresher Jobs
| # | Source | Company | Role | CTC / Salary | Location | Posted | Apply Link |
|---|--------|---------|------|--------------|----------|--------|------------|
| 1 | LinkedIn | Google | SWE Fresher | 12–18 LPA | Bangalore | 2 days ago | [link] |
| 2 | Naukri | Infosys | Junior Dev | 3.6 LPA | Remote | Today | [link] |

### Sheet 2: Summary
- Date, total jobs found, breakdown by source

---

## ⚙️ Customisation

Edit `scraper.py` to change:

```python
# Change search queries
SEARCH_QUERIES = [
    "software engineer fresher",
    "junior developer fresher",
    ...
]

# Change locations
LOCATIONS = ["India", "Remote"]

# Change max results per query (in each scrape_* function)
"maxResults": 30  # increase for more results
```

---

## ❓ Troubleshooting

| Problem | Fix |
|---------|-----|
| No email received | Check spam folder; verify Gmail App Password |
| Apify actor fails | Check Apify dashboard for run logs; ensure account has credits |
| GitHub Action not running | Confirm `.github/workflows/daily_jobs.yml` is in root of repo |
| Jobs showing "N/A" for CTC | Many companies don't publish salary — this is normal |

---

## 🔒 Privacy & Cost

- All secrets are encrypted by GitHub — never visible in logs
- Apify free tier gives ~$5/month credits; this bot uses ~$0.50–1.00/day
- Upgrade Apify plan if you need more results

---

*Built with ❤️ using Apify + Python + GitHub Actions*
