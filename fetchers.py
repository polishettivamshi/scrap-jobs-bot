import requests
from bs4 import BeautifulSoup
import time
from utils import is_under_one_hour

# ==========================================
# COMMON REQUEST HEADERS
# ==========================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Create a session to persist headers and cookies across requests
session = requests.Session()
session.headers.update(HEADERS)

# ==========================================
# LINKEDIN JOB FETCHER
# ==========================================

def fetch_linkedin_jobs(keyword):
    jobs = []
    try:
        print(f"🔍 Fetching LinkedIn jobs for: {keyword}")
        # Added f_TPR=r3600 to fetch jobs posted in the last hour
        # Keep this. It is the most reliable "last hour" filter available.
        url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&f_TPR=r3600&sortBy=DD"
        response = session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")

        for card in cards[:25]:
            if not is_under_one_hour(card):
                continue  # Skip this job if it looks like it's from 'days ago
            try:
                title = card.find("h3").text.strip()
                company = card.find("h4").text.strip()
                link = card.find("a")["href"]
                jobs.append({
                    "id": link, "title": title, "company": company,
                    "link": link, "source": "LinkedIn"
                })
            except: continue
    except Exception as e:
        print(f"❌ LinkedIn Error: {e}")
    return jobs

# ==========================================
# INDEED JOB FETCHER
# ==========================================

def fetch_indeed_jobs(keyword):
    jobs = []
    try:
        print(f"🔍 Fetching Indeed jobs for: {keyword}")
        # sortBy=date ensures we see the latest postings
        # 'fromage=last' restricts results to the last 24 hours (Indeed's tightest standard filter).
        url = f"https://in.indeed.com/jobs?q={keyword.replace(' ', '+')}&sort=date&fromage=last"
        response = session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="job_seen_beacon")

        for card in cards[:25]:
            if not is_under_one_hour(card):
                continue  # Skip this job if it looks like it's from 'days ago
            try:
                title = card.find("h2").text.strip()
                company = card.find("span", {"data-testid": "company-name"}).text.strip()
                link = "https://in.indeed.com" + card.find("a")["href"]
                jobs.append({
                    "id": link, "title": title, "company": company,
                    "link": link, "source": "Indeed"
                })
            except: continue
    except Exception as e:
        print(f"❌ Indeed Error: {e}")
    return jobs

# ==========================================
# NAUKRI JOB FETCHER
# ==========================================

def fetch_naukri_jobs(keyword):
    jobs = []
    try:
        print(f"🔍 Fetching Naukri jobs for: {keyword}")
        keyword_slug = keyword.replace(" ", "-")
        # Naukri often relies on local cookies. If it's returning old jobs, 
        # clear your session and try this structure:
        url = f"https://www.naukri.com/{keyword_slug}-jobs?sort=date&k={keyword.replace(' ', '%20')}"
        response = session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("article", class_="jobTuple")

        for card in cards[:25]:
            if not is_under_one_hour(card):
                continue  # Skip this job if it looks like it's from 'days ago
            try:
                title_tag = card.find("a", class_="title")
                company_tag = card.find("a", class_="comp-name")
                jobs.append({
                    "id": title_tag["href"],
                    "title": title_tag.text.strip(),
                    "company": company_tag.text.strip(),
                    "link": title_tag["href"],
                    "source": "Naukri"
                })
            except: continue
    except Exception as e:
        print(f"❌ Naukri Error: {e}")
    return jobs

# ==========================================
# FETCH ALL PLATFORM JOBS
# ==========================================

def fetch_all_jobs(keyword):
    print(f"\n🚀 Fetching latest jobs for: {keyword}")
    all_jobs = []
    all_jobs.extend(fetch_linkedin_jobs(keyword))
    all_jobs.extend(fetch_indeed_jobs(keyword))
    all_jobs.extend(fetch_naukri_jobs(keyword))
    return all_jobs