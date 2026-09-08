#!/usr/bin/env python3
"""
Job monitor scraper.

Reads scripts/sites.json (list of career pages to check), fetches each page,
extracts job listings using per-site CSS selectors, compares against the
previously saved state, and writes an updated docs/data.json for the
dashboard to display.

Run manually:  python3 scripts/scrape.py
Run on a schedule via the GitHub Actions workflow in .github/workflows/monitor.yml
"""

import json
import hashlib
import datetime
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_FILE = os.path.join(ROOT, "scripts", "sites.json")
STATE_FILE = os.path.join(ROOT, "data", "state.json")
DASHBOARD_DATA_FILE = os.path.join(ROOT, "docs", "data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0; +https://github.com/)"
}

REQUEST_TIMEOUT = 20
REQUEST_DELAY_SECONDS = 2  # be polite between requests


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def make_job_id(title, link):
    raw = f"{title.strip()}|{link.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def resolve_link(base_url, href):
    if not href:
        return base_url
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return base_url.rstrip("/") + href
    return base_url.rstrip("/") + "/" + href


def scrape_site(site):
    """Fetch one site and return a list of {id, title, link} job dicts."""
    try:
        resp = requests.get(site["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ERROR fetching {site['name']}: {e}", file=sys.stderr)
        return None  # None = fetch failed, distinct from [] = fetched but no jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    job_elements = soup.select(site["job_selector"])

    jobs = []
    for el in job_elements:
        title_el = el.select_one(site["title_selector"])
        link_el = el.select_one(site["link_selector"])

        title = title_el.get_text(strip=True) if title_el else None
        href = link_el.get(site.get("link_attr", "href")) if link_el else None

        if not title:
            continue

        link = resolve_link(site.get("base_url", site["url"]), href)
        jobs.append({
            "id": make_job_id(title, link),
            "title": title,
            "link": link,
        })

    return jobs


def main():
    sites = load_json(SITES_FILE, [])
    state = load_json(STATE_FILE, {})  # { site_name: { job_id: {title, link, first_seen} } }

    now = datetime.datetime.utcnow().isoformat() + "Z"
    dashboard_sites = []
    any_new = False

    for site in sites:
        name = site["name"]
        print(f"Checking {name} ...")

        previous_jobs = state.get(name, {})
        current_jobs = scrape_site(site)

        site_result = {
            "name": name,
            "url": site["url"],
            "checked_at": now,
            "status": "ok",
            "jobs": [],
            "new_jobs": [],
        }

        if current_jobs is None:
            site_result["status"] = "error"
            # keep previous state untouched on fetch failure
            dashboard_sites.append(site_result)
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        updated_state_for_site = {}
        for job in current_jobs:
            jid = job["id"]
            if jid in previous_jobs:
                first_seen = previous_jobs[jid]["first_seen"]
                is_new = False
            else:
                first_seen = now
                is_new = True
                any_new = True

            updated_state_for_site[jid] = {
                "title": job["title"],
                "link": job["link"],
                "first_seen": first_seen,
            }

            job_record = {
                "title": job["title"],
                "link": job["link"],
                "first_seen": first_seen,
                "is_new": is_new,
            }
            site_result["jobs"].append(job_record)
            if is_new:
                site_result["new_jobs"].append(job_record)

        state[name] = updated_state_for_site
        dashboard_sites.append(site_result)

        print(f"  {len(current_jobs)} job(s) found, {len(site_result['new_jobs'])} new")
        time.sleep(REQUEST_DELAY_SECONDS)

    save_json(STATE_FILE, state)

    dashboard_data = {
        "last_run": now,
        "sites": dashboard_sites,
    }
    save_json(DASHBOARD_DATA_FILE, dashboard_data)

    print("Done." + (" New jobs found!" if any_new else " No new jobs."))


if __name__ == "__main__":
    main()
