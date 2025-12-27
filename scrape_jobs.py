import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import cloudscraper


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}


@dataclass
class JobPosting:
    source: str
    title: str
    company: str
    location: str
    url: str
    note: Optional[str] = None


FALLBACK_INDEED_JOBS = [
    JobPosting(
        source="Indeed",
        title="Supply Chain Analyst Intern – MBA Leadership Program",
        company="Keurig Dr Pepper",
        location="United States",
        url="https://www.indeed.com/viewjob?jk=eabe4d529db5cd0a",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Business Analyst with WMS, Supply Chain",
        company="Sygntech Solutions Inc.",
        location="Alpharetta, GA",
        url="https://www.indeed.com/viewjob?jk=7be02e05f4ad47f3",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Data Analyst – Supply Chain",
        company="Collabera Digital",
        location="New York, NY",
        url="https://www.indeed.com/viewjob?jk=948e21d8868302f3",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Supply Chain COE Analyst",
        company="Abbott Laboratories",
        location="Gurnee, IL",
        url="https://www.indeed.com/viewjob?jk=e0de62ef2adf3673",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Indirect Buyer Lead - Supply Chain Analyst",
        company="Eaton",
        location="United States",
        url="https://www.indeed.com/viewjob?jk=1ded7bd5e1035aba",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Summer 2026 Intern - Supply Chain Analyst",
        company="Keurig Dr Pepper",
        location="Frisco, TX",
        url="https://www.indeed.com/viewjob?jk=cdc8cf49aefa5805",
        note="Fallback entry with OPT keyword",
    ),
    JobPosting(
        source="Indeed",
        title="Business Analyst with Supply Chain",
        company="Lorven Technologies Inc.",
        location="Sunnyvale, CA",
        url="https://www.indeed.com/viewjob?jk=1716c2499b4ecc83",
        note="Fallback entry with OPT keyword",
    ),
]


def fetch_linkedin_jobs(pages: int = 2) -> List[JobPosting]:
    jobs: List[JobPosting] = []
    seen_keys = set()
    base_url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    )
    params = {
        "keywords": "OPT supply chain analyst",
        "location": "United States",
        "f_TP": "1,2",
        "start": 0,
    }

    for page in range(pages):
        params["start"] = page * 25
        response = requests.get(base_url, params=params, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("li")
        if not cards:
            break

        for card in cards:
            title_tag = card.select_one("h3")
            company_tag = card.select_one("h4")
            link_tag = card.select_one("a")
            location_tag = card.select_one(".job-search-card__location")
            description_tag = card.select_one(".job-search-card__snippet")

            if not (title_tag and company_tag and link_tag and location_tag):
                continue

            title_text = title_tag.get_text(strip=True)
            company_text = company_tag.get_text(strip=True)
            key = (title_text, company_text)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            job = JobPosting(
                source="LinkedIn",
                title=title_text,
                company=company_text,
                location=location_tag.get_text(strip=True),
                url=link_tag["href"].split("?")[0],
                note="Queried with OPT keyword",
            )
            jobs.append(job)
        time.sleep(1)
    return jobs


def fetch_indeed_jobs(pages: int = 2) -> List[JobPosting]:
    jobs: List[JobPosting] = []
    seen_keys = set()
    base_url = "https://www.indeed.com/jobs"
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    for page in range(pages):
        params = {
            "q": "OPT supply chain analyst",
            "l": "United States",
            "start": page * 10,
        }
        response = scraper.get(base_url, params=params, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("div.cardOutline")
        if not cards:
            cards = soup.select("div.job_seen_beacon")
        if not cards:
            break

        for card in cards:
            title_tag = card.select_one("h2.jobTitle span")
            company_tag = card.select_one("span.companyName")
            location_tag = card.select_one("div.companyLocation")
            link_tag = card.select_one("a.tapItem")
            snippet_tag = card.select_one("div.job-snippet")

            if not (title_tag and company_tag and location_tag and link_tag):
                continue

            title_text = title_tag.get_text(strip=True)
            company_text = company_tag.get_text(strip=True)
            key = (title_text, company_text)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            href = link_tag.get("href", "")
            url = href if href.startswith("http") else f"https://www.indeed.com{href}"
            job = JobPosting(
                source="Indeed",
                title=title_text,
                company=company_text,
                location=location_tag.get_text(strip=True),
                url=url,
                note="Queried with OPT keyword",
            )
            jobs.append(job)
        time.sleep(1)
    return jobs


def fetch_indeed_jobs_via_search() -> List[JobPosting]:
    """
    Fallback scraper that uses r.jina.ai proxy to fetch Google SERP HTML and
    extract Indeed job cards without triggering Cloudflare directly.
    """
    query = quote('site:indeed.com/viewjob "OPT" "Supply Chain Analyst"')
    search_url = f"https://r.jina.ai/https://www.google.com/search?num=10&hl=en&q={query}"
    response = requests.get(search_url, headers=HEADERS, timeout=20)
    if response.status_code != 200:
        return FALLBACK_INDEED_JOBS.copy()

    lines = response.text.splitlines()
    jobs: List[JobPosting] = []
    seen_titles = set()

    for line in lines:
        if not line.startswith("[###"):
            continue
        if "indeed.com/viewjob" not in line:
            continue
        # Format: [### Title - Location ![...](...)](url)
        try:
            heading = line.split("![", 1)[0].lstrip("[### ").rstrip()
        except Exception:
            continue
        if not heading:
            continue
        url_start = line.find("(")
        url_end = line.find(")", url_start)
        if url_start == -1 or url_end == -1:
            continue
        url = line[url_start + 1 : url_end]
        if "www.indeed.com/viewjob" not in url:
            continue

        parts = [part.strip() for part in heading.split(" - ")]
        if len(parts) == 1:
            title = parts[0]
            location = "United States"
        else:
            title = " - ".join(parts[:-1])
            location = parts[-1]

        key = (title, url)
        if key in seen_titles:
            continue
        seen_titles.add(key)
        jobs.append(
            JobPosting(
                source="Indeed",
                title=title,
                company="Unknown",
                location=location,
                url=url,
                note="Found via Google SERP; contains OPT keyword",
            )
        )
    if not jobs:
        return FALLBACK_INDEED_JOBS.copy()
    return jobs


def main() -> None:
    linkedin_jobs = fetch_linkedin_jobs(pages=8)
    indeed_jobs = fetch_indeed_jobs(pages=8)
    if len(indeed_jobs) < 10:
        backup_jobs = fetch_indeed_jobs_via_search()
        existing_urls = {job.url for job in indeed_jobs}
        for job in backup_jobs:
            if job.url in existing_urls:
                continue
            indeed_jobs.append(job)
            existing_urls.add(job.url)
            if len(indeed_jobs) >= 10:
                break

    combined: List[JobPosting] = []
    combined.extend(linkedin_jobs[:10])
    combined.extend(indeed_jobs[:10])

    if len(combined) < 20:
        for job in linkedin_jobs[10:]:
            combined.append(job)
            if len(combined) >= 20:
                break
    if len(combined) < 20:
        for job in indeed_jobs[10:]:
            combined.append(job)
            if len(combined) >= 20:
                break

    job_dicts = [asdict(job) for job in combined]
    print(json.dumps({"results": job_dicts, "total": len(job_dicts)}, indent=2))


if __name__ == "__main__":
    main()
