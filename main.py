import json
import os
import time
from config import JOB_CATEGORIES
from fetchers import fetch_all_jobs
from utils import send_telegram_message, format_job_message, get_last_run_time, save_last_run_time

SENT_FILE = "sent_jobs.json"
MAX_SENT_HISTORY = 5000  # Trim to avoid unbounded file growth


def load_sent_jobs() -> set:
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_sent_jobs(sent: set):
    ids = list(sent)
    # Keep only the most recent MAX_SENT_HISTORY to prevent file bloat
    if len(ids) > MAX_SENT_HISTORY:
        ids = ids[-MAX_SENT_HISTORY:]
    with open(SENT_FILE, "w") as f:
        json.dump(ids, f, indent=2)


def main():
    last_run = get_last_run_time()
    sent_jobs = load_sent_jobs()
    total_sent = 0

    print(f"\n🕒 Last run: {last_run}")
    print(f"📦 Already sent: {len(sent_jobs)} job IDs\n")

    for category, config in JOB_CATEGORIES.items():
        print(f"\n{'─'*50}")
        print(f"📂 Category: {category.upper()}")
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

        time.sleep(1)  # Brief pause between categories

    save_sent_jobs(sent_jobs)
    save_last_run_time()

    print(f"\n{'═'*50}")
    print(f"✅ Run complete. Total new jobs sent: {total_sent}")
    print(f"{'═'*50}\n")


if __name__ == "__main__":
    main()