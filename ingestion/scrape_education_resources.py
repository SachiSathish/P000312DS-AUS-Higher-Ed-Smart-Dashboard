from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from datetime import datetime, timezone
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SOURCES = [
    {
        "name": "Australian Government Department of Education",
        "short_name": "education",
        "url": (
            "https://www.education.gov.au/higher-education-statistics/"
            "student-data/selected-higher-education-statistics-2024-student-data"
        ),
        "allowed_domain": "education.gov.au",
        "allowed_path": "/higher-education-statistics/resources/",
        "license_usage": "Not specified by source",
    }
]

OUTPUT_DIR = Path("data/processed")
RAW_DIR = Path("data/raw/education")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_EXTENSIONS = (
    ".xlsx",
    ".xls",
    ".csv",
    ".zip",
    ".pdf",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 60


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def safe_filename(filename):
    """
    Remove characters that Windows does not allow in filenames.
    """
    filename = unquote(filename)
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = filename.strip(" .")

    if not filename:
        filename = "downloaded_file"

    return filename[:180]


def is_allowed_domain(url, allowed_domain):
    """
    Check whether a URL belongs to the trusted domain.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    return (
        hostname == allowed_domain
        or hostname.endswith("." + allowed_domain)
    )


def extract_filename_from_response(response, file_url):
    """
    Determine a useful filename.

    Priority:
    1. Content-Disposition header
    2. Filename in URL
    3. Generated fallback filename
    """
    content_disposition = response.headers.get(
        "Content-Disposition",
        ""
    )

    match = re.search(
        r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)',
        content_disposition,
        re.IGNORECASE,
    )

    if match:
        return safe_filename(match.group(1))

    path_name = Path(
        unquote(urlparse(file_url).path)
    ).name

    if path_name:
        return safe_filename(path_name)

    return "downloaded_resource"


def infer_extension(content_type):
    """
    Infer file extension if the URL does not provide one.
    """
    content_type = content_type.lower()

    mapping = {
        "application/pdf": ".pdf",
        "text/csv": ".csv",
        "application/zip": ".zip",
        "application/vnd.ms-excel": ".xls",
        (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ): ".xlsx",
    }

    for mime, extension in mapping.items():
        if mime in content_type:
            return extension

    return ""


# ---------------------------------------------------------
# STAGE 1: SCRAPE RESOURCE PAGES
# ---------------------------------------------------------

def scrape_resource_links(source):
    """
    Scrape relevant Higher Education Statistics resource
    pages from the main Department of Education page.
    """
    print(f"\nScraping source: {source['short_name']}")

    response = requests.get(
        source["url"],
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    records = []

    for link in soup.find_all("a", href=True):
        title = link.get_text(" ", strip=True)

        if not title:
            continue

        resource_url = urljoin(
            source["url"],
            link["href"],
        )

        if not is_allowed_domain(
            resource_url,
            source["allowed_domain"],
        ):
            continue

        parsed = urlparse(resource_url)

        if source["allowed_path"] not in parsed.path:
            continue

        records.append(
            {
                "source_name": source["name"],
                "source_type": "scrape",
                "title": title,
                "url": resource_url,
                "source_page": source["url"],
                "license_usage": source["license_usage"],
                "retrieved_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )

    print(
        f"Collected {len(records)} resource links "
        f"from {source['short_name']}"
    )

    return records


# ---------------------------------------------------------
# STAGE 2: FIND ACTUAL DOWNLOAD LINKS
# ---------------------------------------------------------

def find_download_links(resource_url, allowed_domain):
    """
    Open a resource page and locate links to actual
    downloadable XLSX, XLS, CSV, ZIP or PDF files.
    """
    response = requests.get(
        resource_url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    downloads = []

    for link in soup.find_all("a", href=True):

        file_url = urljoin(
            resource_url,
            link["href"],
        )

        if not is_allowed_domain(
            file_url,
            allowed_domain,
        ):
            continue

        clean_path = urlparse(file_url).path.lower()

        # Accept links with known downloadable extensions.
        if clean_path.endswith(DOWNLOAD_EXTENSIONS):
            downloads.append(file_url)
            continue

        # Some download URLs may not visibly contain an
        # extension. Check the visible link text as well.
        link_text = link.get_text(" ", strip=True).lower()

        download_words = (
            "download",
            "xlsx",
            "excel",
            "csv",
            "spreadsheet",
            "pdf",
            "zip",
        )

        if any(
            word in link_text
            for word in download_words
        ):
            downloads.append(file_url)

    # Remove duplicates while keeping original order
    return list(dict.fromkeys(downloads))


# ---------------------------------------------------------
# STAGE 3: DOWNLOAD ACTUAL FILES
# ---------------------------------------------------------

def download_file(file_url, resource_title):
    """
    Download a file into data/raw/education/.
    """
    response = requests.get(
        file_url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        stream=True,
    )
    response.raise_for_status()

    filename = extract_filename_from_response(
        response,
        file_url,
    )

    # Add extension if the filename has none
    if not Path(filename).suffix:
        extension = infer_extension(
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        filename += extension

    # Prevent unrelated HTML pages being saved as datasets
    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if (
        "text/html" in content_type
        and not Path(filename).suffix.lower()
        in DOWNLOAD_EXTENSIONS
    ):
        print(
            f"Skipped non-file page: {file_url}"
        )
        return None

    filename = safe_filename(filename)

    filepath = RAW_DIR / filename

    # Avoid overwriting files with the same name
    counter = 1
    original_path = filepath

    while filepath.exists():
        filepath = (
            original_path.parent
            / (
                f"{original_path.stem}_{counter}"
                f"{original_path.suffix}"
            )
        )
        counter += 1

    with open(filepath, "wb") as file:
        for chunk in response.iter_content(
            chunk_size=8192
        ):
            if chunk:
                file.write(chunk)

    print(f"Downloaded: {filepath}")

    return filepath


# ---------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------

def main():

    all_resource_records = []

    # ---------------------------------------------
    # Scrape resource-page links
    # ---------------------------------------------

    for source in SOURCES:

        try:
            records = scrape_resource_links(
                source
            )

            all_resource_records.extend(
                records
            )

        except requests.RequestException as error:
            print(
                f"Could not scrape "
                f"{source['short_name']}: {error}"
            )

    if not all_resource_records:
        print("No resource links were collected.")
        return

    resources_df = pd.DataFrame(
        all_resource_records
    )

    resources_df = resources_df.drop_duplicates(
        subset=["url"]
    ).reset_index(drop=True)

    print(
        f"\nTotal unique resources: "
        f"{len(resources_df)}"
    )

    print(
        resources_df[
            [
                "source_name",
                "title",
                "url",
            ]
        ].head(10)
    )

    # ---------------------------------------------
    # Save scraped resource metadata
    # ---------------------------------------------

    resources_csv = (
        OUTPUT_DIR
        / "higher_education_resources.csv"
    )

    resources_json = (
        OUTPUT_DIR
        / "higher_education_resources.json"
    )

    resources_df.to_csv(
        resources_csv,
        index=False,
    )

    resources_df.to_json(
        resources_json,
        orient="records",
        indent=2,
    )

    print(
        f"\nSaved resource list:\n"
        f"{resources_csv}\n"
        f"{resources_json}"
    )

    # ---------------------------------------------
    # Find and download actual files
    # ---------------------------------------------

    download_records = []

    for index, row in resources_df.iterrows():

        resource_title = row["title"]
        resource_url = row["url"]

        print(
            f"\n[{index + 1}/{len(resources_df)}] "
            f"Checking resource: "
            f"{resource_title}"
        )

        matching_source = next(
            (
                source
                for source in SOURCES
                if row["source_page"]
                == source["url"]
            ),
            None,
        )

        if not matching_source:
            print(
                "Could not identify source "
                "configuration."
            )
            continue

        try:

            file_links = find_download_links(
                resource_url,
                matching_source[
                    "allowed_domain"
                ],
            )

            if not file_links:
                print(
                    "No downloadable file "
                    "found on this resource page."
                )
                continue

            print(
                f"Found {len(file_links)} "
                f"possible file(s)."
            )

            for file_url in file_links:

                try:

                    filepath = download_file(
                        file_url,
                        resource_title,
                    )

                    if filepath is None:
                        continue

                    download_records.append(
                        {
                            "source_name": (
                                row[
                                    "source_name"
                                ]
                            ),
                            "source_type": (
                                "scrape"
                            ),
                            "resource_title": (
                                resource_title
                            ),
                            "resource_page_url": (
                                resource_url
                            ),
                            "download_url": (
                                file_url
                            ),
                            "local_file": (
                                str(filepath)
                            ),
                            "license_usage": (
                                row[
                                    "license_usage"
                                ]
                            ),
                            "retrieved_at_utc": (
                                datetime.now(
                                    timezone.utc
                                ).isoformat()
                            ),
                        }
                    )

                except requests.RequestException as error:

                    print(
                        f"Download failed: "
                        f"{file_url}\n"
                        f"Reason: {error}"
                    )

        except requests.RequestException as error:

            print(
                f"Could not process "
                f"{resource_url}\n"
                f"Reason: {error}"
            )

    # ---------------------------------------------
    # Save download manifest / provenance
    # ---------------------------------------------

    if download_records:

        manifest_df = pd.DataFrame(
            download_records
        )

        manifest_path = (
            OUTPUT_DIR
            / "download_manifest.csv"
        )

        manifest_df.to_csv(
            manifest_path,
            index=False,
        )

        print(
            "\n----------------------------------"
        )
        print(
            f"Downloaded "
            f"{len(download_records)} files."
        )
        print(
            f"Manifest saved to: "
            f"{manifest_path}"
        )
        print(
            f"Raw files saved to: "
            f"{RAW_DIR}"
        )
        print(
            "----------------------------------"
        )

    else:

        print(
            "\nNo downloadable files "
            "were found."
        )


if __name__ == "__main__":
    main()