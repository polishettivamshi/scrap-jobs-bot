import os
import threading
from flask import Flask, jsonify, request, abort
from main import main as run_scraper

app = Flask(__name__)

# Use a lock so that if a ping arrives while a scrape is in progress,
# the app won't start a second, conflicting process.
scrape_lock = threading.Lock()

# Ensure you have this set in your environment variables on Render
SECRET_KEY = os.getenv("SCRAPER_API_KEY", "your-super-secret-key")

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"response": "pong"})

@app.route('/trigger-scrape', methods=['POST'])
def trigger_scrape():
    # 1. Simple Security: Only allow requests with your secret key
    if request.headers.get("X-API-KEY") != SECRET_KEY:
        abort(403)
    
    # 2. Check if already running
    if scrape_lock.locked():
        return jsonify({"status": "error", "message": "Scraper already running"}), 429
    
    # 3. Start the job in a background thread
    # We do this so the HTTP response returns immediately to cron-job.org
    def run_job():
        with scrape_lock:
            try:
                run_scraper()
            except Exception as e:
                print(f"Scraper crashed: {e}")

    threading.Thread(target=run_job).start()
    
    return jsonify({"status": "success", "message": "Scraper started in background"}), 202

if __name__ == '__main__':
    # Render provides a PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)