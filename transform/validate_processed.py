"""Validate everything in data/processed/ and write the cleaning report.

  data/processed/reports/cleaning_report.json   machine-readable: every check, every output
  data/processed/reports/cleaning_report.md     the same, readable

Checks
  A  raw vs processed row counts (from each cleaner's report)
  B  duplicates at each output's grain / load key
  C  categorical unique values; case/spacing variants of the same value fail
  D  suppression: markers never survive as text, nulls are not zeros (unit-tested helper)
  E  schema: columns, types, lengths, nullability, allowed values and unique constraints
     taken from models/models.py (allowed values parsed from the column comments)
  F  code integrity: leading zeroes, numeric measures, date formats, no 'nan'/'None'/'Unnamed'
  +  raw-layer integrity against MANIFEST.csv, provenance (source_file), FK integrity, and
     cross-source reconciliations

Exits 1 if any check fails.
"""

import importlib.util
import json
import re
import sys

import pandas as pd
from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint

import common as c

MODELS = c.ROOT / "models" / "models.py"

# Loadable outputs: models.py table, and how FK ids are replaced by natural keys
TARGETS = {
    "institutions.csv": ("institutions", {}, ["cricos_provider_code"], ["name"]),
    "fields_of_study.csv": ("fields_of_study", {}, [], ["name"]),
    "citizenship_statuses.csv": ("citizenship_statuses", {}, [], ["status", "country_of_origin"]),
    "enrollment_stats.csv": ("enrollment_stats", {
        "institution_id": ["institution_name"], "field_of_study_id": ["field_name", "field_code"],
        "citizenship_status_id": ["status", "country_of_origin"], "data_source_id": ["source_file"]}, [], None),
    "policies.csv": ("policies", {"data_source_id": ["source_file"]}, [], ["title", "source_url"]),
    "data_sources.csv": ("data_sources", {}, [], ["source_file"]),
}

# Staging outputs: measures (everything else, bar source_file, is the grain)
STAGING = {
    "staging/prisms_international_students_ytd.csv": ["ytd_enrolments", "ytd_commencements"],
    "staging/visa_lodgements.csv": ["lodged"],
    "staging/visa_grants.csv": ["granted"],
    "staging/visa_decisions.csv": ["granted", "refused"],
    "staging/abs_nom_financial_year.csv": ["persons"],
    "staging/abs_nom_calendar_year.csv": ["persons"],
}
NOT_GRAIN = {"source_file", "citizenship_country_source", "visa_group", "migration_type", "region", "is_aggregate"}
CODE_PATTERNS = {
    "field_code": r"\d{2}", "cricos_provider_code": r"\d{5}[A-Z]", "financial_year": r"\d{4}-\d{2}",
    "visa_group_code": r"\d{1,2}", "migration_type_code": r"[12]", "region_code": r"[1-8]|AUS",
    "effective_date": r"\d{4}-\d{2}-\d{2}", "retrieved_at": r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
    "quarter": r"Q[1-4]",
}
REPORT_NAME = {
    "institutions.csv": "institutions", "fields_of_study.csv": "fields_of_study",
    "citizenship_statuses.csv": "citizenship_statuses", "enrollment_stats.csv": "enrollment_stats",
    "policies.csv": "policies", "data_sources.csv": "data_sources",
    **{k: k.split("/")[1][:-4] for k in STAGING},
}


class Result:
    def __init__(self):
        self.failures, self.warnings, self.passed = [], [], []

    def check(self, ok, msg):
        (self.passed if ok else self.failures).append(msg)
        return ok


def load_models():
    spec = importlib.util.spec_from_file_location("project_models", MODELS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Base.metadata


def allowed_values():
    """{(table, column): {values}} from comments like  # 'public' | 'private'  in models.py."""
    out, table = {}, None
    for line in MODELS.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        t = re.search(r'__tablename__\s*=\s*"(\w+)"', line)
        if t:
            table = t.group(1)
        m = re.match(r"\s+(\w+): Mapped\[.*\]\s*=\s*mapped_column\(.*\)\s*#\s*(.+\|.+)$", line)
        if m and table:
            vals = {v.strip().strip("'\"") for v in m.group(2).split("|")}
            out[(table, m.group(1))] = {v.split(" ")[0] if v.startswith("other") else v for v in vals}
    return out


def expected_columns(table, fk_map, extra):
    cols = []
    for col in table.columns:
        if col.primary_key:
            continue
        cols += fk_map.get(col.name, [col.name])
    cols += extra
    if "source_file" not in cols:
        cols.append("source_file")
    return cols


def read(rel):
    return pd.read_csv(c.PROCESSED / rel, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")


def common_checks(rel, df, res, measures, manifest_files):
    """F + D + provenance + C, shared by every output."""
    res.check(not any(col.startswith("Unnamed") or col == "" for col in df.columns), f"{rel}: no index/Unnamed columns")
    bad_tokens = {"nan", "NaN", "None", "NULL", "null", "<NA>", "NaT"}
    hits = {col: int(df[col].isin(bad_tokens).sum()) for col in df.columns}
    hits = {k: v for k, v in hits.items() if v}
    res.check(not hits, f"{rel}: no 'nan'/'None'/'<NA>' strings written {hits or ''}")
    markers = {col: int(df[col].str.strip().str.lower().isin(c.SUPPRESSION_MARKERS).sum()) for col in measures}
    markers = {k: v for k, v in markers.items() if v}
    res.check(not markers, f"{rel}: no suppression markers left in measure columns {markers or ''}")
    for col in measures:
        vals = df[col].dropna()
        res.check(vals.str.fullmatch(r"\d+").all(), f"{rel}: {col} is a non-negative integer where present")
    for col, pat in CODE_PATTERNS.items():
        if col in df.columns:
            v = df[col].dropna()
            res.check(v.str.fullmatch(pat).all(), f"{rel}: {col} matches {pat} (text codes intact)")
    if "financial_year" in df.columns:
        fy = df["financial_year"].dropna().drop_duplicates()
        ok = fy.map(lambda s: (int(s[:4]) + 1) % 100 == int(s[5:])).all()
        res.check(ok, f"{rel}: financial_year labels are consecutive years")
    if "source_file" in df.columns:
        parts = set(p for v in df["source_file"].dropna().unique() for p in v.split(";"))
        res.check(df["source_file"].notna().all() and parts <= manifest_files,
                  f"{rel}: every row has source_file and every path is in MANIFEST.csv")
    else:
        res.check(False, f"{rel}: source_file column present")
    # C: case/spacing variants
    variants = {}
    for col in df.columns:
        if col in measures or col == "source_file":
            continue
        u = df[col].dropna().unique()
        if len(u) > 400:
            continue
        norm = pd.Series(u).str.lower().str.replace(r"[\s_\-]+", " ", regex=True).str.strip()
        clash = pd.Series(u)[norm.duplicated(keep=False)].tolist()
        if clash:
            variants[col] = clash
    res.check(not variants, f"{rel}: no case/spacing variants of the same category {variants or ''}")


def schema_checks(rel, df, table, fk_map, extra, key, metadata, allowed, res):
    exp = expected_columns(table, fk_map, extra)
    res.check(list(df.columns) == exp, f"{rel}: columns == {exp}" + ("" if list(df.columns) == exp else f" (got {list(df.columns)})"))
    for col in table.columns:
        if col.primary_key:
            continue
        names = fk_map.get(col.name, [col.name])
        if col.name == "data_source_id":
            continue                                    # source_file handled in common_checks
        first = names[0]
        if first not in df.columns:
            continue
        s = df[first]
        if not col.nullable and col.name != "citizenship_status_id":
            res.check(s.notna().all(), f"{rel}: {first} has no nulls (NOT NULL in {table.name}.{col.name})")
        if col.foreign_keys:
            continue
        v = s.dropna()
        t = col.type
        if isinstance(t, String) and t.length:
            res.check((v.str.len() <= t.length).all(), f"{rel}: {first} <= {t.length} chars (max {int(v.str.len().max()) if len(v) else 0})")
        elif isinstance(t, Integer):
            res.check(v.str.fullmatch(r"-?\d+").all(), f"{rel}: {first} is integer")
        elif isinstance(t, DateTime):
            res.check(v.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}").all(), f"{rel}: {first} is a datetime")
        elif isinstance(t, Date):
            res.check(v.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all() and pd.to_datetime(v, format="%Y-%m-%d", errors="coerce").notna().all(),
                      f"{rel}: {first} is a YYYY-MM-DD date")
        elif isinstance(t, Text):
            pass
        if (table.name, col.name) in allowed:
            vals = set(v.unique())
            ok = vals <= allowed[(table.name, col.name)]
            res.check(ok, f"{rel}: {first} values {sorted(vals)} within models.py {sorted(allowed[(table.name, col.name)])}")
    # unique constraints translated to natural keys
    for con in table.constraints:
        if isinstance(con, UniqueConstraint):
            cols = []
            for cc in con.columns:
                cols += [x for x in fk_map.get(cc.name, [cc.name]) if x != "field_code"]
            n = int(df.duplicated(cols).sum())
            res.check(n == 0, f"{rel}: unique constraint {con.name} on {cols}: {n} duplicates")
    if key:
        n = int(df.duplicated(key).sum())
        res.check(n == 0, f"{rel}: load key {key} unique: {n} duplicates")


def test_suppression_helper(res):
    raw = pd.Series(["<5", "np", "-", "..", "*", "0", "1,234", "", None, "12"], name="t")
    got, stats = c.to_number(raw)
    expected = [None, None, None, None, None, 0, 1234, None, None, 12]
    ok = all((pd.isna(g) and e is None) or g == e for g, e in zip(got, expected))
    res.check(ok and stats["suppressed_to_null"] == 5 and stats["explicit_zeros"] == 1,
              "to_number: <5/np/-/../* -> null, '0' -> 0, '1,234' -> 1234 (never marker -> 0)")


def main():
    res = Result()
    outputs = {}

    # raw layer integrity
    m = c.manifest()
    manifest_files = set(m["file"])
    integrity = {}
    for f in m["file"]:
        try:
            c.raw_path(f)
            integrity[f] = "ok"
        except c.ManifestMismatch as e:
            integrity[f] = str(e)
    res.check(all(v == "ok" for v in integrity.values()),
              f"raw layer: {sum(v == 'ok' for v in integrity.values())}/{len(integrity)} MANIFEST files match sha256")
    on_disk = {p.relative_to(c.DATA).as_posix() for p in c.RAW.rglob("*") if p.is_file()}
    unlisted = sorted(on_disk - manifest_files)
    if unlisted:
        res.warnings.append(f"raw layer has {len(unlisted)} files not in MANIFEST.csv (not used): {unlisted}")

    test_suppression_helper(res)
    metadata = load_models()
    allowed = allowed_values()
    res.check(bool(allowed), f"models.py allowed values parsed: { {f'{k[0]}.{k[1]}': sorted(v) for k, v in allowed.items()} }")

    frames = {}
    for rel, (tname, fk_map, extra, key) in TARGETS.items():
        df = read(rel)
        frames[rel] = df
        measures = ["student_count"] if rel == "enrollment_stats.csv" else []
        common_checks(rel, df, res, measures, manifest_files)
        schema_checks(rel, df, metadata.tables[tname], fk_map, extra, key, metadata, allowed, res)
        outputs[rel] = df

    # FK integrity on natural keys
    es, inst = frames["enrollment_stats.csv"], frames["institutions.csv"]
    fos, cit = frames["fields_of_study.csv"], frames["citizenship_statuses.csv"]
    res.check(es["institution_name"].isin(inst["name"]).all(), "enrollment_stats: every institution_name exists in institutions.csv")
    pairs = set(zip(fos["name"], fos["field_code"].fillna("")))
    res.check(set(zip(es["field_name"], es["field_code"].fillna(""))) <= pairs,
              "enrollment_stats: every (field_name, field_code) exists in fields_of_study.csv")
    cit_keys = set(zip(cit["status"], cit["country_of_origin"].fillna("")))
    res.check(set(zip(es["status"], es["country_of_origin"].fillna(""))) <= cit_keys,
              "enrollment_stats: every citizenship key exists in citizenship_statuses.csv")
    ds = set(frames["data_sources.csv"]["source_file"])
    for rel, df in frames.items():
        if rel != "data_sources.csv":
            parts = set(p for v in df["source_file"].unique() for p in v.split(";"))
            res.check(parts <= ds, f"{rel}: every source_file resolves to a data_sources.csv row")

    # staging
    for rel, measures in STAGING.items():
        df = read(rel)
        common_checks(rel, df, res, measures, manifest_files)
        grain = [col for col in df.columns if col not in measures and col not in NOT_GRAIN]
        n = int(df.duplicated(grain).sum())
        res.check(n == 0, f"{rel}: grain {grain} unique: {n} duplicates")
        outputs[rel] = df
        if rel.endswith("visa_grants.csv") or rel.endswith("visa_decisions.csv"):
            frames[rel] = df[["financial_year", "granted"]]

    # cross-source reconciliations
    g = frames["staging/visa_grants.csv"].assign(granted=lambda d: d["granted"].astype("Int64")).groupby("financial_year")["granted"].sum()
    d = frames["staging/visa_decisions.csv"].assign(granted=lambda d: d["granted"].astype("Int64")).groupby("financial_year")["granted"].sum()
    common_fy = g.index.intersection(d.index)
    diff = (g[common_fy] - d[common_fy]).abs()
    res.check(int(diff.sum()) == 0, f"visas: granted by financial year agrees between grants and decisions workbooks ({len(common_fy)} years)")

    # per-output reports
    reports = {}
    for rel in outputs:
        p = c.REPORTS / f"{REPORT_NAME[rel]}.json"
        reports[rel] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        if reports[rel] is None:
            res.check(False, f"{rel}: cleaner report missing")
            continue
        r = reports[rel]
        res.check(r["processed_rows"] == len(outputs[rel]), f"{rel}: report row count matches file ({len(outputs[rel]):,})")
        res.check(r.get("duplicate_count_after", 0) == 0, f"{rel}: duplicates after cleaning = 0")
        for f in r.get("validation_failures", []):
            res.check(False, f"{rel}: {f}")
        for w in r.get("warnings", []):
            res.warnings.append(f"{rel}: {w}")
        r["category_values"] = c.category_values(
            outputs[rel], [col for col in outputs[rel].columns
                           if col not in STAGING.get(rel, []) + ["student_count", "source_file", "full_text", "title",
                                                                 "name", "url", "source_url", "citizenship_country_source"]
                           and outputs[rel][col].nunique() <= 400])
    rec = reports["enrollment_stats.csv"]["reconciliation"]
    res.check(rec["loaded_total"] + rec["quarantined_total"] == rec["raw_enrolment_total"],
              f"enrollment_stats: loaded {rec['loaded_total']:,} + quarantined {rec['quarantined_total']:,} == raw {rec['raw_enrolment_total']:,}")
    pr = reports["staging/prisms_international_students_ytd.csv"]["published_reconciliation"]
    res.check(all(v["published"] == v["processed"] for v in pr.values()),
              f"PRISMS: {len(pr)} published YTD-May sector totals reproduced exactly")

    summary = {
        "status": "PASS" if not res.failures else "FAIL",
        "schema": {"file": "models/models.py", "origin": (c.ROOT / "models" / "SOURCE.md").read_text(encoding="utf-8").strip()
                   if (c.ROOT / "models" / "SOURCE.md").exists() else None},
        "raw_integrity": integrity,
        "checks_passed": len(res.passed), "checks_failed": len(res.failures),
        "failures": res.failures, "warnings": res.warnings, "passed": res.passed,
        "outputs": reports,
    }
    c.REPORTS.mkdir(parents=True, exist_ok=True)
    (c.REPORTS / "cleaning_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_markdown(summary)
    print(f"{summary['status']}: {len(res.passed)} checks passed, {len(res.failures)} failed, {len(res.warnings)} warnings")
    for f in res.failures:
        print("  FAIL", f)
    return 0 if not res.failures else 1


def write_markdown(s):
    L = [f"# Cleaning report -- {s['status']}", "",
         f"{s['checks_passed']} checks passed, {s['checks_failed']} failed. Schema: `models/models.py`"
         + (f" ({s['schema']['origin']})" if s["schema"]["origin"] else "") + ".", "",
         "## Row reconciliation", "",
         "| Output | Target table | Source file(s) | Raw rows | Processed rows | Removed | Aggregated away | Dup before | Dup after | Suppressed->null | Measure | Year convention |",
         "|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---|"]
    for rel, r in s["outputs"].items():
        if not r:
            continue
        removed = "; ".join(f"{k}: {v:,}" for k, v in r["rows_removed"].items()) or "0"
        L.append(f"| `{rel}` | {r.get('target_table') or 'staging (none)'} | {'<br>'.join(r['source_files'])} | "
                 f"{r['raw_rows']:,} | {r['processed_rows']:,} | {removed} | {r['rows_aggregated']:,} | "
                 f"{r['duplicate_count_before']:,} | {r['duplicate_count_after']:,} | {r['suppressed_to_null']:,} | "
                 f"{r['measure']} | {r['year_convention']} |")
    L += ["", "## Failures", ""] + ([f"- {f}" for f in s["failures"]] or ["None."])
    L += ["", "## Warnings", ""] + [f"- {w}" for w in s["warnings"]]
    L += ["", "## Transformations", ""]
    for rel, r in s["outputs"].items():
        if r:
            L.append(f"- `{rel}`: " + "; ".join(r.get("transformations", [])))
    L += ["", "## Category values", ""]
    for rel, r in s["outputs"].items():
        if r:
            for col, vals in r["category_values"].items():
                shown = ", ".join(vals[:25]) + (f" ... ({len(vals)} values)" if len(vals) > 25 else "")
                L.append(f"- `{rel}` **{col}**: {shown}")
    L += ["", "## Raw layer integrity", ""] + [f"- `{k}`: {v}" for k, v in s["raw_integrity"].items()]
    L += ["", "## Checks passed", ""] + [f"- {p}" for p in s["passed"]]
    (c.REPORTS / "cleaning_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
