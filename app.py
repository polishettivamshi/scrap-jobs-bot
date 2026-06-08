import os
import threading
import subprocess
import sys
import base64
import requests
from datetime import datetime, timezone
from flask import Flask, jsonify, request, abort, render_template_string
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

CHANNELS = [
    {
        "title": "Smart Scale Tech Backend Jobs",
        "description": "Instant Backend Job Alerts for Python, Java, Node.js, goland, rust & Backend Engineer openings",
        "link": "https://t.me/SmartScaleTechBackendJobs",
        "experience": "All Levels (Entry to Lead)",
        "image": "/static/channel_images/backend.jpeg",
    },
    {
        "title": "Smart Scale Tech Frontend Jobs",
        "description": "Instant Frontend Job Alerts for React, Angular, Vue, JavaScript, TypeScript & UI roles.",
        "link": "https://t.me/SmartScaleTechFrontendJobs",
        "experience": "All Levels (Entry to Lead)",
        "image": "/static/channel_images/frontend.jpeg",
    },
    {
        "title": "Smart Scale Tech DevOps Jobs",
        "description": "Instant DevOps Job Alerts for AWS, Docker, Kubernetes, CI/CD, SRE, and cloud roles.",
        "link": "https://t.me/SmartScaleTechDevOpsJobs",
        "experience": "All Levels (Entry to Lead)",
        "image": "/static/channel_images/devops.jpeg",
    },
]


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


@app.route('/channels', methods=['GET'])
def channels():
    html = render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Telegram Channels</title>
            <style>
                :root {
                    color-scheme: dark;
                    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    background: #090b12;
                    color: #edf2f7;
                }
                * { box-sizing: border-box; }
                body { margin: 0; min-height: 100vh; background: radial-gradient(circle at top, rgba(96, 165, 250, 0.14), transparent 32%), linear-gradient(180deg, #111827 0%, #060a12 100%); }
                .page { width: min(1200px, calc(100% - 32px)); margin: 0 auto; padding: 40px 0 56px; }
                .heading { text-align: center; margin-bottom: 28px; }
                .heading h1 { margin: 0; font-size: clamp(2rem, 3vw, 3.2rem); letter-spacing: -0.04em; }
                .heading p { margin: 14px auto 0; max-width: 760px; color: #94a3b8; font-size: 1rem; line-height: 1.7; }
                .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }
                @media (max-width: 960px) { .grid { grid-template-columns: 1fr; } }
                .card {
                    background: rgba(15, 23, 42, 0.88);
                    border: 1px solid rgba(148, 163, 184, 0.12);
                    border-radius: 28px;
                    overflow: hidden;
                    box-shadow: 0 40px 80px rgba(15, 23, 42, 0.18);
                    transition: transform 180ms ease, box-shadow 180ms ease;
                }
                .card:hover { transform: translateY(-4px); box-shadow: 0 48px 100px rgba(15, 23, 42, 0.24); }
                .card img { width: 100%; height: 220px; object-fit: cover; display: block; }
                .card-body { padding: 24px; }
                .card-title { margin: 0 0 10px; font-size: 1.3rem; line-height: 1.2; }
                .meta { display: inline-flex; align-items: center; gap: 10px; margin-bottom: 18px; color: #94a3b8; font-size: 0.95rem; }
                .card-text { margin: 0 0 22px; color: #cbd5e1; line-height: 1.65; }
                .button { display: inline-flex; align-items: center; justify-content: center; gap: 10px; padding: 12px 18px; border-radius: 999px; background: #2563eb; color: #fff; text-decoration: none; font-weight: 600; transition: background 180ms ease; }
                .button:hover { background: #1d4ed8; }
                .badge { background: rgba(37, 99, 235, 0.14); color: #bfdbfe; padding: 6px 12px; border-radius: 999px; font-size: 0.82rem; }
            </style>
        </head>
        <body>
            <div class="page">
                <div class="heading">
                    <h1>Telegram channels</h1>
                    <p>Explore the current Smart Scale Tech job channels. Click any card to open the channel in Telegram.</p>
                </div>
                <div class="grid">
                    {% for channel in channels %}
                    <article class="card">
                        <img src="{{ channel.image }}" alt="{{ channel.title }} preview" />
                        <div class="card-body">
                            <div class="meta"><span class="badge">{{ channel.experience }}</span></div>
                            <h2 class="card-title">{{ channel.title }}</h2>
                            <p class="card-text">{{ channel.description }}</p>
                            <a class="button" href="{{ channel.link }}" target="_blank" rel="noreferrer noopener">View in Telegram</a>
                        </div>
                    </article>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        """,
        channels=CHANNELS,
    )
    return html


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