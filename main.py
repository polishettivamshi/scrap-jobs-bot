import json
import os
import time
from config import JOB_CATEGORIES
from fetchers import fetch_all_jobs
from utils import send_telegram_message, format_job_message, get_last_run_time, save_last_run_time

SENT_FILE = "sent_jobs.json"

def main():
    # 1. Get the time of the last successful run
    last_run = get_last_run_time()
    sent_jobs = json.load(open(SENT_FILE, "r")) if os.path.exists(SENT_FILE) else []

    print(f"🕒 Last run was: {last_run}")

    for category, config in JOB_CATEGORIES.items():
        for keyword in config["keywords"]:
            # Fetch current jobs
            jobs = fetch_all_jobs(keyword)
            
            for job in jobs:
                # 2. Deduplication check
                if job["id"] not in sent_jobs:
                    # 3. Post to Telegram
                    send_telegram_message(config["chat_id"], format_job_message(job))
                    sent_jobs.append(job["id"])
                    time.sleep(2)

    # 4. Save state
    with open(SENT_FILE, "w") as f:
        json.dump(sent_jobs, f)
    
    save_last_run_time()
    print("✅ Run complete. Updated timestamp.")

if __name__ == "__main__":
    main()