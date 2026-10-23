"""Load data/processed/staging/*.csv into the visa, migration and PRISMS tables.

    python transform/load_staging.py        (load_db.py also runs it automatically)

Run it after transform/run_all.py and `alembic upgrade head`, and after load_db.py has
loaded data_sources: every staging row's source_file is looked up there to set
data_source_id.

    staging file                                  -> table
    visa_lodgements.csv                           -> visa_lodgements
    visa_grants.csv                               -> visa_grants
    visa_decisions.csv                            -> visa_decisions
    abs_nom_financial_year.csv                    -> migration_flows (period_type 'financial')
    abs_nom_calendar_year.csv                     -> migration_flows (period_type 'calendar')
    prisms_international_students_ytd.csv         -> intl_student_enrolments

The files hold 2-3.6 million rows each, so they are bulk-loaded with PostgreSQL COPY
rather than inserted row by row. Everything happens in one transaction: the tables are
emptied and reloaded, the summary views are refreshed, and every row count and total is
checked against the cleaning reports in data/processed/reports/. If anything fails or
does not reconcile, the transaction is rolled back and the previous data is untouched.
Re-running never duplicates rows.
"""

import csv
import json
import os
import pathlib
import re
import time

from sqlalchemy import create_engine

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
STAGING = PROCESSED / "staging"
REPORTS = PROCESSED / "reports"

VISA_COLUMNS = [
    "financial_year", "quarter", "month", "client_location", "lodgement_channel", "sector",
    "applicant_type", "provider_state", "gender", "age_group", "citizenship_country",
    "citizenship_country_source",
]
ABS_COLUMNS = [
    "visa_group_code", "visa_group", "migration_type_code", "migration_type",
    "region_code", "region", "persons", "is_aggregate",
]

# Each job: (staging file, target table, {target column: SQL expression over the CSV
# columns}). CSV columns arrive as text; blanks become NULL, never 0.
INT = "NULLIF({}, '')::integer"
BOOL = "NULLIF({}, '')::boolean"


def text_cols(names):
    return {c: f"NULLIF({c}, '')" for c in names}


def visa_job(name, extra_text, measures):
    cols = text_cols(VISA_COLUMNS + extra_text)
    cols["month"] = INT.format("month")
    for m in measures:
        cols[m] = INT.format(m)
    return (name, name, cols)


JOBS = [
    visa_job("visa_lodgements", [], ["lodged"]),
    visa_job("visa_grants", ["last_visa_category"], ["granted"]),
    visa_job("visa_decisions", [], ["granted", "refused"]),
    ("abs_nom_financial_year", "migration_flows", {
        "period_type": "'financial'", "period": "financial_year",
        **text_cols(ABS_COLUMNS), "persons": INT.format("persons"),
        "is_aggregate": BOOL.format("is_aggregate")}),
    ("abs_nom_calendar_year", "migration_flows", {
        "period_type": "'calendar'", "period": "calendar_year",
        **text_cols(ABS_COLUMNS), "persons": INT.format("persons"),
        "is_aggregate": BOOL.format("is_aggregate")}),
    ("prisms_international_students_ytd", "intl_student_enrolments", {
        "year": INT.format("year"), "month": INT.format("month"),
        **text_cols(["citizenship_country", "citizenship_country_source", "state", "sector",
                     "provider_type"]),
        "new_to_australia": BOOL.format("new_to_australia"),
        "ends_this_year": BOOL.format("ends_this_year"),
        "ytd_enrolments": INT.format("ytd_enrolments"),
        "ytd_commencements": INT.format("ytd_commencements")}),
]

TABLES = ["visa_lodgements", "visa_grants", "visa_decisions", "migration_flows",
          "intl_student_enrolments"]
SUMMARY_VIEWS = ["visa_lodgements_annual", "visa_grants_annual", "visa_decisions_annual",
                 "intl_students_annual"]


def source_columns(cols):
    """CSV columns a job reads: every identifier in its SQL expressions, minus SQL words
    and quoted literals, plus source_file."""
    words = set()
    for expr in cols.values():
        words |= set(re.findall(r"[a-z_]+", re.sub(r"'[^']*'", "", expr)))
    return (words - {"integer", "boolean"}) | {"source_file"}


def header(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def report(name):
    path = REPORTS / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_staging(engine):
    """Bulk-load every staging file. Returns {staging file: rows loaded}."""
    if not STAGING.exists():
        print(f"\nNo {STAGING.relative_to(ROOT)}/ folder: skipping visa, migration and PRISMS "
              "tables (run transform/run_all.py to create the staging files).")
        return {}
    missing = [f"{name}.csv" for name, _, _ in JOBS if not (STAGING / f"{name}.csv").exists()]
    if missing:
        raise SystemExit(f"Staging files missing, nothing loaded: {', '.join(missing)}")

    # Check every file has the columns this loader reads before touching the database.
    for name, _, cols in JOBS:
        absent = sorted(source_columns(cols) - set(header(STAGING / f"{name}.csv")))
        if absent:
            raise SystemExit(f"{name}.csv is missing columns {absent}; nothing loaded.")

    sources = {}
    with open(PROCESSED / "data_sources.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sources[row["source_file"]] = row["url"]

    counts = {}
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        # Map each raw file path to its data_sources.id (loaded earlier by load_db.py).
        cur.execute("CREATE TEMP TABLE source_map (source_file text PRIMARY KEY, "
                    "data_source_id integer) ON COMMIT DROP")
        cur.execute("SELECT url, id FROM data_sources")
        ids = dict(cur.fetchall())
        cur.executemany("INSERT INTO source_map VALUES (%s, %s)",
                        [(f, ids.get(url)) for f, url in sources.items()])

        cur.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY")

        for name, table, cols in JOBS:
            started = time.time()
            path = STAGING / f"{name}.csv"
            csv_cols = header(path)
            cur.execute(f"CREATE TEMP TABLE raw_{name} ("
                        + ", ".join(f'"{c}" text' for c in csv_cols) + ") ON COMMIT DROP")
            with open(path, encoding="utf-8") as f:
                cur.copy_expert(f"COPY raw_{name} FROM STDIN WITH (FORMAT csv, HEADER true)", f)

            cur.execute(f"SELECT count(*) FROM raw_{name} r LEFT JOIN source_map s "
                        "USING (source_file) WHERE s.data_source_id IS NULL")
            unmatched = cur.fetchone()[0]
            if unmatched:
                raise SystemExit(f"{name}.csv: {unmatched:,} rows have a source_file that is not "
                                 "in data_sources (run load_db.py first); nothing loaded.")

            targets = ", ".join(cols) + ", data_source_id"
            values = ", ".join(cols.values()) + ", s.data_source_id"
            cur.execute(f"INSERT INTO {table} ({targets}) SELECT {values} "
                        f"FROM raw_{name} JOIN source_map s USING (source_file)")
            counts[name] = cur.rowcount
            cur.execute(f"DROP TABLE raw_{name}")
            print(f"{table:24s} {counts[name]:10,d} rows  ({time.time() - started:.0f}s, "
                  f"from {name}.csv)")

        for view in SUMMARY_VIEWS:
            cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
            cur.execute(f"SELECT count(*) FROM {view}")
            print(f"{view:24s} {cur.fetchone()[0]:10,d} rows  (summary view)")

        reconcile(cur, counts)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return counts


def reconcile(cur, counts):
    """Compare loaded rows and totals with the cleaning reports; abort on any mismatch."""
    problems, checked = [], 0
    for name, table, cols in JOBS:
        rep = report(name)
        if "processed_rows" in rep:
            checked += 1
            if counts[name] != rep["processed_rows"]:
                problems.append(f"{name}: loaded {counts[name]:,} rows, report says "
                                f"{rep['processed_rows']:,}")
        for measure, expected in (rep.get("totals") or {}).items():
            checked += 1
            where = f" WHERE period_type = {cols['period_type']}" if table == "migration_flows" else ""
            cur.execute(f"SELECT COALESCE(SUM({measure}), 0) FROM {table}{where}")
            actual = cur.fetchone()[0]
            if actual != expected:
                problems.append(f"{name}: SUM({measure}) is {actual:,}, report says {expected:,}")
    if problems:
        raise SystemExit("Load does not match the cleaning reports, rolled back:\n  "
                         + "\n  ".join(problems))
    print(f"Reconciled with the cleaning reports: {checked} checks passed.")


def main():
    url = "postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("DB_USERNAME", "dashboard"),
        password=os.getenv("DB_PASSWORD", "dashboard"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", "dashboard"),
    )
    load_staging(create_engine(url))


if __name__ == "__main__":
    main()
