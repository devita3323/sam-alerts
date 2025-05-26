import requests
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import os

API_KEY = "NrJa4HrCopoLWrmIvc4s9hqhoYtJa8wnsB9ZscdT"
URL = "https://api.sam.gov/opportunities/v2/search"
TO_EMAIL = "kyle.johnson@janesvillenissan.com"
FROM_EMAIL = "kyledevita3323@gmail.com"
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

REQUIRED = ["left-hand drive"]
INCLUDE = ["sedan", "suv", "pickup", "mid-size truck"]
EXCLUDE = [
    "passenger van", "van", "minivan", "shuttle", "bus", "forklift", "pallet jack", "trailer",
    "atv", "utv", "heavy equipment", "excavator", "backhoe", "tractor", "sweeper", "loader",
    "golf", "ambulance", "fire", "ladder", "armored vehicle", "boat", "motorcycle", "dump",
    "crane", "tank", "right-hand drive"
]

today = datetime.today()
yesterday = today - timedelta(days=1)
params = {
    "api_key": API_KEY,
    "postedFrom": yesterday.strftime("%m/%d/%Y"),
    "postedTo": today.strftime("%m/%d/%Y"),
    "limit": 1000
}

response = requests.get(URL, params=params)
data = response.json()

results = []
for opp in data.get("opportunitiesData", []):
    title = opp.get("title", "").lower()
    if any(req in title for req in REQUIRED):
        if any(inc in title for inc in INCLUDE):
            if not any(exc in title for exc in EXCLUDE):
                results.append({
                    "Notice ID": opp.get("noticeId"),
                    "Title": opp.get("title", ""),
                    "Solicitation Number": opp.get("solicitationNumber", ""),
                    "Posted": opp.get("postedDate", ""),
                    "Due": opp.get("responseDeadLine", ""),
                    "Agency": opp.get("departmentName", ""),
                    "Link": f"https://sam.gov/opp/{opp.get('noticeId')}/view"
                })

# Load or create history file
history_file = "seen_opportunities.csv"
seen_ids = set()
if os.path.exists(history_file):
    seen_df = pd.read_csv(history_file)
    seen_ids = set(seen_df["Notice ID"].values)

# Filter to only new entries
new_results = [r for r in results if r["Notice ID"] not in seen_ids]

if new_results:
    df_new = pd.DataFrame(new_results)
    df_new.to_csv(f"sam_vehicle_opportunities_{today.strftime('%Y%m%d')}.csv", index=False)

    # Update history
    df_seen_new = pd.DataFrame(new_results)[["Notice ID"]]
    if seen_ids:
        df_old = pd.read_csv(history_file)
        df_all = pd.concat([df_old, df_seen_new]).drop_duplicates()
    else:
        df_all = df_seen_new
    df_all.to_csv(history_file, index=False)

    # Compose email
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
else:
    print("📭 No new results to send.")
