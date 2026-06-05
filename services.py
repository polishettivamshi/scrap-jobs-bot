import os
import requests
import base64
from dotenv import load_dotenv
from logger import log_print as print

load_dotenv()


def push_to_github(file_path):
    # The token is shared for both repos
    # Build the correct URL for the target file, using the state repo for state files
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_STATE_REPO") if file_path in {"sent_jobs.json", "last_run.json", "logs/app.log"} else os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_STATE_BRANCH") if file_path in {"sent_jobs.json", "last_run.json", "logs/app.log"} else None
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    if branch:
        url += f"?ref={branch}"


    headers = {"Authorization": f"token {token}"}

    # Read local file content
    try:
        with open(file_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  ⚠️ push_to_github: local file '{file_path}' not found, skipping.")
        return

    encoded = base64.b64encode(content.encode()).decode()

    # Try to get existing file SHA (needed for updates)
    get_resp = requests.get(url, headers=headers)

    payload = {
        "message": f"chore: update {file_path} [skip ci]",
        "content": encoded,
    }

    if get_resp.status_code == 200:
        # File exists — include SHA so GitHub accepts the update
        payload["sha"] = get_resp.json().get("sha")
    elif get_resp.status_code == 404:
        # File doesn't exist yet — create it (no SHA needed)
        pass
    else:
        print(f"  ⚠️ push_to_github: unexpected GET status {get_resp.status_code} for '{file_path}'")
        return

    put_resp = requests.put(url, headers=headers, json=payload)
    if put_resp.status_code in (200, 201):
        print(f"  ✅ Pushed '{file_path}' to GitHub.")
    else:
        print(f"  ❌ Failed to push '{file_path}' to GitHub: {put_resp.status_code} — {put_resp.text[:120]}")