from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


SOURCES = [
    {
        "name": "education",
        "url": (
            "https://www.education.gov.au/higher-education-statistics/"
            "student-data/selected-higher-education-statistics-2024-student-data"
        ),
        "allowed_domain": "education.gov.au",
        "allowed_path": "/higher-education-statistics/resources/",
    }
]


OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def scrape_resource_links(source):
    response = requests.get(
        source["url"],
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    records = []

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)
        href = urljoin(source["url"], link["href"])

        if not title:
            continue

        parsed = urlparse(href)

        if source["allowed_domain"] not in parsed.netloc:
            continue

        if source["allowed_path"] not in parsed.path:
            continue

        records.append(
            {
                "source_name": source["name"],
                "title": title,
                "url": href,
                "source_page": source["url"],
            }
        )

    return records


def main():
    all_records = []

    for source in SOURCES:
        print(f"Scraping: {source['name']}")
        records = scrape_resource_links(source)
        all_records.extend(records)

        print(f"Collected {len(records)} links from {source['name']}")

    df = pd.DataFrame(all_records).drop_duplicates(
        subset=["url"]
    )

    df.to_csv(
        OUTPUT_DIR / "higher_education_resources.csv",
        index=False,
    )

    df.to_json(
        OUTPUT_DIR / "higher_education_resources.json",
        orient="records",
        indent=2,
    )

    print(f"\nTotal unique resources: {len(df)}")
    print(df.head(10))


if __name__ == "__main__":
    main()