import os
import json
import time
import smtplib
import requests
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ─── CONFIG (set via environment variables) ───────────────────────────────────
APIFY_API_KEY   = os.environ["APIFY_API_KEY"]
EMAIL_SENDER    = os.environ["EMAIL_SENDER"]       # e.g. yourname@gmail.com
EMAIL_PASSWORD  = os.environ["EMAIL_PASSWORD"]     # Gmail App Password
EMAIL_RECIPIENT = os.environ["EMAIL_RECIPIENT"]    # where to send the report

# ─── APIFY ACTOR IDS ─────────────────────────────────────────────────────────
ACTORS = {
    "LinkedIn":    "curious_coder/linkedin-jobs-scraper",
    "Indeed":      "misceres/indeed-scraper",
    "Naukri":      "pratikdaigavane/naukri-jobs-scraper",
    "Internshala": "curious_coder/internshala-scraper",
}

SEARCH_QUERIES = [
    "software engineer fresher",
    "junior developer fresher",
    "software developer 0 experience",
    "fresher IT jobs",
    "entry level software engineer",
]

LOCATIONS = ["India", "Remote"]


def run_actor(actor_id: str, run_input: dict) -> list:
    """Start an Apify actor and wait for results."""
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_API_KEY}"
    resp = requests.post(url, json=run_input, timeout=30)
    resp.raise_for_status()
    run_id = resp.json()["data"]["id"]

    # Poll until finished
    for _ in range(60):
        time.sleep(10)
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_KEY}"
        status = requests.get(status_url, timeout=15).json()["data"]["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if status != "SUCCEEDED":
        print(f"  ⚠ Actor {actor_id} ended with status: {status}")
        return []

    dataset_id = requests.get(status_url, timeout=15).json()["data"]["defaultDatasetId"]
    items_url  = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_KEY}&format=json&limit=200"
    return requests.get(items_url, timeout=30).json()


def normalise(raw: dict, source: str) -> dict | None:
    """Map raw actor output to our standard schema."""
    def pick(*keys):
        for k in keys:
            v = raw.get(k)
            if v and str(v).strip() not in ("", "N/A", "null", "None"):
                return str(v).strip()
        return "N/A"

    company = pick("company", "companyName", "employer", "company_name", "organizationName")
    role    = pick("title", "jobTitle", "position", "role", "positionTitle")
    ctc     = pick("salary", "ctc", "salaryRange", "compensation", "stipend", "pay")
    link    = pick("url", "applyUrl", "jobUrl", "link", "applyLink", "jobLink", "externalApplyLink")

    if role == "N/A" or link == "N/A":
        return None

    return {
        "Source":  source,
        "Company": company,
        "Role":    role,
        "CTC / Salary": ctc,
        "Apply Link": link,
        "Location": pick("location", "jobLocation", "city", "place"),
        "Posted":   pick("postedAt", "datePosted", "publishedAt", "date"),
    }


def scrape_linkedin(queries, locations) -> list:
    results = []
    for query in queries[:3]:
        for loc in locations:
            print(f"  LinkedIn: '{query}' | {loc}")
            raw = run_actor(ACTORS["LinkedIn"], {
                "searchQueries": [query],
                "location": loc,
                "maxResults": 30,
                "contractType": "FULL_TIME",
            })
            for item in raw:
                n = normalise(item, "LinkedIn")
                if n:
                    results.append(n)
    return results


def scrape_indeed(queries, locations) -> list:
    results = []
    for query in queries[:3]:
        for loc in locations:
            print(f"  Indeed: '{query}' | {loc}")
            raw = run_actor(ACTORS["Indeed"], {
                "position": query,
                "country": "IN" if loc == "India" else "worldwide",
                "location": loc,
                "maxItems": 30,
                "startUrls": [],
            })
            for item in raw:
                n = normalise(item, "Indeed")
                if n:
                    results.append(n)
    return results


def scrape_naukri(queries) -> list:
    results = []
    for query in queries[:3]:
        print(f"  Naukri: '{query}'")
        raw = run_actor(ACTORS["Naukri"], {
            "keyword": query,
            "experience": "0",
            "location": "India",
            "maxResults": 30,
        })
        for item in raw:
            n = normalise(item, "Naukri")
            if n:
                results.append(n)
    return results


def scrape_internshala(queries) -> list:
    results = []
    for query in queries[:2]:
        print(f"  Internshala: '{query}'")
        raw = run_actor(ACTORS["Internshala"], {
            "searchQuery": query,
            "maxResults": 30,
        })
        for item in raw:
            n = normalise(item, "Internshala")
            if n:
                results.append(n)
    return results


def deduplicate(jobs: list) -> list:
    seen, out = set(), []
    for j in jobs:
        key = (j["Company"].lower(), j["Role"].lower())
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out


# ─── EXCEL BUILDER ────────────────────────────────────────────────────────────
SOURCE_COLORS = {
    "LinkedIn":    "0A66C2",
    "Indeed":      "2164F3",
    "Naukri":      "FF7555",
    "Internshala": "006BFF",
}

def build_excel(jobs: list, filepath: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Fresher Jobs"

    # Header
    headers = ["#", "Source", "Company", "Role", "CTC / Salary", "Location", "Posted", "Apply Link"]
    header_fill = PatternFill("solid", fgColor="1E293B")
    header_font = Font(bold=True, color="FFFFFF", name="Arial", size=11)
    thin = Side(style="thin", color="D1D5DB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    ws.row_dimensions[1].height = 30

    # Data rows
    for i, job in enumerate(jobs, 1):
        row = i + 1
        alt_fill = PatternFill("solid", fgColor="F8FAFC") if i % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        base_font = Font(name="Arial", size=10)

        data = [i, job["Source"], job["Company"], job["Role"],
                job["CTC / Salary"], job["Location"], job["Posted"], job["Apply Link"]]

        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = alt_fill
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=(col in (4, 8)))

            if col == 2:  # Source badge
                color = SOURCE_COLORS.get(str(val), "6B7280")
                cell.font = Font(name="Arial", size=10, bold=True, color=color)
            elif col == 8:  # Apply link — blue hyperlink style
                cell.font = Font(name="Arial", size=10, color="2563EB", underline="single")
                cell.hyperlink = str(val)
            else:
                cell.font = base_font

    # Column widths
    widths = [5, 13, 22, 35, 20, 18, 14, 45]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    # Freeze header
    ws.freeze_panes = "A2"

    # Summary sheet
    ws2 = wb.create_sheet("Summary")
    ws2["A1"] = "Job Scrape Summary"
    ws2["A1"].font = Font(bold=True, size=14, name="Arial", color="1E293B")

    ws2["A3"] = "Date"
    ws2["B3"] = str(date.today())
    ws2["A4"] = "Total Jobs"
    ws2["B4"] = f"=COUNTA('{ws.title}'!B2:B10000)-COUNTIF('{ws.title}'!B2:B10000,\"N/A\")"
    ws2["A5"] = "Sources"
    ws2["B5"] = ", ".join(ACTORS.keys())

    source_counts = {}
    for j in jobs:
        source_counts[j["Source"]] = source_counts.get(j["Source"], 0) + 1

    ws2["A7"] = "Breakdown by Source"
    ws2["A7"].font = Font(bold=True, name="Arial")
    for r, (src, cnt) in enumerate(source_counts.items(), 8):
        ws2.cell(row=r, column=1, value=src)
        ws2.cell(row=r, column=2, value=cnt)

    for col in ["A", "B"]:
        ws2.column_dimensions[col].width = 25

    wb.save(filepath)
    print(f"✅ Saved: {filepath}")


# ─── EMAIL SENDER ─────────────────────────────────────────────────────────────
def send_email(filepath: str, job_count: int):
    today = date.today().strftime("%d %b %Y")
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg["Subject"] = f"🧑‍💻 Fresher Software Jobs — {today} ({job_count} jobs)"

    body = f"""Hi,

Here is your daily fresher software job report for {today}.

📊 Total jobs found: {job_count}
🔍 Sources: LinkedIn, Indeed, Naukri, Internshala
📍 Locations: India + Remote

Open the attached Excel file to view all listings with direct apply links.

Good luck with your applications! 🚀

---
This email is auto-generated by your Job Scraper bot.
"""
    msg.attach(MIMEText(body, "plain"))

    with open(filepath, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(filepath)}")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
    print(f"📧 Email sent to {EMAIL_RECIPIENT}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    today     = date.today().strftime("%Y-%m-%d")
    filename  = f"fresher_jobs_{today}.xlsx"
    filepath  = os.path.join(os.path.dirname(__file__), filename)

    print("🔍 Starting job scrape...\n")
    all_jobs = []

    print("[1/4] LinkedIn")
    all_jobs += scrape_linkedin(SEARCH_QUERIES, LOCATIONS)

    print("[2/4] Indeed")
    all_jobs += scrape_indeed(SEARCH_QUERIES, LOCATIONS)

    print("[3/4] Naukri")
    all_jobs += scrape_naukri(SEARCH_QUERIES)

    print("[4/4] Internshala")
    all_jobs += scrape_internshala(SEARCH_QUERIES)

    jobs = deduplicate(all_jobs)
    print(f"\n✅ Total unique jobs: {len(jobs)}\n")

    build_excel(jobs, filepath)
    send_email(filepath, len(jobs))


if __name__ == "__main__":
    main()
