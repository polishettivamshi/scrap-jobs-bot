import requests
from bs4 import BeautifulSoup
import time
from utils import is_under_one_hour

# ==========================================
# COMMON REQUEST HEADERS (Updated for Server)
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

session = requests.Session()
session.headers.update(HEADERS)

def safe_get(url):
    """Helper to request and debug status codes"""
    try:
        response = session.get(url, timeout=30)
        print(f"DEBUG: URL: {url[:50]}... | Status: {response.status_code}")
        if response.status_code != 200:
            print(f"DEBUG: Blocked! Response content snippet: {response.text[:200]}")
        return response
    except Exception as e:
        print(f"DEBUG: Connection Error: {e}")
        return None

# ==========================================
# FETCHERS
# ==========================================

def fetch_linkedin_jobs(keyword):
    jobs = []
    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&f_TPR=r3600&sortBy=DD"
    response = safe_get(url)
    if not response: return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("div", class_="base-card")
    print(f"DEBUG: LinkedIn found {len(cards)} potential cards.")
    
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
    jobs = []
    url = f"https://in.indeed.com/jobs?q={keyword.replace(' ', '+')}&sort=date&fromage=last"
    response = safe_get(url)
    if not response: return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("div", class_="job_seen_beacon")
    print(f"DEBUG: Indeed found {len(cards)} potential cards.")
    
    for card in cards[:25]:
        if not is_under_one_hour(card): continue
        try:
            title = card.find("h2").text.strip()
            company = card.find("span", {"data-testid": "company-name"}).text.strip()
            link = "https://in.indeed.com" + card.find("a")["href"]
            jobs.append({"id": link, "title": title, "company": company, "link": link, "source": "Indeed"})
        except: continue
    return jobs

def fetch_naukri_jobs(keyword):
    jobs = []
    url = f"https://www.naukri.com/{keyword.replace(' ', '-')}-jobs-?sort=date"
    response = safe_get(url)
    if not response: return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("article", class_="jobTuple")
    print(f"DEBUG: Naukri found {len(cards)} potential cards.")
    
    for card in cards[:25]:
        if not is_under_one_hour(card): continue
        try:
            title_tag = card.find("a", class_="title")
            company_tag = card.find("a", class_="comp-name")
            jobs.append({"id": title_tag["href"], "title": title_tag.text.strip(), "company": company_tag.text.strip(), "link": title_tag["href"], "source": "Naukri"})
        except: continue
    return jobs

def fetch_all_jobs(keyword):
    print(f"\n🚀 Fetching latest jobs for: {keyword}")
    all_jobs = []
    all_jobs.extend(fetch_linkedin_jobs(keyword))
    time.sleep(3) # Anti-bot pause
    all_jobs.extend(fetch_indeed_jobs(keyword))
    time.sleep(3) # Anti-bot pause
    all_jobs.extend(fetch_naukri_jobs(keyword))
    return all_jobs