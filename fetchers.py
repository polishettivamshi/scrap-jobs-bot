import requests
from bs4 import BeautifulSoup
import time
from utils import is_under_one_hour

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
}

session = requests.Session()
session.headers.update(HEADERS)

def safe_get(url):
    try:
        # Added a longer timeout for server-side response
        response = session.get(url, timeout=45)
        return response if response.status_code == 200 else None
    except Exception as e:
        print(f"DEBUG: Error: {e}")
        return None

def fetch_linkedin_jobs(keyword):
    # LinkedIn frequently rotates class names. 'base-card' is good, 
    # but 'job-card-container' is a frequent alternative.
    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&f_TPR=r3600&sortBy=DD"
    resp = safe_get(url)
    if not resp: return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    # Using a combined selector to catch cards
    cards = soup.select(".base-card, .job-card-container")
    
    jobs = []
    for card in cards[:25]:
        if not is_under_one_hour(card): continue
        try:
            title = card.find("h3").text.strip()
            company = card.find("h4").text.strip()
            link = card.find("a")["href"]
            jobs.append({"id": link, "title": title, "company": company, "link": link, "source": "LinkedIn"})
        except: continue
    return jobs

def fetch_indeed_jobs(keyword):
    # INDEED NOTE: Indeed is very hard to scrape via requests on servers.
    # If this continues to return 403, it's best to remove it to save runtime.
    return [] 

def fetch_naukri_jobs(keyword):
    # Naukri requires very specific headers. 
    # Adding a 'DNT' (Do Not Track) header can sometimes bypass basic bot checks.
    session.headers.update({"DNT": "1"})
    url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-?sort=date"
    resp = safe_get(url)
    if not resp: return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    # Naukri is highly dynamic. If this returns 0, the site is likely 
    # hiding the job list behind a script we cannot reach with 'requests'.
    cards = soup.select('article, .srp-jobtuple-wrapper')
    
    jobs = []
    for card in cards[:25]:
        try:
            # Flexible finding for Naukri
            title_tag = card.select_one('a.title, .title')
            company_tag = card.select_one('a.comp-name, .comp-name')
            if title_tag and company_tag:
                jobs.append({
                    "id": title_tag["href"],
                    "title": title_tag.text.strip(),
                    "company": company_tag.text.strip(),
                    "link": title_tag["href"],
                    "source": "Naukri"
                })
        except: continue
    return jobs

def fetch_all_jobs(keyword):
    all_jobs = []
    all_jobs.extend(fetch_linkedin_jobs(keyword))
    time.sleep(2)
    # Indeed is skipped due to 403 blocks
    all_jobs.extend(fetch_naukri_jobs(keyword))
    return all_jobs