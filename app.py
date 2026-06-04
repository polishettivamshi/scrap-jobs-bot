import os
import threading
import subprocess
import sys
from flask import Flask, jsonify, request, abort
from dotenv import load_dotenv
from logger import log_print as print

load_dotenv()

app = Flask(__name__)

# Use a lock so that if a ping arrives while a scrape is in progress,
# the app won't start a second, conflicting process.
scrape_lock = threading.Lock()

# Ensure you have this set in your environment variables on Render
SECRET_KEY = os.getenv("SCRAPER_API_KEY", "your-super-secret-key")

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"response": "pong"})


@app.route('/status', methods=['GET'])
def status():
    """Quick health check — shows whether the scraper is currently running."""
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)
    log_path = os.path.join("logs", "app.log")
    log_info = {}
    if os.path.exists(log_path):
        stat = os.stat(log_path)
        from datetime import datetime, timezone
        log_info = {
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }
    return jsonify({
        "scraper_running": scrape_lock.locked(),
        "log": log_info,
    })


@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Returns the last N lines of logs/app.log as plain text.
    Secured with the X-API-KEY header.
    Optional query param: ?lines=2000 (default 2000, max 3000)
    """
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)

    try:
        n = min(int(request.args.get("lines", 2000)), 3000)
    except (ValueError, TypeError):
        n = 2000

    log_path = os.path.join("logs", "app.log")
    if not os.path.exists(log_path):
        return "Log file not found. The scraper may not have run yet.", 404

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tail = "".join(lines[-n:])
        return tail, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        return f"Error reading log file: {e}", 500

@app.route('/trigger-scrape', methods=['POST'])
def trigger_scrape():
    # 1. Simple Security: Only allow requests with your secret key
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)
    
    # 2. Check if already running
    if scrape_lock.locked():
        return jsonify({"status": "error", "message": "Scraper already running"}), 429
    
    # 3. Start the job in a background thread using a subprocess
    # We do this so the HTTP response returns immediately to cron-job.org
    def run_job():
        with scrape_lock:
            try:
                print("Starting scraper subprocess...")
                result = subprocess.run(
                    [sys.executable, "main.py"],
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
                print(f"Scraper subprocess finished with exit code {result.returncode}")
            except Exception as e:
                print(f"Failed to run scraper subprocess: {e}")

    threading.Thread(target=run_job).start()
    
    return jsonify({"status": "success", "message": "Scraper started in background"}), 202

if __name__ == '__main__':
    # Render provides a PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)