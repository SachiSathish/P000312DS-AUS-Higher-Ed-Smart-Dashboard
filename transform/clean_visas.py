"""Build the Home Affairs student-visa (BP0015) staging tables.

STAGING ONLY: models.py has no visa table.

  staging/visa_lodgements.csv  <- student-visas-lodged    (year = financial year of LODGEMENT)
  staging/visa_grants.csv      <- student-visas-granted   (year = financial year of GRANT)
  staging/visa_decisions.csv   <- student-visa-grant-rates (year = financial year of DECISION)

The three are kept separate on purpose: each counts a different event in a different year, so
joining lodged to granted on financial_year would compare different cohorts. grant rate is not
stored -- compute granted / (granted + refused) from visa_decisions in the app layer.

All three workbooks are pivot caches (2.1M-2.3M records each).
"""

import pandas as pd

import common as c

FILES = {
    "visa_lodgements": ("bronze/homeaffairs-visas/homeaffairs_student-visas-lodged_asat-2026-06-30.xlsx",
                        "Financial Year of Visa Lodged", {"Total": "lodged"}),
    "visa_grants": ("bronze/homeaffairs-visas/homeaffairs_student-visas-granted_asat-2026-06-30.xlsx",
                    "Financial Year of Visa Grant", {"Total": "granted"}),
    "visa_decisions": ("bronze/homeaffairs-visas/homeaffairs_student-visa-grant-rates_asat-2026-06-30.xlsx",
                       "Financial Year of Decision", {"Grant Total": "granted", "Refused Total": "refused",
                                                      "Total": "decided"}),
}
DIMS = {
    "Financial Year Quarter": "quarter", "Client Location": "client_location",
    "Lodgement Channel": "lodgement_channel", "Sector": "sector", "Applicant Type": "applicant_type",
    "Education Provider Registered State": "provider_state", "Gender": "gender", "Age Group": "age_group",
    "Last Visa Held - Visa Category": "last_visa_category",
}
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
YEAR_EVENT = {"visa_lodgements": "lodgement", "visa_grants": "grant", "visa_decisions": "decision"}


def clean_one(name, src, year_field, measures):
    raw, declared = c.read_pivot_cache(c.raw_path(src))
    raw_rows = len(raw)
    warnings, parsing = [], {}

    # Labels are '2024-25' or '2025-26 to 30 June 2026' (part-year as at the lock date).
    # The cache also lists stale labels from earlier releases; only labels used by records count.
    label = c.clean_text(raw[year_field])
    df = pd.DataFrame({"financial_year": label.str.extract(r"^(\d{4}-\d{2})(?: to .+)?$", expand=False)})
    if df["financial_year"].isna().any():
        raise SystemExit(f"{name}: unexpected financial year labels {label[df['financial_year'].isna()].unique()}")
    used = pd.DataFrame({"fy": df["financial_year"], "label": label}).drop_duplicates()
    if used["fy"].duplicated().any():
        raise SystemExit(f"{name}: one financial year published under several labels: {used.to_dict('records')}")
    fy_labels = {r.fy: r.label for r in used.itertuples() if r.fy != r.label}
    df["quarter"] = c.clean_text(raw["Financial Year Quarter"]).str.extract(r"^(Q[1-4])", expand=False)
    month = c.clean_text(raw["Month"]).str.extract(r"^M\d{2} (\w{3})$", expand=False)
    df["month"] = month.map(MONTHS).astype("Int64")
    if df["quarter"].isna().any() or df["month"].isna().any():
        raise SystemExit(f"{name}: unparsed quarter/month labels")
    for src_col, col in DIMS.items():
        if src_col in raw.columns and col != "quarter":
            df[col] = c.clean_text(raw[src_col])
    df["citizenship_country"], remapped = c.standardise_country(raw["Citizenship Country"])
    df["citizenship_country_source"] = c.clean_text(raw["Citizenship Country"])
    for src_col, col in measures.items():
        df[col], parsing[col] = c.to_number(raw[src_col])
    del raw

    dropped_cols = []
    if name == "visa_decisions":
        both = df[["granted", "refused", "decided"]].notna().all(axis=1)
        off = int((both & (df["granted"] + df["refused"] != df["decided"])).sum())
        if off == 0 and df["decided"].notna().sum() == both.sum():
            df = df.drop(columns="decided")
            dropped_cols.append("decided (= granted + refused on every row; derived, not stored)")
        else:
            warnings.append(f"decided != granted + refused on {off} rows; decided kept")
    measure_cols = [m for m in measures.values() if m in df.columns]
    grain = [col for col in df.columns if col not in measure_cols]
    df, agg = c.aggregate_grain(df, grain, measure_cols)
    df["source_file"] = src

    rows = c.write_csv(df, c.STAGING / f"{name}.csv", sort_by=grain)
    cats = [col for col in grain if col not in ("citizenship_country_source",)]
    c.write_report(name, {
        "output_file": f"data/processed/staging/{name}.csv", "target_table": None,
        "staging_reason": "no visa table in models.py", "source_files": [src],
        "extraction": f"pivot cache via transform/extract_pivot_cache.py; {declared:,} declared, {raw_rows:,} read",
        "raw_rows": raw_rows, "processed_rows": rows, "rows_removed": {},
        "rows_aggregated": agg["rows_collapsed_by_aggregation"],
        "duplicate_count_before": agg["duplicate_rows_at_grain_before"],
        "duplicate_count_after": agg["duplicate_rows_at_grain_after"],
        "suppressed_to_null": sum(p["suppressed_to_null"] for p in parsing.values()),
        "value_parsing": parsing, "columns_dropped": dropped_cols + ["Grant Rate (derived ratio)"] * (name == "visa_decisions"),
        "totals": {m: int(df[m].sum()) for m in measure_cols},
        "countries_remapped": remapped,
        "financial_year_labels_relabelled": fy_labels,
        "category_values": c.category_values(df, cats),
        "warnings": warnings + ["country mapping config/country_map.csv is PROPOSED",
                                "'Not Specified' / 'Not Available' categories kept as published"],
        "measure": ", ".join(f"{m}: count of visa applications ({YEAR_EVENT[name]} event)" for m in measure_cols),
        "year_convention": f"Australian financial year (Jul-Jun) of {YEAR_EVENT[name]}, e.g. 2024-25",
        "transformations": ["'Q1 (Jul-Sep)' -> Q1", "'M01 Jul' -> calendar month 7",
                            "country standardised (raw kept in citizenship_country_source)",
                            "rows summed over identical dimension values"],
    })
    rows_dict = [
        ("financial_year", f"Financial year of {YEAR_EVENT[name]}", "text YYYY-YY", year_field, "-", "financial year (Jul-Jun)"),
        ("quarter", "Financial-year quarter (Q1 = Jul-Sep)", "text Q1-Q4", "Financial Year Quarter", "-", "financial year"),
        ("month", "Calendar month number (7 = July)", "integer 1-12", "Month 'M01 Jul' -> 7", "-", "calendar month"),
        ("client_location", "Applicant in / outside Australia", "text", "Client Location", "-", "-"),
        ("lodgement_channel", "Internet / Paper", "text", "Lodgement Channel", "-", "-"),
        ("sector", "Education sector of the visa", "text", "Sector", "-", "-"),
        ("applicant_type", "Primary / Secondary applicant", "text", "Applicant Type", "-", "-"),
        ("provider_state", "Provider's registered state", "text", "Education Provider Registered State", "-", "-"),
        ("gender", "Gender", "text", "Gender", "-", "-"),
        ("age_group", "Age group", "text", "Age Group", "-", "-"),
    ]
    if "last_visa_category" in df.columns:
        rows_dict.append(("last_visa_category", "Visa held before this grant", "text", "Last Visa Held - Visa Category", "-", "-"))
    rows_dict += [
        ("citizenship_country", "Citizenship, project standard spelling", "text", "Citizenship Country via config/country_map.csv", "-", "-"),
        ("citizenship_country_source", "Citizenship as published", "text", "Citizenship Country", "-", "-"),
    ]
    rows_dict += [(m, f"Number of applications {m}", "integer, nullable", src_col, f"count ({YEAR_EVENT[name]})", "financial year")
                  for src_col, m in measures.items() if m in df.columns]
    rows_dict.append(("source_file", "MANIFEST.csv path", "text", "-", "-", "-"))
    c.write_dictionary(f"staging/{name}.csv", f"Student visas -- {name.split('_')[1]}", [
        "STAGING -- no target table in models.py. Grain: every column except the measures and source_file.",
        "Grant rate is not stored; derive it from visa_decisions (granted / (granted + refused)).",
    ], rows_dict)
    print(f"{name}.csv: {rows:,} rows")


def main(only=None):
    for name, (src, year_field, measures) in FILES.items():
        if only and name not in only:
            continue
        clean_one(name, src, year_field, measures)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
