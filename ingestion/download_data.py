"""
Download every verified source into data/raw/ and record provenance in MANIFEST.csv.

This is the bronze layer described in DATA-SOURCES.md: raw files exactly as published, never
edited, each one recorded with its source URL, retrieval timestamp, size and SHA-256. Cleaning
happens downstream into silver/ -- nothing here gets modified.

Two sources publish behind rotating download IDs (the Department of Education's file IDs change
every release), so those links are resolved by scraping the landing page at run time rather than
hardcoded. That is the pattern any scheduled refresh needs.

Re-running is safe: files already present with the expected size are skipped.

Run: python download_data.py
"""

import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

BRONZE = Path("data/raw")          # gitignored in the team repo; source files never get committed
MANIFEST = Path("data/MANIFEST.csv")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

CKAN = "https://data.gov.au/data/dataset/e5ae7059-bfa8-4fa4-a5c0-c13cf3520193/resource"
HA = "https://data.gov.au/data/dataset/324aa4f7-46bb-4d56-bc2d-772333a2317e/resource"
EDU = "https://www.education.gov.au"

# (folder, filename, url, dataset description, licence)
STATIC = [
    # --- Home Affairs: student visa program BP0015 -------------------------------------
    ("homeaffairs-visas", "homeaffairs_student-visas-lodged_asat-2026-06-30.xlsx",
     f"{HA}/ef31b2b4-a894-484b-99bc-e35d62ace777/download/"
     "bp0015l-student-visas-lodged-report-locked-at-2026-06-30-v100.xlsx",
     "Student visa applications lodged, FY2005-06 to 2025-26", "CC BY 2.5 AU"),
    ("homeaffairs-visas", "homeaffairs_student-visas-granted_asat-2026-06-30.xlsx",
     f"{HA}/dfc7a893-0523-4b8e-bc5a-829e35bec90f/download/"
     "bp0015l-student-visas-granted-report-locked-at-2026-06-30-v100.xlsx",
     "Student visas granted, FY2005-06 to 2025-26", "CC BY 2.5 AU"),
    ("homeaffairs-visas", "homeaffairs_student-visa-grant-rates_asat-2026-06-30.xlsx",
     f"{HA}/b4775919-d0f5-4beb-8901-6384342774c6/download/"
     "bp0015l-student-visa-grant-rates-locked-at-2026-06-30-v100.xlsx",
     "Student visa grant rates, FY2005-06 to 2025-26", "CC BY 2.5 AU"),
    ("homeaffairs-visas", "homeaffairs_pivot-table-user-guide_v4.pdf",
     f"{HA}/39e7d9ba-ba9d-47e2-9d8f-3708444506a1/download/pivot-table-user-guide-v400.pdf",
     "Home Affairs guide to reading the pivot workbooks", "CC BY 2.5 AU"),

    # --- CRICOS register: current CSVs (datastore-backed, always latest) ---------------
    ("cricos-register", "cricos_institutions_asat-2026-08-09.csv",
     f"{CKAN}/7f6941f3-5327-4db7-b556-5f16d77f63c1/download/cricos-institutions.csv",
     "1,552 CRICOS providers with Government/Private type and capacity", "CC BY 2.5 AU"),
    ("cricos-register", "cricos_courses_asat-2026-08-09.csv",
     f"{CKAN}/48cacf69-2082-415e-9595-f17d0c3a4af0/download/cricos-courses.csv",
     "26,738 courses with ASCED field of education, level and tuition fees", "CC BY 2.5 AU"),
    ("cricos-register", "cricos_locations_asat-2026-08-09.csv",
     f"{CKAN}/45d29535-1360-4486-8242-3850e61b5524/download/cricos-locations.csv",
     "Physical campus locations for geospatial joins", "CC BY 2.5 AU"),
    ("cricos-register", "cricos_course-locations_asat-2026-08-09.csv",
     f"{CKAN}/4cd2de02-8ba3-4eb2-bac2-fe272cae3f5f/download/cricos-course-locations.csv",
     "Which courses are delivered at which campus", "CC BY 2.5 AU"),
    ("cricos-register", "cricos_providers-courses-locations_asat-2026-07-01.xlsx",
     f"{CKAN}/051a159a-182b-4ca7-a4ff-8cafce78181d/download/"
     "cricos-providers-courses-and-locations-as-at-2026-7-1-10-38-49.xlsx",
     "Monthly point-in-time snapshot -- one frame of the provider entry/exit panel",
     "CC BY 2.5 AU"),

    # --- ABS: net overseas migration by visa group ------------------------------------
    ("abs-migration", "abs_nom-arrivals-departures-by-visa_calendar-year.csv",
     "https://data.api.abs.gov.au/rest/data/ABS,ABS_NOM_VISA_CY,1.0.0/all"
     "?format=csvfilewithlabels",
     "Net overseas migration by visa group and state, 2004 onwards", "CC BY 4.0"),
    ("abs-migration", "abs_nom-arrivals-departures-by-visa_financial-year.csv",
     "https://data.api.abs.gov.au/rest/data/ABS,ABS_NOM_VISA_FY,1.0.0/all"
     "?format=csvfilewithlabels",
     "Net overseas migration by visa group and state, FY2004-05 onwards", "CC BY 4.0"),

    # --- Policy corpus ----------------------------------------------------------------
    ("legislation-policy", "homeaffairs_ministerial-direction-115_2025-11-14.pdf",
     "https://immi.homeaffairs.gov.au/support-subsite/files/ministerial-direction-115.pdf",
     "MD115 -- current visa processing priority direction", "CC BY 3.0 AU"),
]

# Pages whose download links carry rotating IDs -- resolve at run time.
# (folder, landing page, link-text pattern, output filename, description)
# PRISMS publishes monthly and keeps older releases on the page, so its patterns capture the
# month (PERIOD) and resolve() takes the newest; {period} in the filename becomes e.g. 2026-05.
PERIOD = r"/(?P<period>[a-z]+-\d{4})"   # leading / stops the href prefix eating the month
SCRAPED = [
    ("education-international",
     f"{EDU}/international-education-data-and-research/"
     "international-student-monthly-summary-and-data-tables",
     PERIOD + r"-latest-data/xlsx",
     "education_intl-students-ytd-latest_{period}.xlsx",
     "PRISMS year-to-date international student data, current year"),
    ("education-international",
     f"{EDU}/international-education-data-and-research/"
     "international-student-monthly-summary-and-data-tables",
     PERIOD + r"-all-data/xlsx",
     "education_intl-students-ytd-all_{period}.xlsx",
     "PRISMS year-to-date international student data, full history"),
    ("education-international",
     f"{EDU}/international-education-data-and-research/"
     "international-student-monthly-summary-and-data-tables",
     PERIOD + r"-summary-infographic/pdf",
     "education_intl-students-summary-infographic_{period}.pdf",
     "Monthly summary infographic"),
    # Higher education statistics (HESSC) are collected by Shangavi's scraper (topics 1 and 2).
]


def fetch_legislation(dest):
    """
    Page the Federal Register of Legislation OData API into one JSON file.

    The API caps $top at 100 and there are 170 matching titles, so this has to paginate.
    """
    import json

    base = "https://api.prod.legislation.gov.au/v1/titles"
    params = {
        "$filter": "contains(name,'Overseas Students')",
        "$select": "name,id,collection,administeringDepartments",
        "$top": "100",
    }
    items, skip = [], 0
    while True:
        r = requests.get(base, params={**params, "$skip": str(skip)}, timeout=90)
        r.raise_for_status()
        batch = r.json().get("value", [])
        if not batch:
            break
        items.extend(batch)
        skip += len(batch)

    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items, indent=1).encode()
    dest.write_bytes(payload)
    return len(payload), hashlib.sha256(payload).hexdigest()


def resolve(page, pattern):
    """
    Find the current download link on a landing page.

    Returns (url, period). If the pattern captures a month such as "may-2026", the newest
    release on the page wins and period is "2026-05"; otherwise the first match wins and
    period is None.
    """
    r = requests.get(page, headers=UA, timeout=90)
    r.raise_for_status()
    hits = list(re.finditer(r'href="([^"]*' + pattern + r'[^"]*)"', r.text))
    if not hits:
        raise LookupError(f"no link matching {pattern!r} on {page}")
    if "period" not in hits[0].groupdict():
        return urljoin(page, hits[0].group(1)), None

    def when(m):
        mon, yr = m.group("period").rsplit("-", 1)
        return int(yr), datetime.strptime(mon[:3], "%b").month

    newest = max(hits, key=when)
    yr, mo = when(newest)
    return urljoin(page, newest.group(1)), f"{yr}-{mo:02d}"


def download(url, dest):
    """Stream a file to disk, returning (bytes, sha256)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    h, n = hashlib.sha256(), 0
    with requests.get(url, headers=UA, timeout=600, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                n += len(chunk)
    return n, h.hexdigest()


def main():
    jobs = []
    for folder, name, url, desc, lic in STATIC:
        jobs.append((folder, name, url, desc, lic, None))
    for folder, page, pattern, name, desc in SCRAPED:
        jobs.append((folder, name, None, desc, "CC BY 4.0", (page, pattern)))
    jobs.append(("legislation-policy",
                 "legislation_overseas-students-titles_asat-2026-08-09.json",
                 "https://api.prod.legislation.gov.au/v1/titles"
                 "?$filter=contains(name,'Overseas Students')",
                 "170 Acts and instruments mentioning Overseas Students, paged from the API",
                 "CC BY 4.0", "ODATA"))

    rows, failed = [], []
    for i, (folder, name, url, desc, lic, scrape) in enumerate(jobs, 1):
        dest = BRONZE / folder / name
        print(f"[{i:2d}/{len(jobs)}] {name}")

        try:
            if scrape == "ODATA":
                size, digest = fetch_legislation(dest)
                print(f"          {size:,} bytes")
                rows.append({
                    "file": str(dest.relative_to(BRONZE.parent)).replace("\\", "/"),
                    "source_group": folder, "description": desc, "source_url": url,
                    "licence": lic, "bytes": size, "sha256": digest,
                    "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                })
                continue
            if scrape:
                url, period = resolve(*scrape)
                if period:
                    name = name.format(period=period)
                    dest = BRONZE / folder / name
                print(f"          resolved -> {url}")
            if dest.exists() and dest.stat().st_size > 0:
                print(f"          already have it ({dest.stat().st_size:,} bytes), skipping")
                data = dest.read_bytes()
                size, digest = len(data), hashlib.sha256(data).hexdigest()
            else:
                size, digest = download(url, dest)
                print(f"          {size:,} bytes")
        except Exception as e:
            print(f"          FAILED: {type(e).__name__}: {e}")
            failed.append((name, str(e)))
            continue

        rows.append({
            "file": str(dest.relative_to(BRONZE.parent)).replace("\\", "/"),
            "source_group": folder,
            "description": desc,
            "source_url": url,
            "licence": lic,
            "bytes": size,
            "sha256": digest,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = sum(r["bytes"] for r in rows)
    print(f"\n{len(rows)} files, {total/1e6:.1f} MB total")
    print(f"manifest -> {MANIFEST}")
    if failed:
        print(f"\n{len(failed)} FAILED:")
        for n, e in failed:
            print(f"  {n}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
