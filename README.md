# Smart Scale Tech Job Bot

This is a professional, automated job scraping bot designed to monitor the latest job postings from LinkedIn, Indeed, and Naukri. It filters jobs by category and keyword, then sends real-time notifications to dedicated Telegram channels.

## 🚀 Features
- **Multi-Platform Scraping**: Simultaneously fetches job listings from LinkedIn, Indeed, and Naukri.
- **Category-Based Routing**: Automatically routes jobs to specific Telegram channels based on job roles (Backend, Frontend, DevOps, etc.).
- **Smart Deduplication**: Ensures no duplicate jobs are sent by tracking processed job IDs in `sent_jobs.json`.
- **Time-Aware Filtering**: Designed to run via Cron/GitHub Actions to fetch the latest postings.
- **Modular Design**: Separated concerns for fetching, utility functions, and configuration for easy maintenance.

## 🛠️ Project Structure
```text
📁 scrap-jobs-bot
├── .env                # Environment variables (Tokens, Chat IDs)
├── .gitignore          # Files excluded from Git
├── main.py             # Main entry point and orchestration logic
├── config.py           # Job categories and keyword configurations
├── fetchers.py         # Scraping functions for individual platforms
├── utils.py            # Telegram sender and message formatting
├── requirements.txt    # Python dependencies
├── sent_jobs.json      # Persistent storage for deduplication
└── last_run.json       # Tracks the last execution time

```

## ⚙️ Setup & Configuration

### 1. Requirements

* Python 3.10+
* `requests`, `beautifulsoup4`, `python-dotenv`

### 2. Installation

```bash
pip install -r requirements.txt

```

### 3. Environment Variables (`.env`)

Create a `.env` file in the root directory and add your credentials:

```env
SST_BOT_TOKEN=your_telegram_bot_token
SST_BACKEND_JOBS_CHAT_ID=your_backend_chat_id
SST_FRONTEND_JOBS_CHAT_ID=your_frontend_chat_id
SST_DEVOPS_JOBS_CHAT_ID=your_devops_chat_id

```

## 🤖 Automation (GitHub Actions)

This project is configured to run automatically every 15 minutes using GitHub Actions.

* The workflow is defined in `.github/workflows/scraper.yml`.
* It handles the automated fetching, state updates, and Git commits to keep `sent_jobs.json` and `last_run.json` synchronized.

## 📝 License

This project is for educational and personal use only. Please respect the `robots.txt` and Terms of Service of the platforms being scraped.
"""

with open("README.md", "w") as f:
f.write(readme_content)
