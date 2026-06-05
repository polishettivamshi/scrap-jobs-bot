import json
import os
import time
import requests
import base64
from datetime import datetime, timezone
from config import JOB_CATEGORIES
from fetchers import fetch_all_jobs
from utils import send_telegram_message, format_job_message, get_last_run_time, save_last_run_time, STATE_FILE
from dotenv import load_dotenv
from services import push_to_github
from logger import log_print as print

load_dotenv()


SENT_FILE = "sent_jobs.json"
MAX_SENT_HISTORY = 5000  # Trim to avoid unbounded file growth

# Hard cap: exit cleanly before Render kills the process at ~30 min.
# Render free tier sends SIGKILL after 30 min with no warning — we exit at 25 min
# so at least the last category's progress is saved before being cut off.
RUN_TIMEOUT_SECONDS = 25 * 60   # 25 minutes


def load_sent_jobs() -> set:
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                data = json.load(f)
                return set(data)
        except json.JSONDecodeError:
            print(f"⚠️ Warning: {SENT_FILE} was empty or invalid. Starting fresh.")
            return set() # Return empty set if file is corrupt
    return set()


def save_sent_jobs(sent: set):
    ids = list(sent)
    if len(ids) > MAX_SENT_HISTORY:
        ids = ids[-MAX_SENT_HISTORY:]
    
    # Write to local ephemeral disk
    with open(SENT_FILE, "w") as f:
        json.dump(ids, f, indent=2)
    # Sync to GitHub
    push_to_github(SENT_FILE)


def pull_from_github(file_path):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # GitHub returns base64 encoded content
        content = base64.b64decode(response.json()['content']).decode()
        with open(file_path, "w") as f:
            f.write(content)
        print(f"✅ Successfully pulled {file_path} from GitHub.")
    else:
        print(f"⚠️ Could not pull {file_path} from GitHub (Status: {response.status_code})")


def main():
    run_start = time.monotonic()

    # ── Startup diagnostics (helps debug env issues on Render) ────────────────
    print("\n" + "=" * 60)
    print("[STARTUP] ENV VAR CHECK")
    print("=" * 60)
    env_vars = [
        "SST_BOT_TOKEN", "SST_BACKEND_JOBS_CHAT_ID",
        "SST_FRONTEND_JOBS_CHAT_ID", "SST_DEVOPS_JOBS_CHAT_ID",
        "GITHUB_TOKEN", "GITHUB_REPO", "SCRAPER_API_KEY",
    ]
    for var in env_vars:
        val = os.getenv(var)
        if val:
            print(f"  [OK]     {var} = ***{val[-4:]}")
        else:
            print(f"  [MISSING] {var} = NOT SET")
    print("=" * 60 + "\n")

    pull_from_github(SENT_FILE)
    pull_from_github(STATE_FILE)
    last_run = get_last_run_time()
    sent_jobs = load_sent_jobs()
    total_sent = 0

    print(f"\n🕒 Last run: {last_run}")
    print(f"📦 Already sent: {len(sent_jobs)} job IDs\n")

    for category, config in JOB_CATEGORIES.items():
        # Check timeout before starting each category (not mid-category)
        elapsed = time.monotonic() - run_start
        if elapsed > RUN_TIMEOUT_SECONDS:
            print(f"\n[TIMEOUT] Run limit reached ({elapsed/60:.1f} min). "
                  f"Skipping remaining categories to avoid Render kill.")
            break

        print(f"\n{'─'*50}")
        print(f"📂 Category: {category.upper()} | Elapsed: {elapsed/60:.1f} min")
        print(f"{'─'*50}")

        for keyword in config["keywords"]:
            jobs = fetch_all_jobs(keyword)
            new_count = 0

            for job in jobs:
                if job["id"] not in sent_jobs:
                    send_telegram_message(config["chat_id"], format_job_message(job))
                    sent_jobs.add(job["id"])
                    new_count += 1
                    total_sent += 1
                    time.sleep(1.5)  # Telegram allows ~20 msg/min to same chat; 1.5s ≈ safe

            print(f"  📨 Sent {new_count} new jobs for '{keyword}'")

            # Save state incrementally to prevent losing progress if the process is terminated/restarted
            if new_count > 0:
                save_sent_jobs(sent_jobs)
                save_last_run_time()


        time.sleep(1)  # Brief pause between categories

    save_sent_jobs(sent_jobs)
    save_last_run_time()

    print(f"\n{'═'*50}")
    print(f"✅ Run complete. Total new jobs sent: {total_sent}")
    print(f"{'═'*50}\n")


if __name__ == "__main__":
    main()