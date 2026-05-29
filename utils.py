import requests
import os
import json
from datetime import datetime, timezone, timedelta

# Create an IST timezone object
IST = timezone(timedelta(hours=5, minutes=30))

STATE_FILE = "last_run.json"

def get_last_run_time():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            # Load the stored time and ensure it is IST-aware
            return datetime.fromisoformat(json.load(f)["timestamp"])
    # Return current IST time if no file exists
    return datetime.now(IST).replace(microsecond=0)

def save_last_run_time():
    # Force the use of IST for the save
    with open(STATE_FILE, "w") as f:
        json.dump({"timestamp": datetime.now(IST).isoformat()}, f)


def send_telegram_message(chat_id, message):
    BOT_TOKEN = os.getenv("SST_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)


def format_job_message(job):
    return f"""
🚀 *New Job Posted*

💼 *Role:* {job['title']}

🏢 *Company:* {job['company']}

🌐 *Source:* {job['source']}

🔗 *Apply Here:*
{job['link']}
"""


def is_under_one_hour(card):
    """
    Checks if a job card contains strings that imply it is old.
    Returns False if the job is definitely old, True otherwise.
    """
    text = card.get_text().lower()
    
    # These are common indicators that a job is NOT within the last hour
    old_keywords = ['day', 'days', 'week', 'weeks', 'month', 'months', 'ago']
    
    for word in old_keywords:
        if word in text:
            # If we find '1 day ago' or '2 weeks ago', we return False (skip)
            return False
            
    return True