"""Build data/processed/data_sources.csv (target table: data_sources) from data/MANIFEST.csv.

One row per raw file. source_file is the load key that every other processed file points at.

source_type (models allow 'api' | 'csv' | 'scrape'):
  - ABS data API and legislation.gov.au API         -> api
  - files fetched as published .csv                  -> csv
  - everything else (xlsx / pdf files whose links are published on agency pages) -> scrape
    The schema has no value for "direct file download"; this is flagged as a warning.
retrieved_at: MANIFEST retrieved_utc, written as 'YYYY-MM-DD HH:MM:SS' in UTC.
"""

import pandas as pd

import common as c


def source_type(row):
    if "api.abs.gov.au" in row["source_url"] or "api.prod.legislation.gov.au" in row["source_url"]:
        return "api"
    if row["file"].lower().endswith(".csv"):
        return "csv"
    return "scrape"


def main():
    m = c.manifest()
    for f in m["file"]:
        c.raw_path(f)                                   # fingerprint check for every listed file
    df = pd.DataFrame({
        "name": m["description"].str.strip(),
        "source_type": m.apply(source_type, axis=1),
        "url": m["source_url"],
        "retrieved_at": pd.to_datetime(m["retrieved_utc"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S"),
        "license_notes": m["licence"],
        "source_file": m["file"],
    })
    if (df["name"].str.len() > 255).any() or (df["url"].str.len() > 1000).any():
        raise SystemExit("data_sources name/url over schema length")
    rows = c.write_csv(df, c.PROCESSED / "data_sources.csv", sort_by=["source_file"])
    c.write_report("data_sources", {
        "output_file": "data/processed/data_sources.csv", "target_table": "data_sources",
        "source_files": ["MANIFEST.csv"], "raw_rows": len(m), "processed_rows": rows,
        "rows_removed": {}, "rows_aggregated": 0,
        "duplicate_count_before": int(m["file"].duplicated().sum()),
        "duplicate_count_after": int(df["source_file"].duplicated().sum()), "suppressed_to_null": 0,
        "category_values": c.category_values(df, ["source_type", "license_notes"]),
        "warnings": ["source_type 'scrape' is used for direct xlsx/pdf downloads: the schema has no "
                     "'download' value -- team decision needed"],
        "measure": "n/a", "year_convention": "retrieved_at in UTC",
        "transformations": ["description -> name", "retrieved_utc -> retrieved_at (UTC, no offset)"],
    })
    c.write_dictionary("data_sources.csv", "data_sources", [
        "Target table `data_sources`. Load key: `source_file` (= MANIFEST.csv `file`)."], [
        ("name", "Dataset description", "text <=255", "MANIFEST description", "-", "-"),
        ("source_type", "api, csv or scrape", "text", "rule in clean_data_sources.py", "-", "-"),
        ("url", "Download URL", "text <=1000", "MANIFEST source_url", "-", "-"),
        ("retrieved_at", "When the file was downloaded (UTC)", "datetime YYYY-MM-DD HH:MM:SS", "MANIFEST retrieved_utc", "-", "-"),
        ("license_notes", "Licence", "text", "MANIFEST licence", "-", "-"),
        ("source_file", "MANIFEST.csv file path (load key)", "text", "MANIFEST file", "-", "-"),
    ])
    print(f"data_sources.csv: {rows} rows")


if __name__ == "__main__":
    main()
