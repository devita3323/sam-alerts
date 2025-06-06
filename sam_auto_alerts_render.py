import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import os

# Use API key from env or fallback to hardcoded key
API_KEY = os.getenv("SAM_API_KEY", "NrJa4HrCopoLWrmIvc4s9hqhoYtJa8wnsB9ZscdT")
URL = "https://api.sam.gov/opportunities/v2/search"
TO_EMAIL = os.getenv("TO_EMAIL", "kyle.johnson@janesvillenissan.com")
FROM_EMAIL = os.getenv("FROM_EMAIL", "kyledevita3323@gmail.com")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Filters
STRICT_REQUIRED = ["left-hand drive"]
STRICT_INCLUDE = ["sedan", "suv", "pickup", "mid-size truck"]
BROAD_INCLUDE = ["passenger vehicle", "sedan", "suv", "pickup truck", "mid-size truck", "left-hand drive"]
EXCLUDE = [
    "passenger van", "van", "minivan", "shuttle", "bus", "forklift", "pallet jack", "trailer",
    "atv", "utv", "heavy equipment", "excavator", "backhoe", "tractor", "sweeper", "loader",
    "golf", "ambulance", "fire", "ladder", "armored vehicle", "boat", "motorcycle", "dump",
    "crane", "tank", "right-hand drive"
]

def is_valid(title, strict=True):
    title = title.lower()
    if any(exc in title for exc in EXCLUDE):
        return False
    if strict:
        return any(req in title for req in STRICT_REQUIRED) and any(inc in title for inc in STRICT_INCLUDE)
    else:
        return any(inc in title for inc in BROAD_INCLUDE)

def query_sam():
    today = datetime.today()

    # Check if this is the first run (no history yet)
    history_file = "seen_opportunities.csv"
    if os.path.exists(history_file):
        # Standard run: only grab the past 24 hours
        posted_from = today - timedelta(days=1)
    else:
        # First run: go back to April 1st, 2025
        posted_from = datetime(2025, 4, 1)

    params = {
        "api_key": API_KEY,
        "postedFrom": posted_from.strftime("%m/%d/%Y"),
        "postedTo": today.strftime("%m/%d/%Y"),
        "limit": 1000
    }

    response = requests.get(URL, params=params)
    return response.json().get("opportunitiesData", [])

def main():
    history_file = "seen_opportunities.csv"
    seen_ids = set()

    if os.path.exists(history_file):
        seen_df = pd.read_csv(history_file)
        seen_ids = set(seen_df["Notice ID"].values)

    opps = query_sam()
    new_results = []

    for opp in opps:
        title = opp.get("title", "").lower()
        notice_id = opp.get("noticeId")

        if notice_id in seen_ids:
            continue

        if is_valid(title, strict=True) or is_valid(title, strict=False):
            new_results.append({
                "Notice ID": notice_id,
                "Title": opp.get("title", ""),
                "Solicitation Number": opp.get("solicitationNumber", ""),
                "Posted": opp.get("postedDate", ""),
                "Due": opp.get("responseDeadLine", ""),
                "Agency": opp.get("departmentName", ""),
                "Link": f"https://sam.gov/opp/{notice_id}/view"
            })

    if not new_results:
        print("📭 No new results to send.")
        return

    df_new = pd.DataFrame(new_results)
    today = datetime.today().strftime("%Y%m%d")
    df_new.to_csv(f"sam_opps_{today}.csv", index=False)

    # Update seen
    df_seen_new = df_new[["Notice ID"]]
    if seen_ids:
        df_old = pd.read_csv(history_file)
        df_all = pd.concat([df_old, df_seen_new]).drop_duplicates()
    else:
        df_all = df_seen_new
    df_all.to_csv(history_file, index=False)

    # Email message
    msg = EmailMessage()
    msg["Subject"] = f"🚨 {len(new_results)} New SAM.gov Vehicle Contracts"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    body = "New vehicle-related opportunities:\n\n"

    for r in new_results:
        body += f"- {r['Title']}\n  Due: {r['Due']}\n  {r['Link']}\n\n"

    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(FROM_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)

    print(f"✅ Sent {len(new_results)} new results to {TO_EMAIL}")

if __name__ == "__main__":
    main()
