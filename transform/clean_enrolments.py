"""Build the enrolment star from the HESSC 2024 enrolments pivot workbook.

Outputs (target table in brackets):
  data/processed/enrollment_stats.csv      (enrollment_stats)
  data/processed/fields_of_study.csv       (fields_of_study)
  data/processed/citizenship_statuses.csv  (citizenship_statuses)
  data/processed/quarantine/enrollment_stats_quarantine.csv  -- not loadable, kept with a reason

Read with the pivot-cache extractor: the visible sheet is a summary view of 235,292 records.

Measure: student_count = HESSC "Enrolment Count" (all students: commencing + continuing,
headcount of course enrolments, not EFTSL). Each record is assigned to its PRIMARY broad field.
Combined courses are therefore counted once, under their primary field, so the field rows add
up to the institution total. (The per-field "... Count" columns credit a combined course to both
fields and are not used.)

Year: calendar (reference) year of enrolment, 2020-2024.
Grain: institution x field x citizenship x year. Gender, course level, attendance etc. are summed.

Requires data/processed/institutions.csv (run clean_institutions.py first).
"""

import re

import pandas as pd

import common as c

HESSC = "bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx"
CRICOS_COURSES = "bronze/cricos-register/cricos_courses_asat-2026-08-09.csv"
CITIZENSHIP = {"Domestic": "domestic", "Overseas": "international"}
GROUP_LABELS = {"Non-University Higher Education Providers",
                "Private Universities and Non-University Higher Education Providers"}
GRAIN = ["institution_name", "field_name", "status", "country_of_origin", "year"]


def asced_fields():
    """field name -> 2-digit code, read from the CRICOS course register ("09 - Society and Culture")
    and checked against config/asced_broad_field_map.csv."""
    courses = pd.read_csv(c.raw_path(CRICOS_COURSES), dtype=str, keep_default_na=False)
    labels = pd.concat([courses["Field of Education 1 Broad Field"], courses["Field of Education 2 Broad Field"]])
    from_cricos = {}
    for label in labels[labels.str.strip() != ""].unique():
        m = re.fullmatch(r"(\d{2}) - (.+)", label.strip())
        if not m:
            raise SystemExit(f"Unexpected CRICOS broad-field label: {label!r}")
        from_cricos[m.group(2)] = m.group(1)
    fmap = c.load_config("asced_broad_field_map.csv")
    for _, r in fmap[fmap["field_code"] != ""].iterrows():
        if from_cricos.get(r["field_name"]) != r["field_code"]:
            raise SystemExit(f"config ASCED code {r['field_code']} {r['field_name']} disagrees with CRICOS")
    return fmap


def main():
    warnings = []
    df, declared = c.read_pivot_cache(c.raw_path(HESSC))
    raw_rows = len(df)

    count, num_stats = c.to_number(df["Enrolment Count"])
    raw_total = int(count.sum())

    # check: for single-field courses the primary field's own count column equals Enrolment Count
    single = df["Broad_Field_of_Education_Secondary"] == "Not a Combined Course"
    field_cols = {col[: -len(" Count")]: col for col in df.columns
                  if col.endswith(" Count") and col != "Enrolment Count"}
    own = pd.Series(pd.NA, index=df.index, dtype="Int64")
    for field, col in field_cols.items():
        sel = df["Broad_Field_of_Education_Primary"] == field
        own[sel] = c.to_number(df.loc[sel, col])[0]
    mismatch = int((single & own.notna() & (own != count)).sum())
    if mismatch:
        warnings.append(f"{mismatch} single-field records where the field count column differs from Enrolment Count")

    out = pd.DataFrame({
        "institution_name": c.clean_text(df["Institution"]),
        "field_name": c.clean_text(df["Broad_Field_of_Education_Primary"]),
        "status": df["Citizenship"].map(CITIZENSHIP),
        "country_of_origin": pd.Series(pd.NA, index=df.index, dtype="string"),
        "year": pd.to_numeric(df["Year"], errors="raise").astype("Int64"),
        "student_count": count,
    })
    if out["status"].isna().any():
        raise SystemExit(f"Unknown Citizenship values: {df.loc[out['status'].isna(), 'Citizenship'].unique()}")

    fmap = asced_fields()
    unknown_fields = sorted(set(out["field_name"].dropna()) - set(fmap["field_name"]))
    if unknown_fields:
        raise SystemExit(f"HESSC fields missing from config/asced_broad_field_map.csv: {unknown_fields}")
    out["field_code"] = out["field_name"].map(dict(zip(fmap["field_name"], fmap["field_code"]))).replace("", pd.NA)

    # --- quarantine: rows that cannot be loaded without an undocumented assumption ---------
    institutions = pd.read_csv(c.PROCESSED / "institutions.csv", dtype=str, keep_default_na=False)
    reason = pd.Series(pd.NA, index=out.index, dtype="string")
    reason[out["institution_name"].isin(GROUP_LABELS)] = (
        "HESSC group of many providers, not one institution; provider_type mixed")
    reason[reason.isna() & ~out["institution_name"].isin(institutions["name"])] = (
        "institution not in institutions.csv (not on CRICOS, provider_type unknown)")
    reason[reason.isna() & out["student_count"].isna()] = "student_count suppressed/missing; column is NOT NULL"
    out["source_file"] = HESSC

    q = out[reason.notna()].assign(reason=reason[reason.notna()])
    q_agg = (q.groupby(["reason", "institution_name", "field_name", "status", "year"], dropna=False)
             ["student_count"].sum(min_count=1).reset_index())
    q_agg["source_file"] = HESSC
    c.write_csv(q_agg, c.QUARANTINE / "enrollment_stats_quarantine.csv",
                sort_by=["reason", "institution_name", "year", "field_name", "status"])
    keep = out[reason.isna()]

    fact, agg = c.aggregate_grain(keep, GRAIN + ["field_code", "source_file"], ["student_count"])
    if fact["student_count"].isna().any():
        raise SystemExit("null student_count after aggregation")
    fact = fact[["institution_name", "field_name", "field_code", "status", "country_of_origin",
                 "year", "student_count", "source_file"]]
    rows = c.write_csv(fact, c.PROCESSED / "enrollment_stats.csv", sort_by=GRAIN)

    # reconciliation: nothing lost between raw and (loaded + quarantined)
    loaded_total, q_total = int(fact["student_count"].sum()), int(q["student_count"].sum())
    if loaded_total + q_total != raw_total:
        raise SystemExit(f"count reconciliation failed: {loaded_total}+{q_total} != {raw_total}")

    # --- dimensions --------------------------------------------------------------------
    used = sorted(set(fact["field_name"]) | set(q["field_name"].dropna()))
    fields = fmap[fmap["field_name"].isin(used)].rename(columns={"field_name": "name"})
    fields = fields.assign(field_code=fields["field_code"].replace("", pd.NA),
                           source_file=f"{HESSC};{CRICOS_COURSES}")[["name", "broad_field", "field_code", "source_file"]]
    c.write_csv(fields, c.PROCESSED / "fields_of_study.csv", sort_by=["field_code", "name"])
    if (fmap["status"] != "AGREED").any():
        warnings.append("fields_of_study.broad_field uses config/asced_broad_field_map.csv, status PROPOSED "
                        "-- needs team sign-off")

    cit = pd.DataFrame({"status": sorted(CITIZENSHIP.values()), "country_of_origin": pd.NA, "source_file": HESSC})
    c.write_csv(cit, c.PROCESSED / "citizenship_statuses.csv", sort_by=["status"])

    by_reason = q.groupby("reason")["student_count"].agg(["size", "sum"])
    q_by_year = q.groupby("year")["student_count"].sum().to_dict()
    tot_by_year = out.groupby("year")["student_count"].sum().to_dict()
    warnings.append("Quarantined enrolments by year (share of all HESSC enrolments): " + ", ".join(
        f"{y}: {int(q_by_year.get(y, 0)):,} ({q_by_year.get(y, 0) / tot_by_year[y]:.1%})" for y in sorted(tot_by_year)))
    warnings.append("country_of_origin is blank for every citizenship row: HESSC has no country dimension")

    common_meta = {
        "measure": "Enrolment Count (all-student headcount of course enrolments; commencing + continuing; not EFTSL)",
        "year_convention": "calendar year (HESSC reference year), 2020-2024",
    }
    c.write_report("enrollment_stats", {
        "output_file": "data/processed/enrollment_stats.csv",
        "target_table": "enrollment_stats",
        "source_files": [HESSC],
        "extraction": f"pivot cache via transform/extract_pivot_cache.py; {declared:,} records declared, {raw_rows:,} read",
        "raw_rows": raw_rows,
        "processed_rows": rows,
        "rows_removed": {f"quarantined: {k}": int(v) for k, v in by_reason["size"].items()},
        "rows_aggregated": agg["rows_collapsed_by_aggregation"],
        "aggregation_note": "HESSC records are finer than the grain (gender, level, attendance, commencing...); "
                            "they are summed to institution x field x citizenship x year",
        "duplicate_count_before": agg["duplicate_rows_at_grain_before"],
        "duplicate_groups_before": agg["duplicate_groups_at_grain_before"],
        "duplicate_count_after": agg["duplicate_rows_at_grain_after"],
        "suppressed_to_null": num_stats["suppressed_to_null"],
        "value_parsing": num_stats,
        "reconciliation": {"raw_enrolment_total": raw_total, "loaded_total": loaded_total,
                           "quarantined_total": q_total,
                           "quarantined_by_reason": {k: int(v) for k, v in by_reason["sum"].items()},
                           "single_field_count_mismatches": mismatch},
        "category_values": c.category_values(fact, ["institution_name", "field_name", "field_code", "status", "year"]),
        "warnings": warnings,
        **common_meta,
        "transformations": [
            "Citizenship Domestic -> domestic, Overseas -> international",
            "field = Broad_Field_of_Education_Primary; field_code from the CRICOS ASCED labels",
            "summed over gender, course level, attendance mode/type, commencing status, special course, state",
            "HESSC provider groups, institutions without provider_type, and null counts -> quarantine",
        ],
    })
    c.write_report("fields_of_study", {
        "output_file": "data/processed/fields_of_study.csv", "target_table": "fields_of_study",
        "source_files": [HESSC, CRICOS_COURSES], "raw_rows": len(fmap), "processed_rows": len(fields),
        "rows_removed": {"mapping rows not used by HESSC": len(fmap) - len(fields)}, "rows_aggregated": 0,
        "duplicate_count_before": 0, "duplicate_count_after": int(fields["name"].duplicated().sum()),
        "suppressed_to_null": 0,
        "category_values": c.category_values(fields, ["name", "broad_field", "field_code"]),
        "warnings": ["broad_field mapping is PROPOSED (config/asced_broad_field_map.csv); needs team sign-off"],
        "measure": "n/a (dimension)", "year_convention": "n/a",
        "transformations": ["ASCED broad field names from HESSC; codes from CRICOS; broad_field from config"],
    })
    c.write_report("citizenship_statuses", {
        "output_file": "data/processed/citizenship_statuses.csv", "target_table": "citizenship_statuses",
        "source_files": [HESSC], "raw_rows": 2, "processed_rows": len(cit), "rows_removed": {},
        "rows_aggregated": 0, "duplicate_count_before": 0, "duplicate_count_after": 0, "suppressed_to_null": 0,
        "category_values": c.category_values(cit, ["status"]),
        "warnings": ["country_of_origin blank: HESSC has no country dimension"],
        "measure": "n/a (dimension)", "year_convention": "n/a",
        "transformations": ["Domestic -> domestic, Overseas -> international"],
    })

    c.write_dictionary("enrollment_stats.csv", "enrollment_stats", [
        "Target table `enrollment_stats`. Grain: institution x field x citizenship x year (unique).",
        "The loader resolves `institution_name` -> institutions.name, `field_name` -> fields_of_study.name, "
        "(`status`, `country_of_origin`) -> citizenship_statuses, `source_file` -> data_sources.",
        "Excluded rows (provider groups, Batchelor, Carnegie Mellon) are in quarantine/enrollment_stats_quarantine.csv.",
    ], [
        ("institution_name", "Institution (load key)", "text <=255", "HESSC Institution", "-", "-"),
        ("field_name", "ASCED broad field of the primary course field (load key)", "text", "HESSC Broad_Field_of_Education_Primary", "-", "-"),
        ("field_code", "2-digit ASCED broad field code; blank for Non-Award / Not provided", "text '01'-'12'", "CRICOS ASCED labels", "-", "-"),
        ("status", "domestic or international", "text", "HESSC Citizenship: Domestic->domestic, Overseas->international", "-", "-"),
        ("country_of_origin", "Always blank (no country in HESSC)", "text, blank", "-", "-", "-"),
        ("year", "Reference year", "integer", "HESSC Year", "-", "calendar year"),
        ("student_count", "Course enrolments, all students", "integer >= 0, not null", "sum of HESSC Enrolment Count over the grain", "headcount enrolments (commencing + continuing); not EFTSL", "calendar year"),
        ("source_file", "MANIFEST.csv path", "text", "-", "-", "-"),
    ])
    c.write_dictionary("fields_of_study.csv", "fields_of_study", [
        "Target table `fields_of_study`. Load key: `name`. broad_field mapping is PROPOSED."], [
        ("name", "ASCED broad field name", "text <=255", "HESSC", "-", "-"),
        ("broad_field", "STEM, Social Studies or other", "text", "config/asced_broad_field_map.csv (PROPOSED)", "-", "-"),
        ("field_code", "2-digit ASCED broad field code", "text, nullable", "CRICOS course register labels", "-", "-"),
        ("source_file", "MANIFEST.csv path(s), ';'-separated", "text", "-", "-", "-"),
    ])
    c.write_dictionary("citizenship_statuses.csv", "citizenship_statuses", [
        "Target table `citizenship_statuses`. Load key: (`status`, `country_of_origin`)."], [
        ("status", "domestic or international", "text <=20", "HESSC Citizenship", "-", "-"),
        ("country_of_origin", "Blank (HESSC has no country)", "text <=100, nullable", "-", "-", "-"),
        ("source_file", "MANIFEST.csv path", "text", "-", "-", "-"),
    ])
    print(f"enrollment_stats.csv: {rows} rows; quarantined {len(q)} records ({q_total:,} enrolments)")


if __name__ == "__main__":
    main()
