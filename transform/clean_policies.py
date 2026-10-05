"""Build data/processed/policies.csv (target table: policies).

Sources:
  - legislation.gov.au titles API dump: 170 records whose title mentions "Overseas Students";
    33 are exact repeats from API paging overlap and are dropped (137 distinct instruments). Only id, title and collection are in the dump, so summary, full_text
    and effective_date stay blank (not invented).
  - Ministerial Direction 115 PDF: title, commencement date and full text extracted from the PDF.

category rule (models allow 'immigration' | 'education'):
  - title contains the word "Migration"  -> immigration  (Migration Act 1958 family)
  - everything else in the legislation dump -> education (ESOS / Overseas Students Charge family)
  - Ministerial Direction 115 (made under s499 of the Migration Act) -> immigration
source_url for legislation = https://www.legislation.gov.au/<register id>, the register's
canonical address for that id (checked: resolves for F2020L00905).
"""

import json
import re
from datetime import datetime

import pandas as pd
import pypdf

import common as c

TITLES = "bronze/legislation-policy/legislation_overseas-students-titles_asat-2026-08-09.json"
MD115 = "bronze/legislation-policy/homeaffairs_ministerial-direction-115_2025-11-14.pdf"
COLUMNS = ["title", "category", "summary", "full_text", "effective_date", "source_url", "source_file"]


def md115_row():
    path = c.raw_path(MD115)
    text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
    text = text.replace("\x00", "").replace("�", "-")
    title = re.search(r"OFFICIAL\s*\n(Direction No\..+?)\nI, ", text, re.S)
    commences = re.search(r"This Direction commences on (\d{1,2} \w+ \d{4})", text)
    if not (title and commences):
        raise SystemExit("MD115: could not find the title or commencement clause in the PDF text")
    m = c.manifest()
    return {
        "title": re.sub(r"\s+", " ", title.group(1)).strip(),
        "category": "immigration",
        "summary": pd.NA,
        "full_text": text.strip(),
        "effective_date": datetime.strptime(commences.group(1), "%d %B %Y").strftime("%Y-%m-%d"),
        "source_url": m.loc[m["file"] == MD115, "source_url"].iloc[0],
        "source_file": MD115,
    }


def main():
    with open(c.raw_path(TITLES), encoding="utf-8") as fh:
        recs = json.load(fh)
    raw_rows = len(recs)
    leg = pd.DataFrame(recs)
    exact_dupes = int(leg.duplicated().sum())          # API paging overlap: identical records
    leg = leg.drop_duplicates()
    if leg["id"].duplicated().any():
        raise SystemExit("register ids with conflicting titles in the legislation dump")
    leg["title"] = c.clean_text(leg["name"])
    leg = pd.DataFrame({
        "title": leg["title"],
        "category": leg["title"].str.contains(r"\bMigration\b", regex=True).map({True: "immigration", False: "education"}),
        "summary": pd.NA, "full_text": pd.NA, "effective_date": pd.NA,
        "source_url": "https://www.legislation.gov.au/" + leg["id"],
        "source_file": TITLES,
    })
    df = pd.concat([leg, pd.DataFrame([md115_row()])], ignore_index=True)[COLUMNS]
    long_titles = df[df["title"].str.len() > 500]
    if len(long_titles):
        raise SystemExit(f"policy titles over 500 chars: {long_titles['title'].tolist()}")
    rows = c.write_csv(df, c.PROCESSED / "policies.csv", sort_by=["category", "title", "source_url"])

    dup_titles = int(df["title"].duplicated().sum())
    c.write_report("policies", {
        "output_file": "data/processed/policies.csv", "target_table": "policies",
        "source_files": [TITLES, MD115], "raw_rows": raw_rows + 1,
        "raw_rows_note": f"{raw_rows} legislation titles + 1 PDF", "processed_rows": rows,
        "rows_removed": {"exact duplicate records (same register id, title, collection)": exact_dupes},
        "rows_aggregated": 0,
        "duplicate_count_before": exact_dupes,
        "duplicate_count_after": int(df.duplicated(["title", "source_url"]).sum()),
        "suppressed_to_null": 0,
        "category_values": c.category_values(df, ["category"]),
        "category_counts": df["category"].value_counts().to_dict(),
        "immigration_titles": df.loc[df["category"] == "immigration", "title"].tolist(),
        "warnings": [
            f"{dup_titles} titles repeat (e.g. several 'Overseas Students Charge Regulations (Amendment)'); "
            "they are different instruments -- load key must be (title, source_url), not title alone",
            "legislation rows have no summary, full_text or effective_date: the titles dump does not carry them",
            "category is assigned by the title rule in clean_policies.py; check immigration_titles",
        ],
        "measure": "n/a (documents)",
        "year_convention": "effective_date = commencement date (MD115 only)",
        "transformations": ["title whitespace collapsed", "category by title rule",
                            "source_url from register id", "MD115 text extracted with pypdf"],
    })
    c.write_dictionary("policies.csv", "policies", [
        "Target table `policies`. Load key: (`title`, `source_url`) -- titles alone repeat."], [
        ("title", "Act / instrument / direction title", "text <=500", "legislation dump `name`; MD115 PDF heading", "-", "-"),
        ("category", "immigration or education", "text", "title rule (see script docstring)", "-", "-"),
        ("summary", "Blank", "text, nullable", "not in sources", "-", "-"),
        ("full_text", "Full text (MD115 only)", "text, nullable", "pypdf extraction; signature line is OCR-noisy", "-", "-"),
        ("effective_date", "Commencement date (MD115 only)", "date YYYY-MM-DD, nullable", "'This Direction commences on ...'", "-", "calendar date"),
        ("source_url", "Canonical URL", "text <=1000", "legislation.gov.au/<id>; MD115 from MANIFEST", "-", "-"),
        ("source_file", "MANIFEST.csv path", "text", "-", "-", "-"),
    ])
    print(f"policies.csv: {rows} rows")


if __name__ == "__main__":
    main()
