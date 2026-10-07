"""Build the ABS net overseas migration (NOM) staging tables.

STAGING ONLY: models.py has no migration table.

  staging/abs_nom_financial_year.csv  <- ABS_NOM_VISA_FY (year ending 30 June; '2004-05' style)
  staging/abs_nom_calendar_year.csv   <- ABS_NOM_VISA_CY (calendar year)

The two conventions are written to separate files and never converted into each other.

Aggregate rows (visa group 'Temporary visa - Total', 'Permanent visa - Total', 'Total', and
region 'Australia') are tested against the sum of their components:
  - if they equal the component sum on every row they are redundant and removed;
  - otherwise they are kept with is_aggregate = true (ABS rounds to the nearest 10 and 'Australia'
    includes Other Territories, so totals need not equal the parts) -- filter on is_aggregate
    before summing.
"""

import pandas as pd

import common as c

FILES = {
    "abs_nom_financial_year": "bronze/abs-migration/abs_nom-arrivals-departures-by-visa_financial-year.csv",
    "abs_nom_calendar_year": "bronze/abs-migration/abs_nom-arrivals-departures-by-visa_calendar-year.csv",
}
TEMP = ["2", "3", "4", "5", "6", "7", "8"]
PERM = ["10", "11", "12", "15"]
VISA_TOTALS = {"1": TEMP, "9": PERM, "16": ["1", "9", "13", "14", "17"]}
GRAIN_DIMS = ["visa_group_code", "migration_type_code", "region_code"]


def reconcile(df, year_col):
    """Return {aggregate label: rows whose value differs from the sum of components}."""
    keyed = df.set_index(["visa_group_code", "migration_type_code", "region_code", year_col])["persons"]
    result = {}
    for total, parts in VISA_TOTALS.items():
        t = keyed.xs(total, level="visa_group_code")
        s = keyed[keyed.index.get_level_values("visa_group_code").isin(parts)].groupby(
            level=["migration_type_code", "region_code", year_col]).sum(min_count=1)
        result[f"visa_group_code {total}"] = int((t - s.reindex(t.index)).abs().gt(0).sum())
    t = keyed.xs("AUS", level="region_code")
    s = keyed[keyed.index.get_level_values("region_code") != "AUS"].groupby(
        level=["visa_group_code", "migration_type_code", year_col]).sum(min_count=1)
    result["region_code AUS"] = int((t - s.reindex(t.index)).abs().gt(0).sum())
    return result


def clean_one(name, src):
    raw = pd.read_csv(c.raw_path(src), dtype=str, keep_default_na=False)
    raw_rows = len(raw)
    fy = "FY" in raw["STRUCTURE_ID"].iloc[0]
    if raw["STRUCTURE_ID"].nunique() != 1 or raw["UNIT_MEASURE"].unique().tolist() != ["PSNS"]:
        raise SystemExit(f"{name}: mixed structures or units")
    persons, stats = c.to_number(raw["OBS_VALUE"])
    year = pd.to_numeric(raw["TIME_PERIOD"], errors="raise").astype("Int64")
    if fy:
        if raw["REPYEAREND"].unique().tolist() != ["30-6"]:
            raise SystemExit("FY file without a 30 June year end")
        year_col = "financial_year"
        year_val = (year - 1).astype(str) + "-" + (year % 100).astype(str).str.zfill(2)   # 2005 -> 2004-05
    else:
        year_col, year_val = "calendar_year", year

    df = pd.DataFrame({
        year_col: year_val,
        "visa_group_code": c.clean_text(raw["MEASURE"]),
        "visa_group": c.clean_text(raw["Visa and Citizenship Groups"]),
        "migration_type_code": c.clean_text(raw["MIGRATIONTYPE"]),
        "migration_type": c.clean_text(raw["Migration Type"]),
        "region_code": c.clean_text(raw["REGION"]),
        "region": c.clean_text(raw["Region"]),
        "persons": persons,
        "obs_status": c.clean_text(raw["OBS_STATUS"]),
    })
    dup_before = int(df.duplicated(GRAIN_DIMS + [year_col]).sum())
    if dup_before:
        raise SystemExit(f"{name}: {dup_before} duplicate observations")

    diffs = reconcile(df, year_col)
    removed, flagged = {}, []
    agg_mask = pd.Series(False, index=df.index)
    for label, n_diff in diffs.items():
        col, code = label.split(" ")
        rows = df[col] == code
        if n_diff == 0:
            removed[f"{label} equals the sum of its components (redundant)"] = int(rows.sum())
            df = df[~rows]
            agg_mask = agg_mask[~rows]
        else:
            agg_mask = agg_mask | rows
            flagged.append(f"{label}: differs from its components on {n_diff} rows -> kept, is_aggregate=true")
    df = df.assign(is_aggregate=agg_mask.map({True: "true", False: "false"}))
    if df["obs_status"].isna().all():
        df = df.drop(columns="obs_status")
    df["source_file"] = src

    out = c.STAGING / f"{name}.csv"
    rows = c.write_csv(df, out, sort_by=[year_col] + GRAIN_DIMS)
    c.write_report(name, {
        "output_file": f"data/processed/staging/{name}.csv", "target_table": None,
        "staging_reason": "no migration table in models.py", "source_files": [src],
        "raw_rows": raw_rows, "processed_rows": rows, "rows_removed": removed, "rows_aggregated": 0,
        "duplicate_count_before": dup_before, "duplicate_count_after": int(df.duplicated(GRAIN_DIMS + [year_col]).sum()),
        "suppressed_to_null": stats["suppressed_to_null"], "value_parsing": stats,
        "aggregate_reconciliation_rows_differing": diffs,
        "category_values": c.category_values(df, [year_col, "visa_group", "migration_type", "region", "is_aggregate"]),
        "warnings": flagged + ["ABS values are rounded to the nearest 10"],
        "measure": "persons (NOM arrivals / departures)",
        "year_convention": "financial year ending 30 June (TIME_PERIOD 2005 -> 2004-05)" if fy else "calendar year",
        "transformations": ["SDMX labelled CSV reduced to one value per row", "ABS codes kept as text",
                            "redundant aggregate rows removed / non-reconciling ones flagged"],
    })
    c.write_dictionary(f"staging/{name}.csv", f"ABS NOM by visa group -- {'financial' if fy else 'calendar'} year", [
        "STAGING -- no target table in models.py. Grain: year x visa_group_code x migration_type_code x region_code.",
        "Rows with is_aggregate = true are totals that do not equal their parts; exclude them before summing.",
    ], [
        (year_col, "Reference year", "text YYYY-YY" if fy else "integer", "TIME_PERIOD", "-",
         "financial year ending 30 June" if fy else "calendar year"),
        ("visa_group_code", "ABS visa / citizenship group code", "text", "MEASURE", "-", "-"),
        ("visa_group", "Visa / citizenship group", "text", "Visa and Citizenship Groups", "-", "-"),
        ("migration_type_code", "ABS code (1 arrivals, 2 departures)", "text", "MIGRATIONTYPE", "-", "-"),
        ("migration_type", "NOM arrivals or NOM departures", "text", "Migration Type", "-", "-"),
        ("region_code", "ABS state code (AUS = Australia)", "text", "REGION", "-", "-"),
        ("region", "State / territory or Australia", "text", "Region", "-", "-"),
        ("persons", "Number of people", "integer, nullable", "OBS_VALUE", "persons, rounded to 10", year_col),
        ("is_aggregate", "true for total rows kept because they do not reconcile", "true/false", "reconciliation", "-", "-"),
        ("source_file", "MANIFEST.csv path", "text", "-", "-", "-"),
    ])
    print(f"{name}.csv: {rows:,} rows; removed {sum(removed.values())}; flagged {len(flagged)} aggregate types")


def main():
    for name, src in FILES.items():
        clean_one(name, src)


if __name__ == "__main__":
    main()
