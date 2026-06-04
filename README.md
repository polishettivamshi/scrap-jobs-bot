# Smart Scale Tech Job Bot

This is a professional, automated job scraping bot designed to monitor the latest job postings from LinkedIn, Naukri, Remotive, WeWorkRemotely, and RemoteOK. It filters jobs by category, keyword, and target locations, then sends real-time notifications to dedicated Telegram channels.

---

## 🚀 Features

- **Multi-Platform Scraping**: Simultaneously fetches job listings from:
  - **LinkedIn** (Public RSS feed - no auth, reliable)
  - **Naukri** (Internal API with fallback parsing)
  - **Remotive** (Public REST API for remote jobs)
  - **WeWorkRemotely** (High-quality tech jobs)
  - **RemoteOK** (Developer and remote jobs)
- **Multi-Location Search**: Supports multiple locations per role: `Hyderabad`, `Bangalore`, `Chennai`, `Pune`, and `Remote`.
- **API Server & Background Triggers**: Features a Flask server (`app.py`) for triggering scrapes in the background (perfect for hosting on Render with third-party cron tools like `cron-job.org`).
- **Robust State Persistence**: Syncs `sent_jobs.json` and `last_run.json` with GitHub dynamically to preserve state between ephemeral runner runs, avoiding duplicate notifications.
- **Incremental State Saving**: Saves progress after searching each keyword to prevent losing state if the server process restarts.
- **Background Log Rotation**: Logs all activities to `logs/app.log` (10MB max size per file, keeping a max of 2 log files). Logs print to the console *only* when running on the production server (Render), keeping your local development terminal clean.
- **Safe Message Formatting**: Escapes Markdown characters automatically to prevent Telegram API formatting errors.

---

## 🛠️ Project Structure

```text
📁 scrap-jobs-bot
├── logs/
│   └── app.log           # Background logs (rotated at 10MB)
├── .env                  # Local environment variables
├── .gitignore            # Files excluded from git
├── app.py                # Flask server exposing trigger endpoints
├── main.py               # Main scraper orchestration logic
├── config.py             # Job categories, keyword, and location configs
├── fetchers.py           # Scraping functions for each job board
├── logger.py             # Rotated logging wrapper
├── services.py           # GitHub sync operations (push)
├── utils.py              # Telegram notifications & message formatting
└── requirements.txt      # Python dependencies
```

---

## ⚙️ Setup & Configuration

### 1. Requirements
* Python 3.10+
* Virtual Environment (optional, but recommended)

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
# Telegram Bot Credentials
SST_BOT_TOKEN="your_telegram_bot_token"

# Telegram Channel/Chat IDs
SST_BACKEND_JOBS_CHAT_ID="-100xxxxxxxxx"
SST_FRONTEND_JOBS_CHAT_ID="-100xxxxxxxxx"
SST_DEVOPS_JOBS_CHAT_ID="-100xxxxxxxxx"

# API Token for triggering scraper (Flask)
SCRAPER_API_KEY="your-super-secret-key"

# GitHub Auth for State Syncing
GITHUB_TOKEN="ghp_your_github_personal_access_token"
GITHUB_REPO="your_username/scrap-jobs-bot"
```

> **Note on GITHUB_TOKEN**: Ensure the token is generated as a **classic token** with the ✅ **`repo`** scope enabled so the bot can write and update the state files on GitHub.

---

## 💻 Running the App

### Running locally (Scraper Orchestrator)
To run the scraper orchestration process directly:
```bash
python main.py
```
*Local execution outputs log entries directly into `logs/app.log` instead of the console.*

### Running the API Web Server (Flask)
To start the server that listens for triggers:
```bash
python app.py
```

### API Endpoints
- **GET** `/ping` -> Returns `{"response": "pong"}` (used for health checks).
- **POST** `/trigger-scrape` -> Starts the scraper in a background thread. Requires the header `X-API-KEY` set to your `SCRAPER_API_KEY`.

---

## 🤖 Server Automation & Deployment

This project is fully ready to be deployed on **Render** (as a Web Service):
1. Connect your repository to Render.
2. Set the start command to: `gunicorn app:app` or `python app.py`.
3. Add all variables in the **Environment** settings page on Render.
4. Set up a scheduler on [cron-job.org](https://cron-job.org/) to hit your hosted Render API endpoint `/trigger-scrape` periodically (e.g., every 15–30 minutes) using `POST` with the header `X-API-KEY: your-key`.
