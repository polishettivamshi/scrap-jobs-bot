import os
import threading
import subprocess
import sys
import base64
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request, abort
from dotenv import load_dotenv
from logger import log_print as print, MEMORY_LOG_BUFFER

load_dotenv()

app = Flask(__name__)

# Use a lock so that if a ping arrives while a scrape is in progress,
# the app won't start a second, conflicting process.
scrape_lock = threading.Lock()

# Ensure you have this set in your environment variables on Render
SECRET_KEY = os.getenv("SCRAPER_API_KEY", "your-super-secret-key")

LOG_PATH = os.path.join("logs", "app.log")
GITHUB_LOG_PATH = "logs/app.log"   # path as stored in the GitHub repo


# ── GitHub log helpers ────────────────────────────────────────────────────────

def _github_headers():
    token = os.getenv("GITHUB_TOKEN")
    return {"Authorization": f"token {token}"} if token else {}

def _github_log_url():
    # Log file lives in the *state* repository
    repo = os.getenv("GITHUB_STATE_REPO")
    return f"https://api.github.com/repos/{repo}/contents/{GITHUB_LOG_PATH}"


def pull_log_from_github():
    """
    On startup, pull the last-known log from GitHub into MEMORY_LOG_BUFFER
    so logs survive Render restarts.
    """
    try:
        resp = requests.get(_github_log_url(), headers=_github_headers(), timeout=10)
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()["content"]).decode("utf-8", errors="replace")
            for line in content.splitlines():
                MEMORY_LOG_BUFFER.append(line)
            print(f"[startup] Pulled {len(MEMORY_LOG_BUFFER)} log lines from GitHub.")
        else:
            print(f"[startup] No previous log on GitHub (status {resp.status_code}), starting fresh.")
    except Exception as e:
        print(f"[startup] Could not pull log from GitHub: {e}")


def push_log_to_github():
    """
    After each scrape run, push the in-memory buffer to GitHub
    so the next server instance can restore it on startup.
    """
    try:
        content_str = "\n".join(MEMORY_LOG_BUFFER) + "\n"
        encoded = base64.b64encode(content_str.encode("utf-8")).decode()

        # Get current SHA if the file already exists
        get_resp = requests.get(_github_log_url(), headers=_github_headers(), timeout=10)
        payload = {
            "message": "chore: update logs/app.log [skip ci]",
            "content": encoded,
        }
        if get_resp.status_code == 200:
            payload["sha"] = get_resp.json().get("sha")

        put_resp = requests.put(_github_log_url(), headers=_github_headers(), json=payload, timeout=15)
        if put_resp.status_code in (200, 201):
            print(f"[github] Log pushed successfully ({len(MEMORY_LOG_BUFFER)} lines).")
        else:
            print(f"[github] Log push failed: {put_resp.status_code} — {put_resp.text[:120]}")
    except Exception as e:
        print(f"[github] Could not push log to GitHub: {e}")


# ── Pull logs from GitHub on startup ─────────────────────────────────────────
pull_log_from_github()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"response": "pong"})


@app.route('/status', methods=['GET'])
def status():
    """Quick health check — shows whether the scraper is currently running."""
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)

    log_info = {
        "memory_buffer_lines": len(MEMORY_LOG_BUFFER),
        "file_exists": False,
        "size_bytes": 0,
        "last_modified": None,
    }
    if os.path.exists(LOG_PATH):
        stat = os.stat(LOG_PATH)
        log_info["file_exists"] = True
        log_info["size_bytes"] = stat.st_size
        log_info["last_modified"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    return jsonify({
        "scraper_running": scrape_lock.locked(),
        "log": log_info,
    })


@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Returns the last N lines of logs as plain text.
    Source priority: in-memory buffer → file fallback.
    Secured with the X-API-KEY header.
    Optional query param: ?lines=2000 (default 2000, max 3000)
    """
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)

    try:
        n = min(int(request.args.get("lines", 2000)), 3000)
    except (ValueError, TypeError):
        n = 2000

    # Primary: in-memory buffer (always populated via subprocess stdout capture)
    if MEMORY_LOG_BUFFER:
        lines = list(MEMORY_LOG_BUFFER)[-n:]
        tail = "\n".join(lines) + "\n"
        return tail, 200, {"Content-Type": "text/plain; charset=utf-8"}

    # Fallback: disk file
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                file_lines = f.readlines()
            tail = "".join(file_lines[-n:])
            return tail, 200, {"Content-Type": "text/plain; charset=utf-8"}
        except Exception as e:
            return f"Error reading log file: {e}", 500

    return (
        "No logs available. The server just restarted and no previous log was found on GitHub.\n"
        "Trigger a scrape run to generate logs.",
        404,
    )


@app.route('/trigger-scrape', methods=['POST'])
def trigger_scrape():
    # 1. Simple Security: Only allow requests with your secret key
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)

    # 2. Check if already running
    if scrape_lock.locked():
        return jsonify({"status": "error", "message": "Scraper already running"}), 429

    # 3. Start the job in a background thread using a subprocess.
    #    We capture stdout line-by-line so all log output from main.py
    #    flows into MEMORY_LOG_BUFFER in this (Flask) process.
    def run_job():
        with scrape_lock:
            try:
                timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                MEMORY_LOG_BUFFER.append(f"{'='*60}")
                MEMORY_LOG_BUFFER.append(f"[RUN START] {timestamp}")
                MEMORY_LOG_BUFFER.append(f"{'='*60}")

                proc = subprocess.Popen(
                    [sys.executable, "-u", "main.py"],   # -u = unbuffered stdout
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,             # merge stderr into stdout
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                # Stream each line into the buffer AND print to Render's dashboard
                for line in proc.stdout:
                    line = line.rstrip("\n").rstrip("\r")
                    if line:
                        MEMORY_LOG_BUFFER.append(line)
                        sys.stdout.write(line + "\n")
                        sys.stdout.flush()

                proc.wait()
                exit_code = proc.returncode

                MEMORY_LOG_BUFFER.append(f"{'='*60}")
                MEMORY_LOG_BUFFER.append(f"[RUN END] exit code: {exit_code}")
                MEMORY_LOG_BUFFER.append(f"{'='*60}")

                # Push accumulated logs to GitHub for persistence across restarts
                push_log_to_github()

            except Exception as e:
                MEMORY_LOG_BUFFER.append(f"[ERROR] Failed to run scraper subprocess: {e}")
                sys.stdout.write(f"[ERROR] Failed to run scraper subprocess: {e}\n")
                sys.stdout.flush()

    threading.Thread(target=run_job, daemon=True).start()

    return jsonify({"status": "success", "message": "Scraper started in background"}), 202


if __name__ == '__main__':
    # Render provides a PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)