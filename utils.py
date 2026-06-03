import requests
import os
import json
import time
from datetime import datetime, timezone, timedelta
from main import push_to_github

IST        = timezone(timedelta(hours=5, minutes=30))
STATE_FILE = "last_run.json"

# Source → emoji badge
SOURCE_BADGES = {
    "LinkedIn":       "🔵 LinkedIn",
    "Indeed":         "🟣 Indeed",
    "Naukri":         "🟠 Naukri",
    "Remotive":       "🟢 Remotive",
    "WeWorkRemotely": "🔴 WeWorkRemotely",
    "RemoteOK":       "⚫ RemoteOK",
}


# ── State helpers ─────────────────────────────────────────────────────────────

def get_last_run_time() -> datetime:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return datetime.fromisoformat(json.load(f)["timestamp"])
    return datetime.now(IST).replace(microsecond=0)


def save_last_run_time():
    # Write to local ephemeral disk
    with open(STATE_FILE, "w") as f:
        json.dump({"timestamp": datetime.now(IST).isoformat()}, f)
    # Sync to GitHub
    push_to_github(STATE_FILE)


# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram_message(chat_id: str, message: str, _retries: int = 3):
    """
    Send a message and respect Telegram's retry_after on 429 rate limits.
    Retries up to _retries times before giving up on the message.
    """
    BOT_TOKEN = os.getenv("SST_BOT_TOKEN")
    url       = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload   = {
        "chat_id":                  chat_id,
        "text":                     message,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True,
    }
    for attempt in range(1, _retries + 1):
        try:
            resp = requests.post(url, data=payload, timeout=15)
            if resp.status_code == 200:
                return
            if resp.status_code == 429:
                wait = resp.json().get("parameters", {}).get("retry_after", 15)
                print(f"  [Telegram] Rate limited — waiting {wait}s (attempt {attempt}/{_retries})")
                time.sleep(wait + 1)
                continue
            print(f"  [Telegram] ⚠️  {resp.status_code} — {resp.text[:120]}")
            return
        except Exception as e:
            print(f"  [Telegram] Error: {e}")
            return


# ── Message formatter ─────────────────────────────────────────────────────────

def format_job_message(job: dict) -> str:
    source_badge = SOURCE_BADGES.get(job["source"], f"🌐 {job['source']}")

    # Optional fields — only rendered if the source provides them
    location_line   = f"\n📍 *Location:* {job['location']}"       if job.get("location")   else ""
    type_line       = f"\n⏱ *Type:* {job['job_type']}"            if job.get("job_type")   else ""
    exp_line        = f"\n🎯 *Experience:* {job['experience']}"    if job.get("experience") else ""

    posted_line = ""
    if job.get("posted_at"):
        diff_mins = int((_now_utc() - job["posted_at"].astimezone(timezone.utc)).total_seconds() / 60)
        if diff_mins < 60:
            time_str = f"{diff_mins}m ago"
        elif diff_mins < 120:
            time_str = f"1h {diff_mins % 60}m ago"
        else:
            time_str = job["posted_at"].astimezone(IST).strftime("%d %b, %I:%M %p IST")
        posted_line = f"\n🕐 *Posted:* {time_str}"

    tags_line = ""
    if job.get("tags"):
        tags_line = "\n🏷 " + "  ".join(f"`{t}`" for t in job["tags"][:6])

    return (
        f"🚀 *New Job Posted*\n"
        f"\n"
        f"💼 *Role:* {job['title']}\n"
        f"🏢 *Company:* {job['company']}"
        f"{location_line}"
        f"{type_line}"
        f"{exp_line}"
        f"{posted_line}"
        f"{tags_line}\n"
        f"\n"
        f"🌐 *Source:* {source_badge}\n"
        f"\n"
        f"🔗 *Apply Here:*\n"
        f"{job['link']}"
    )


def _now_utc():
    return datetime.now(timezone.utc)