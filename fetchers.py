"""
fetchers.py — Job fetching via RSS feeds & public APIs.

WHY NOT HTML SCRAPING FOR NAUKRI/INDEED/LINKEDIN?
  All three render job cards via JavaScript. A plain `requests` call only gets
  the HTML shell — the actual job list is injected after page load by React/Vue,
  so BeautifulSoup will always find 0 cards or hit a 403/block.

STRATEGY PER SOURCE:
  LinkedIn       → Public RSS feed (no auth, server-side rendered)
  Indeed         → Official RSS feed with &sort=date&fromage=1
  Naukri         → Internal JSON API used by their own frontend
  Remotive       → Public REST API (remote jobs, no auth)
  WeWorkRemotely → RSS feed (high quality remote tech jobs)
  RemoteOK       → Public JSON API

JOB DICT SCHEMA (all fields):
  id          str      — unique dedup key
  title       str      — job title
  company     str      — company name
  link        str      — apply URL
  source      str      — platform name
  posted_at   datetime | None  — UTC-aware datetime
  location    str | None       — city / country / "Remote"
  job_type    str | None       — "Full-time" / "Remote" / "Contract" etc.
  experience  str | None       — e.g. "2-5 years"
  tags        list[str]        — skills / tech stack e.g. ["Python", "AWS"]

RECENCY FILTERING:
  Each fetcher returns a 'posted_at' datetime (UTC-aware).
  fetch_all_jobs() filters out anything older than MAX_AGE_HOURS.
"""

import requests
import feedparser
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from config import TARGET_LOCATIONS

IST = timezone(timedelta(hours=5, minutes=30))

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_AGE_HOURS = 24
RESULTS_PER_SOURCE = 25

# Sources that are remote-only — location filtering doesn't apply to them.
REMOTE_ONLY_SOURCES = {"Remotive", "WeWorkRemotely", "RemoteOK"}

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

# Helper to get the primary location for URL construction
def _get_api_location():
    # Grab the first location, or default to "India" if the list is empty
    return TARGET_LOCATIONS[0] if TARGET_LOCATIONS else "India"

def _now_utc():
    return datetime.now(timezone.utc)

def _is_recent(posted_at) -> bool:
    if posted_at is None:
        return True
    cutoff = _now_utc() - timedelta(hours=MAX_AGE_HOURS)
    try:
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        return posted_at >= cutoff
    except Exception:
        return True

def _parse_rfc2822(date_str) -> datetime | None:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).astimezone(timezone.utc)
    except Exception:
        return None

def _parse_struct_time(st) -> datetime | None:
    if st is None:
        return None
    try:
        return datetime(*st[:6], tzinfo=timezone.utc)
    except Exception:
        return None

def _safe_request(url: str, extra_headers: dict = None, timeout: int = 30, retries: int = 2):
    headers = {**BASE_HEADERS, **(extra_headers or {})}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            print(f"    [{resp.status_code}] {url[:90]}")
            return resp if resp.status_code == 200 else None
        except Exception as e:
            print(f"    [ERR attempt {attempt}/{retries}] {url[:90]} → {e}")
            if attempt < retries:
                time.sleep(3 * attempt)  # back off before retry
    return None

def _job(id, title, company, link, source, posted_at=None,
         location=None, job_type=None, experience=None, tags=None) -> dict:
    """Canonical job dict factory — ensures every key always exists."""
    return {
        "id":         id,
        "title":      title,
        "company":    company,
        "link":       link,
        "source":     source,
        "posted_at":  posted_at,
        "location":   location,
        "job_type":   job_type,
        "experience": experience,
        "tags":       tags or [],
    }


# ── Source 1: LinkedIn RSS ────────────────────────────────────────────────────

def fetch_linkedin_jobs(keyword: str) -> list[dict]:
    jobs = []
    seen_links = set()
    
    for location in TARGET_LOCATIONS:
        kw  = keyword.replace(" ", "%20")
        loc = location.replace(" ", "%20")
        url = (
            f"https://www.linkedin.com/jobs/search/rss"
            f"?keywords={kw}&location={loc}&f_TPR=r7200&sortBy=DD&count={RESULTS_PER_SOURCE}"
        )
        feed = feedparser.parse(url)

        if not feed.entries:
            # Fallback: guest jobs API
            url2 = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={kw}&location={loc}&f_TPR=r7200&sortBy=DD&start=0"
            )
            resp = _safe_request(url2)
            if resp:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for card in soup.select("li")[:RESULTS_PER_SOURCE]:
                    try:
                        a         = card.find("a", href=True)
                        title_el  = card.find(class_=lambda c: c and "title"   in c.lower()) or card.find("h3") or card.find("h2")
                        company_el= card.find(class_=lambda c: c and "company" in c.lower()) or card.find("h4")
                        location_el=card.find(class_=lambda c: c and "location" in c.lower())
                        if not (a and title_el):
                            continue
                        link = a["href"].split("?")[0]
                        if link in seen_links:
                            continue
                        seen_links.add(link)
                        jobs.append(_job(
                            id       = link,
                            title    = title_el.get_text(strip=True),
                            company  = company_el.get_text(strip=True) if company_el else "Unknown",
                            link     = link,
                            source   = "LinkedIn",
                            location = location_el.get_text(strip=True) if location_el else location,
                        ))
                    except Exception:
                        continue
        else:
            for entry in feed.entries[:RESULTS_PER_SOURCE]:
                try:
                    posted_at = (_parse_struct_time(entry.get("published_parsed"))
                                 or _parse_rfc2822(entry.get("published")))
                    link  = entry.get("link", "").split("?")[0]
                    if link in seen_links:
                        continue
                    title = entry.get("title", "").strip()
                    company = "Unknown"
                    if " at " in title:
                        title, company = title.rsplit(" at ", 1)
                        title, company = title.strip(), company.strip()

                    # Location is sometimes in the summary
                    job_location = None
                    summary  = entry.get("summary", "")
                    if summary:
                        from bs4 import BeautifulSoup
                        loc_soup = BeautifulSoup(summary, "html.parser")
                        text = loc_soup.get_text(" ", strip=True)
                        # LinkedIn summary often ends with "· Location"
                        if "·" in text:
                            parts = [p.strip() for p in text.split("·")]
                            job_location = parts[-1] if parts else None

                    seen_links.add(link)
                    jobs.append(_job(
                        id        = link,
                        title     = title,
                        company   = company,
                        link      = link,
                        source    = "LinkedIn",
                        posted_at = posted_at,
                        location  = job_location or location,
                    ))
                except Exception:
                    continue
        time.sleep(0.5)
    return jobs


# ── Source 2: Indeed RSS ──────────────────────────────────────────────────────

def fetch_indeed_jobs(keyword: str) -> list[dict]:
    kw = keyword.replace(" ", "+")

    # Indeed RSS is geo-biased. in.indeed.com covers India better.
    # Adding Accept header and Referer unblocks it on most server IPs.
    rss_headers = {
        **BASE_HEADERS,
        "Accept":  "application/rss+xml, application/xml, text/xml, */*",
        "Referer": "https://in.indeed.com/",
    }

    rss_urls = [
        f"https://in.indeed.com/rss?q={kw}&l={TARGET_LOCATIONS}&sort=date&fromage=1",   # India first
        f"https://www.indeed.com/rss?q={kw}&l={TARGET_LOCATIONS}&sort=date&fromage=1",  # US fallback
    ]
    jobs = []
    for url in rss_urls:
        # feedparser doesn't support custom headers natively — fetch raw then parse
        try:
            raw = requests.get(url, headers=rss_headers, timeout=20)
            if raw.status_code != 200:
                print(f"    [{raw.status_code}] Indeed RSS: {url[:70]}")
                continue
            feed = feedparser.parse(raw.text)
        except Exception as e:
            print(f"    [ERR] Indeed: {e}")
            continue

        print(f"    [200] Indeed RSS ({len(feed.entries)} entries): {url[:70]}")
        for entry in feed.entries[:RESULTS_PER_SOURCE]:
            try:
                posted_at = (_parse_struct_time(entry.get("published_parsed"))
                             or _parse_rfc2822(entry.get("published")))
                job_id = entry.get("id") or entry.get("link", "")
                title  = entry.get("title", "").strip()
                company= entry.get("author", "")

                location = None
                summary  = entry.get("summary", "")
                if summary:
                    from bs4 import BeautifulSoup
                    text = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
                    parts = [p.strip() for p in text.split(" - ") if p.strip()]
                    if len(parts) >= 2:
                        location = parts[1]

                jobs.append(_job(
                    id        = job_id,
                    title     = title,
                    company   = company or "Unknown",
                    link      = entry.get("link", ""),
                    source    = "Indeed",
                    posted_at = posted_at,
                    location  = location,
                ))
            except Exception:
                continue
        time.sleep(0.5)
    return jobs


def extract_naukri_v2_location(job: dict) -> str:
    locations = []
    city_val = (job.get("city") or "").lower()
    locality_list = job.get("locality") or []
    locality_city = ""
    if isinstance(locality_list, list) and len(locality_list) > 0:
        locality_city = (locality_list[0].get("city") or "").lower()
        
    is_remote = "remote" in city_val or "remote" in locality_city
    is_hybrid = "hybrid" in city_val or "hybrid" in locality_city
    
    cityfield = (job.get("cityfield") or "").lower()
    
    if "hyderabad" in cityfield:
        locations.append("Hyderabad")
    if "bengaluru" in cityfield or "bangalore" in cityfield:
        locations.append("Bangalore")
    if "chennai" in cityfield:
        locations.append("Chennai")
    if "pune" in cityfield:
        locations.append("Pune")
    if "remote" in cityfield or is_remote:
        locations.append("Remote")
        
    loc_str = ", ".join(locations) if locations else "Other"
    if is_hybrid and "Remote" not in locations:
        loc_str = f"Hybrid - {loc_str}"
    elif is_remote and "Remote" not in locations:
        loc_str = f"Remote - {loc_str}"
        
    return loc_str


# ── Source 3: Naukri Internal API ─────────────────────────────────────────────
# Naukri's JSON API returns rich metadata: experience, location, skills, salary.

def fetch_naukri_jobs(keyword: str) -> list[dict]:
    """
    Fetches jobs from Naukri's internal API.
    Uses v3 as primary, falls back to v2 if necessary.
    Loops over all TARGET_LOCATIONS.
    """
    jobs = []
    seen_ids = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "appid": "109",
        "systemid": "Naukri",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.naukri.com/",
    }
    
    kw_encoded = keyword.replace(" ", "%20")
    kw_slug = keyword.replace(" ", "-").lower()

    for location in TARGET_LOCATIONS:
        loc_encoded = location.replace(" ", "%20")
        
        # Naukri v3 API parameters
        url = (
            f"https://www.naukri.com/jobapi/v3/search"
            f"?noOfResults={RESULTS_PER_SOURCE}&urlType=search_by_keyword"
            f"&searchType=adv&keyword={kw_encoded}&location={loc_encoded}&pageNo=1"
            f"&k={kw_encoded}&seoKey={kw_slug}-jobs-in-{location.lower()}&src=jobsearchDesk&latLong="
        )
        
        try:
            with requests.Session() as s:
                resp = requests.get(url, headers=headers, timeout=15)
                
                # If v3 fails, try v2 fallback
                if resp.status_code != 200:
                    url_v2 = (
                        f"https://www.naukri.com/jobapi/v2/search"
                        f"?noOfResults={RESULTS_PER_SOURCE}&urlType=search_by_keyword"
                        f"&searchType=adv&keyword={kw_encoded}&location={loc_encoded}&pageNo=1&src=jobsearchDesk"
                    )
                    resp = requests.get(url_v2, headers=headers, timeout=15)
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except ValueError:
                        print(f"    [ERR] Naukri returned invalid JSON for '{keyword}' in '{location}'")
                        continue
                else:
                    print(f"    [!] Naukri returned status {resp.status_code} for '{keyword}' in '{location}'")
                    continue
        except Exception as e:
            print(f"    [ERR] Naukri connection error for '{location}': {e}")
            continue

        jobs_data = data.get("jobDetails")
        is_v2 = False
        if jobs_data is None:
            jobs_data = data.get("list", [])
            is_v2 = True

        for job in jobs_data:
            try:
                if is_v2:
                    title = job.get("post", "").strip()
                    company = job.get("companyName", "Unknown").strip()
                    link = job.get("urlStr") or job.get("jdURL") or f"https://www.naukri.com/job-listings-{job.get('jobId', '')}"
                    job_id = str(job.get("jobId", link))

                    if job_id in seen_ids:
                        continue

                    # parse addDate "2026-06-02 17:42:44.0"
                    add_date = job.get("addDate")
                    posted_at = None
                    if add_date:
                        try:
                            dt = datetime.strptime(add_date.split(".")[0], "%Y-%m-%d %H:%M:%S")
                            dt_ist = dt.replace(tzinfo=IST)
                            posted_at = dt_ist.astimezone(timezone.utc)
                        except Exception:
                            pass

                    # extract location
                    job_location = extract_naukri_v2_location(job)

                    # experience
                    exp_min = job.get("minExp")
                    exp_max = job.get("maxExp")
                    experience = f"{exp_min}–{exp_max} yrs" if (exp_min is not None and exp_max is not None) else None

                    # tags
                    skills = job.get("keywords", "") or ""
                    tags = [s.strip() for s in skills.split(",") if s.strip()][:6]
                else:
                    title = job.get("title", "").strip()
                    company = job.get("companyName", "Unknown").strip()
                    link = job.get("jdURL") or f"https://www.naukri.com/job-listings-{job.get('jobId', '')}"
                    job_id = str(job.get("jobId", link))

                    if job_id in seen_ids:
                        continue

                    # Convert epoch ms to datetime
                    created_ms = job.get("createdDate") or job.get("modifiedDate")
                    posted_at = (datetime.fromtimestamp(int(created_ms) / 1000, tz=timezone.utc)
                                 if created_ms else None)

                    # Extract location string
                    raw_loc = job.get("placeholders", [])
                    job_location = None
                    if isinstance(raw_loc, list):
                        loc_parts = [p.get("label", "") for p in raw_loc if p.get("type") == "location"]
                        job_location = ", ".join(loc_parts) if loc_parts else None
                    if not job_location:
                        job_location = job.get("location") or None

                    # Map experience
                    exp_min = job.get("minimumExperience")
                    exp_max = job.get("maximumExperience")
                    experience = f"{exp_min}–{exp_max} yrs" if (exp_min is not None and exp_max is not None) else None

                    # Extract skills/tags
                    skills = job.get("tagsAndSkills", "") or ""
                    tags = [s.strip() for s in skills.split(",") if s.strip()][:6]

                seen_ids.add(job_id)
                jobs.append(_job(
                    id=job_id,
                    title=title,
                    company=company,
                    link=link,
                    source="Naukri",
                    posted_at=posted_at,
                    location=job_location or location,
                    job_type=job.get("jobTypeLabel") or job.get("employmentType"),
                    experience=experience,
                    tags=tags
                ))
            except Exception:
                continue
        time.sleep(0.5)
        
    return jobs


# Remotive returns the same ~300 jobs regardless of the search param on free tier.
# We fetch the full list once per process and filter client-side per keyword.
_remotive_cache: list[dict] | None = None

def _get_remotive_all() -> list[dict]:
    global _remotive_cache
    if _remotive_cache is not None:
        return _remotive_cache
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs?limit=100",
            headers=BASE_HEADERS, timeout=20
        )
        if resp.status_code != 200:
            _remotive_cache = []
            return []
        _remotive_cache = resp.json().get("jobs", [])
        print(f"    [Remotive] Cached {len(_remotive_cache)} total jobs")
    except Exception as e:
        print(f"    [ERR] Remotive cache: {e}")
        _remotive_cache = []
    return _remotive_cache

def fetch_remotive_jobs(keyword: str) -> list[dict]:
    all_jobs = _get_remotive_all()
    kw_words = set(keyword.lower().split())

    jobs = []
    for job in all_jobs:
        title = (job.get("title") or "").lower()
        tags  = " ".join(job.get("tags") or []).lower()
        # Match against title OR tags
        if not any(w in title or w in tags for w in kw_words):
            continue
        try:
            posted_at = None
            if pub := job.get("publication_date"):
                try:
                    posted_at = datetime.fromisoformat(pub).astimezone(timezone.utc)
                except Exception:
                    pass
            jobs.append(_job(
                id        = str(job.get("id", "")),
                title     = job.get("title", "").strip(),
                company   = job.get("company_name", "Unknown").strip(),
                link      = job.get("url", ""),
                source    = "Remotive",
                posted_at = posted_at,
                location  = job.get("candidate_required_location") or "Remote",
                job_type  = job.get("job_type") or None,
                tags      = (job.get("tags") or [])[:6],
            ))
        except Exception:
            continue
    return jobs


# ── Source 5: We Work Remotely RSS ───────────────────────────────────────────

def fetch_wwr_jobs(keyword: str) -> list[dict]:
    url  = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    feed = feedparser.parse(url)

    kw_words = set(keyword.lower().split())
    jobs = []
    for entry in feed.entries[:60]:
        title = entry.get("title", "")
        if not any(w in title.lower() for w in kw_words):
            continue
        try:
            posted_at = _parse_struct_time(entry.get("published_parsed"))
            link      = entry.get("link", "")
            if ": " in title:
                company, job_title = title.split(": ", 1)
            else:
                company, job_title = "Unknown", title
            jobs.append(_job(
                id        = link,
                title     = job_title.strip(),
                company   = company.strip(),
                link      = link,
                source    = "WeWorkRemotely",
                posted_at = posted_at,
                location  = "Remote",
                job_type  = "Full-time Remote",
            ))
        except Exception:
            continue
    return jobs


# ── Source 6: RemoteOK JSON API ───────────────────────────────────────────────

def fetch_remoteok_jobs(keyword: str) -> list[dict]:
    url = "https://remoteok.com/api"
    try:
        resp = requests.get(
            url,
            headers={**BASE_HEADERS, "Accept": "application/json"},
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        print(f"    [ERR] RemoteOK: {e}")
        return []

    kw_words = set(keyword.lower().split())
    jobs = []
    for job in data[1:]:
        if not isinstance(job, dict):
            continue
        title = job.get("position", "")
        if not any(w in title.lower() for w in kw_words):
            continue
        try:
            posted_at = None
            if epoch := job.get("epoch"):
                posted_at = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            link = job.get("url") or f"https://remoteok.com/remote-jobs/{job.get('id', '')}"
            tags = [t for t in job.get("tags", []) if isinstance(t, str)][:6]
            jobs.append(_job(
                id        = str(job.get("id", link)),
                title     = title.strip(),
                company   = job.get("company", "Unknown").strip(),
                link      = link,
                source    = "RemoteOK",
                posted_at = posted_at,
                location  = "Remote",
                job_type  = "Remote",
                tags      = tags,
            ))
        except Exception:
            continue
        if len(jobs) >= 10:
            break
    return jobs


# ── Aggregator ────────────────────────────────────────────────────────────────

SOURCES = [
    ("LinkedIn",        fetch_linkedin_jobs),
    # ("Indeed",          fetch_indeed_jobs),
    ("Naukri",          fetch_naukri_jobs),
    ("Remotive",        fetch_remotive_jobs),
    ("WeWorkRemotely",  fetch_wwr_jobs),
    ("RemoteOK",        fetch_remoteok_jobs),
]


def _is_location_match(job: dict) -> bool:
    # 1. Bypass check for dedicated remote boards
    if job.get("source") in REMOTE_ONLY_SOURCES:
        return True
    
    job_loc = (job.get("location") or "").lower()
    
    # 2. Accept if the job explicitly mentions 'remote'
    if "remote" in job_loc:
        return True
        
    # 3. Accept if no location is provided (don't filter blindly)
    if not job_loc:
        return True
    
    # 4. Check if ANY city in our list is found in the job's location string
    # e.g., if job_loc is "Senior Dev, Bangalore", it will match "bangalore"
    check_locations = []
    for city in TARGET_LOCATIONS:
        city_lower = city.lower()
        check_locations.append(city_lower)
        if city_lower == "bangalore":
            check_locations.append("bengaluru")
        elif city_lower == "bengaluru":
            check_locations.append("bangalore")

    is_match = any(city in job_loc for city in check_locations)
    if not is_match and job.get("source") not in REMOTE_ONLY_SOURCES:
        print(f"[DEBUG] Dropped job in '{job_loc}' — not in target list")
    return is_match


def fetch_all_jobs(keyword: str) -> list[dict]:
    print(f"\n📡 [{keyword}] — {TARGET_LOCATIONS}")
    seen_ids = set()
    all_jobs = []

    for name, fetcher in SOURCES:
        try:
            results  = fetcher(keyword)
            recent   = [j for j in results if _is_recent(j.get("posted_at"))]
            local    = [j for j in recent  if _is_location_match(j)]
            new      = [j for j in local   if j["id"] not in seen_ids]
            for j in new:
                seen_ids.add(j["id"])
            all_jobs.extend(new)
            filtered_out = len(recent) - len(local)
            # Add this to fetch_all_jobs()
            print(f" ✅ {name}: {len(results)} fetched → {len(new)} new & recent (filtered: {len(results) - len(new)})")
        except Exception as e:
            print(f"  ❌ {name} error: {e}")
        time.sleep(0.5)

    return all_jobs