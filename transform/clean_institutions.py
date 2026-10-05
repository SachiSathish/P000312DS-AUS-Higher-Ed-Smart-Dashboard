"""Build data/processed/institutions.csv (target table: institutions).

Scope: higher-education providers only (models.Institution is "A higher education provider").
  1. The universities HESSC reports individually, matched to CRICOS through
     config/institution_crosswalk.csv (provider code, not fuzzy names).
  2. Every other CRICOS provider that offers at least one higher-education award course.

Rule for (2): a provider is in scope if any of its CRICOS courses has a Course Level that only
higher-education providers can award: Associate Degree, Bachelor Degree, Bachelor Honours Degree,
Masters Degree (Coursework / Research / Extended), Doctoral Degree. Diplomas, Advanced Diplomas,
Graduate Certificates and Graduate Diplomas are excluded from the test because VET providers can
also offer them.

provider_type: CRICOS "Institution Type"  Government -> public, Private -> private.
state:         CRICOS "Postal Address State" (the registered postal address, not campus).
sector, teqsa_id: left blank -- no source in the repository provides them.
"""

import zipfile

import pandas as pd

import common as c

HESSC = "bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx"
CRICOS_INST = "bronze/cricos-register/cricos_institutions_asat-2026-08-09.csv"
CRICOS_COURSES = "bronze/cricos-register/cricos_courses_asat-2026-08-09.csv"
OUT = c.PROCESSED / "institutions.csv"

HE_LEVELS = {
    "Associate Degree", "Bachelor Degree", "Bachelor Honours Degree", "Masters Degree (Coursework)",
    "Masters Degree (Research)", "Masters Degree (Extended)", "Doctoral Degree",
}
PROVIDER_TYPE = {"Government": "public", "Private": "private"}
# HESSC groups that are not a single institution; handled as quarantine in clean_enrolments.py
HESSC_GROUPS = {"Non-University Higher Education Providers",
                "Private Universities and Non-University Higher Education Providers"}
COLUMNS = ["name", "provider_type", "state", "sector", "teqsa_id", "cricos_provider_code", "source_file"]


def main():
    warnings, removed = [], {}

    # HESSC institution labels straight from the pivot-cache definition (no record scan needed)
    zf = zipfile.ZipFile(c.raw_path(HESSC))
    names, shared, _ = c.epc.read_fields(zf, c.epc.cache_parts(zf)[0])
    hessc_names = [n for n in shared[names.index("Institution")] if n]

    inst_raw = pd.read_csv(c.raw_path(CRICOS_INST), dtype=str, keep_default_na=False)
    raw_rows = len(inst_raw)
    blank = (inst_raw.apply(lambda col: col.str.strip()) == "").all(axis=1)
    removed["blank_trailing_rows"] = int(blank.sum())
    inst = inst_raw[~blank].copy()
    for col in inst.columns:
        inst[col] = c.clean_text(inst[col])
    exact_dupes = inst.duplicated()
    removed["exact_duplicate_rows"] = int(exact_dupes.sum())
    inst = inst[~exact_dupes]
    if inst["CRICOS Provider Code"].duplicated().any():
        raise SystemExit(f"Conflicting CRICOS rows for codes: "
                         f"{inst.loc[inst['CRICOS Provider Code'].duplicated(), 'CRICOS Provider Code'].tolist()}")
    bad_codes = inst[~inst["CRICOS Provider Code"].str.fullmatch(r"\d{5}[A-Z]")]
    if len(bad_codes):
        raise SystemExit(f"Malformed CRICOS provider codes: {bad_codes['CRICOS Provider Code'].tolist()}")
    inst = inst.set_index("CRICOS Provider Code", drop=False)

    courses = pd.read_csv(c.raw_path(CRICOS_COURSES), dtype=str, keep_default_na=False)
    he_codes = set(courses.loc[courses["Course Level"].str.strip().isin(HE_LEVELS), "CRICOS Provider Code"])

    # --- 1. HESSC universities via the crosswalk ------------------------------------------
    xw = c.load_config("institution_crosswalk.csv")
    missing = sorted(set(hessc_names) - HESSC_GROUPS - set(xw["hessc_name"]))
    if missing:
        raise SystemExit(f"HESSC institutions missing from config/institution_crosswalk.csv: {missing}")
    matched = xw[xw["cricos_provider_code"] != ""].copy()
    unknown = sorted(set(matched["cricos_provider_code"]) - set(inst.index))
    if unknown:
        raise SystemExit(f"Crosswalk codes not on the CRICOS register: {unknown}")
    hessc_rows = pd.DataFrame({
        "name": matched["hessc_name"].values,
        "cricos_provider_code": matched["cricos_provider_code"].values,
        "source_file": f"{HESSC};{CRICOS_INST}",
    })
    unmatched = xw.loc[xw["cricos_provider_code"] == "", "hessc_name"].tolist()
    for n in unmatched:
        warnings.append(f"HESSC institution '{n}' is not on CRICOS: provider_type unknown, "
                        f"not loaded (its enrolments go to quarantine)")

    # --- 2. other CRICOS higher-education providers ---------------------------------------
    crosswalked_names = set(inst.loc[matched["cricos_provider_code"], "Institution Name"])
    others = inst[inst.index.isin(he_codes) & ~inst.index.isin(matched["cricos_provider_code"])]
    secondary = others["Institution Name"].isin(crosswalked_names)
    removed["cricos_secondary_registrations_of_listed_universities"] = int(secondary.sum())
    others = others[~secondary]
    cricos_rows = pd.DataFrame({
        "name": others["Institution Name"].values,
        "cricos_provider_code": others.index.values,
        "source_file": f"{CRICOS_INST};{CRICOS_COURSES}",
    })
    removed["cricos_not_higher_education"] = int((~inst.index.isin(he_codes)
                                                  & ~inst.index.isin(matched["cricos_provider_code"])).sum())

    df = pd.concat([hessc_rows, cricos_rows], ignore_index=True)
    attrs = inst.loc[df["cricos_provider_code"]]
    df["provider_type"] = attrs["Institution Type"].map(PROVIDER_TYPE).values
    df["state"] = attrs["Postal Address State"].values
    df["sector"] = pd.NA
    df["teqsa_id"] = pd.NA

    no_type = df["provider_type"].isna()
    if no_type.any():
        q = df[no_type].assign(reason="CRICOS Institution Type blank: provider_type cannot be set")
        c.write_csv(q, c.QUARANTINE / "institutions_quarantine.csv", sort_by=["name"])
        warnings.append(f"{int(no_type.sum())} CRICOS providers have no Institution Type; quarantined")
    removed["quarantined_no_provider_type"] = int(no_type.sum())
    df = df[~no_type]

    dup_names = df[df["name"].duplicated(keep=False)]
    if len(dup_names):
        q = dup_names.assign(reason="Institution name shared by several CRICOS providers: "
                                    "name is the load key, so these need a team decision")
        c.write_csv(q, c.QUARANTINE / "institutions_name_collisions.csv", sort_by=["name", "cricos_provider_code"])
        warnings.append(f"{dup_names['name'].nunique()} names shared by {len(dup_names)} CRICOS providers; "
                        f"quarantined (see quarantine/institutions_name_collisions.csv)")
    removed["quarantined_name_collisions"] = len(dup_names)
    df = df[~df["name"].duplicated(keep=False)]

    too_long = df["name"].str.len() > 255
    if too_long.any():
        raise SystemExit(f"Institution names over 255 chars: {df.loc[too_long, 'name'].tolist()}")

    df = df[COLUMNS]
    rows = c.write_csv(df, OUT, sort_by=["name"])

    c.write_report("institutions", {
        "output_file": "data/processed/institutions.csv",
        "target_table": "institutions",
        "source_files": [HESSC, CRICOS_INST, CRICOS_COURSES],
        "raw_rows": raw_rows,
        "raw_rows_note": "rows in the CRICOS institutions CSV; plus HESSC institution labels",
        "hessc_institution_labels": len(hessc_names),
        "processed_rows": rows,
        "rows_removed": removed,
        "rows_aggregated": 0,
        "duplicate_count_before": removed["exact_duplicate_rows"],
        "duplicate_count_after": int(df["name"].duplicated().sum()),
        "suppressed_to_null": 0,
        "scope": {
            "rule": "HESSC universities + CRICOS providers with >=1 course at an HE-only AQF level",
            "he_only_levels": sorted(HE_LEVELS),
            "cricos_providers": int(len(inst)),
            "cricos_providers_in_he_scope": int(inst.index.isin(he_codes).sum()),
        },
        "category_values": c.category_values(df, ["provider_type", "state", "sector"]),
        "provider_type_counts": df["provider_type"].value_counts().to_dict(),
        "warnings": warnings + ["teqsa_id is blank for every row: TEQSA register not collected",
                                "sector is blank for every row: no source distinguishes university / TAFE / other"],
        "measure": "n/a (dimension table)",
        "year_convention": "n/a; CRICOS register as at 2026-08-09",
        "transformations": [
            "CRICOS Government -> public, Private -> private",
            "HESSC names kept as the canonical name for the universities HESSC lists",
            "CRICOS registrations sharing a crosswalked university's CRICOS name dropped as secondary registrations",
            "whitespace trimmed/collapsed; codes kept as text",
        ],
    })
    c.write_dictionary("institutions.csv", "institutions", [
        "Target table `institutions`. Load key: `name` (the loader assigns `id`).",
        "Scope: higher-education providers only -- see the rule in transform/clean_institutions.py.",
    ], [
        ("name", "Institution name (HESSC spelling for HESSC universities, CRICOS spelling otherwise)", "text <=255", "HESSC Institution / CRICOS Institution Name, whitespace collapsed", "-", "-"),
        ("provider_type", "public or private", "text: public|private", "CRICOS Institution Type: Government->public, Private->private", "-", "-"),
        ("state", "State of the registered postal address", "text <=10, nullable", "CRICOS Postal Address State", "-", "as at 2026-08-09"),
        ("sector", "Provider sector", "text, blank", "No source available", "-", "-"),
        ("teqsa_id", "TEQSA provider ID", "text, blank", "TEQSA register not collected", "-", "-"),
        ("cricos_provider_code", "CRICOS provider code (natural key for joins; not a models.py column)", "text, 5 digits + letter", "CRICOS Provider Code; HESSC rows via config/institution_crosswalk.csv", "-", "-"),
        ("source_file", "MANIFEST.csv path(s) the row came from, ';'-separated", "text", "-", "-", "-"),
    ])
    print(f"institutions.csv: {rows} rows")


if __name__ == "__main__":
    main()
