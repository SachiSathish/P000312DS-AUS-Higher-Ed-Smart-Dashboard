"""Build data/processed/staging/prisms_international_students_ytd.csv.

STAGING ONLY: models.py has no table for PRISMS, and PRISMS has no institution, so it cannot
feed enrollment_stats. Kept tidy so it is ready if a table is added.

Source: PRISMS "all data" YTD workbook to May 2026 (pivot cache, 3.58M records). The "latest"
workbook is a subset of the same series and is not processed (it would duplicate rows).

Values are YEAR-TO-DATE CUMULATIVE: the May row already includes Jan-Apr. Never sum across
months; use one month per year (December = full calendar year; May 2026 = current part-year).

Reconciled against the published May YTD enrolments in the infographic PDF from the same release.
"""

import pandas as pd

import common as c

SRC = "bronze/education-international/education_intl-students-ytd-all_2026-05.xlsx"
OUT = c.STAGING / "prisms_international_students_ytd.csv"
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
PROVIDER_TYPE = {"Government": "public", "Non Government": "private"}
YES_NO = {"Yes": "true", "No": "false"}
GRAIN = ["year", "month", "citizenship_country", "citizenship_country_source", "state", "sector",
         "provider_type", "new_to_australia", "ends_this_year"]
MEASURES = ["ytd_enrolments", "ytd_commencements"]
# Published "Enrolments by Sector | YTD May", infographic education_intl-students-summary-infographic_2026-05.pdf
PUBLISHED_MAY = {
    2024: {"Higher Education": 398463, "VET": 275035, "Schools": 16207, "ELICOS": 97254, "Non-award": 19619},
    2025: {"Higher Education": 442157, "VET": 273884, "Schools": 17203, "ELICOS": 61388, "Non-award": 20044},
    2026: {"Higher Education": 452364, "VET": 219994, "Schools": 15901, "ELICOS": 44775, "Non-award": 19750},
}


def main():
    raw, declared = c.read_pivot_cache(c.raw_path(SRC))
    raw_rows = len(raw)
    enr, enr_stats = c.to_number(raw["DATA_YTD_Enrolments"])
    com, com_stats = c.to_number(raw["DATA_YTD_Commencements"])
    country, remapped = c.standardise_country(raw["Nationality"])

    df = pd.DataFrame({
        "year": pd.to_numeric(raw["Year"], errors="raise").astype("Int64"),
        "month": raw["Month"].map(MONTHS).astype("Int64"),
        "citizenship_country": country,
        "citizenship_country_source": c.clean_text(raw["Nationality"]),
        "state": c.clean_text(raw["State"]),
        "sector": c.clean_text(raw["Sector"]),
        "provider_type": raw["ProviderType"].map(PROVIDER_TYPE),
        "new_to_australia": raw["New_to_Australia"].map(YES_NO),
        "ends_this_year": raw["Ends_This_Year"].map(YES_NO),          # blank in source -> null
        "ytd_enrolments": enr,
        "ytd_commencements": com,
    })
    del raw
    for col, src_vals in [("month", MONTHS), ("provider_type", PROVIDER_TYPE), ("new_to_australia", YES_NO)]:
        if df[col].isna().any():
            raise SystemExit(f"unmapped values in {col}")

    df, agg = c.aggregate_grain(df, GRAIN, MEASURES)
    df["source_file"] = SRC

    # reconciliation with the published release
    may = df[df["month"] == 5].groupby(["year", "sector"])["ytd_enrolments"].sum()
    checks, failures = {}, []
    for year, sectors in PUBLISHED_MAY.items():
        for sector, published in sectors.items():
            got = int(may.get((year, sector), 0))
            checks[f"{year} {sector}"] = {"published": published, "processed": got}
            if got != published:
                failures.append(f"{year} {sector}: processed {got:,} != published {published:,}")

    rows = c.write_csv(df, OUT, sort_by=GRAIN)
    c.write_report("prisms_international_students_ytd", {
        "output_file": "data/processed/staging/prisms_international_students_ytd.csv",
        "target_table": None, "staging_reason": "no PRISMS table in models.py; no institution dimension",
        "source_files": [SRC],
        "extraction": f"pivot cache via transform/extract_pivot_cache.py; {declared:,} declared, {raw_rows:,} read",
        "raw_rows": raw_rows, "processed_rows": rows, "rows_removed": {},
        "rows_aggregated": agg["rows_collapsed_by_aggregation"],
        "duplicate_count_before": agg["duplicate_rows_at_grain_before"],
        "duplicate_count_after": agg["duplicate_rows_at_grain_after"],
        "suppressed_to_null": enr_stats["suppressed_to_null"] + com_stats["suppressed_to_null"],
        "value_parsing": {"ytd_enrolments": enr_stats, "ytd_commencements": com_stats},
        "published_reconciliation": checks,
        "validation_failures": failures,
        "countries_remapped": remapped,
        "category_values": c.category_values(df, ["month", "state", "sector", "provider_type",
                                                  "new_to_australia", "ends_this_year", "citizenship_country"]),
        "warnings": ["country mapping config/country_map.csv is PROPOSED",
                     "YTD cumulative values: do not sum across months",
                     "state 'NAT' kept as published (national / no single state)"],
        "measure": "YTD enrolments and YTD commencements (a student in two courses = two enrolments)",
        "year_convention": "calendar year, year-to-date to `month`",
        "transformations": ["Month name -> month number", "ProviderType Government->public, Non Government->private",
                            "Yes/No -> true/false", "country standardised (raw kept in citizenship_country_source)"],
    })
    c.write_dictionary("staging/prisms_international_students_ytd.csv", "PRISMS international students (YTD)", [
        "STAGING -- no target table in models.py. Grain: every column except the two measures and source_file.",
        "Values are cumulative year-to-date. Never add months together.",
    ], [
        ("year", "Reporting year", "integer", "Year", "-", "calendar year"),
        ("month", "YTD up to this month (1-12)", "integer", "Month name -> number", "-", "calendar month"),
        ("citizenship_country", "Nationality, project standard spelling", "text", "Nationality via config/country_map.csv", "-", "-"),
        ("citizenship_country_source", "Nationality as published", "text", "Nationality", "-", "-"),
        ("state", "State/territory of study (NAT = national)", "text", "State", "-", "-"),
        ("sector", "Education sector", "text", "Sector", "-", "-"),
        ("provider_type", "public or private", "text", "ProviderType: Government->public, Non Government->private", "-", "-"),
        ("new_to_australia", "Student new to Australia", "true/false", "New_to_Australia", "-", "-"),
        ("ends_this_year", "Course ends this year (blank = not reported)", "true/false, nullable", "Ends_This_Year", "-", "-"),
        ("ytd_enrolments", "Enrolments YTD", "integer, nullable", "DATA_YTD_Enrolments", "YTD enrolments", "calendar YTD"),
        ("ytd_commencements", "Commencements YTD", "integer, nullable", "DATA_YTD_Commencements", "YTD commencements", "calendar YTD"),
        ("source_file", "MANIFEST.csv path", "text", "-", "-", "-"),
    ])
    print(f"{OUT.name}: {rows:,} rows; published check failures: {len(failures)}")


if __name__ == "__main__":
    main()
