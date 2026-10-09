"""Load data/processed/*.csv into the database defined by models/models.py.

    python transform/load_db.py

Run it after transform/run_all.py and `make migration_head`. It connects with the same
DB_* variables as docker-compose; DB_HOST defaults to localhost because this runs on the
host against the published Postgres port, not inside the api container.

Every row is matched on its natural key, never on a CSV row number, so re-running updates
rows in place instead of duplicating them:
  data_sources          url
  institutions          name
  fields_of_study       name           (two fields have no ASCED code)
  citizenship_statuses  status + country_of_origin
  policies              title + source_url   (138 policies share 121 titles, so title alone collides)
  enrollment_stats      institution + field + citizenship + year  (uq_enrollment_grain)
Foreign keys are looked up from those keys; source_file in each CSV resolves data_source_id.
"""

import os
import pathlib
import sys
from datetime import date, datetime

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

sys.path.insert(0, str(ROOT / "models"))
from models import (  # noqa: E402
    CitizenshipStatus, DataSource, EnrollmentStat, FieldOfStudy, Institution, Policy,
)


def read(name):
    """A processed CSV as a list of dicts, with blanks as None (blank = unknown, never 0)."""
    df = pd.read_csv(PROCESSED / f"{name}.csv", dtype=str, keep_default_na=False)
    return [{k: (v if v != "" else None) for k, v in row.items()} for row in df.to_dict("records")]


def upsert(session, model, rows, key):
    """Insert or update rows matched on the key columns. Returns {key tuple: id}."""
    existing = {tuple(getattr(o, k) for k in key): o for o in session.scalars(select(model))}
    for row in rows:
        obj = existing.get(tuple(row[k] for k in key))
        if obj is None:
            obj = model()
            session.add(obj)
            existing[tuple(row[k] for k in key)] = obj
        for col, val in row.items():
            setattr(obj, col, val)
    session.flush()
    return {k: o.id for k, o in existing.items()}


def load(engine):
    counts = {}
    with Session(engine) as session, session.begin():
        ds_rows = read("data_sources")
        ds = upsert(session, DataSource, [
            {"name": r["name"], "source_type": r["source_type"], "url": r["url"],
             "retrieved_at": datetime.fromisoformat(r["retrieved_at"]),
             "license_notes": r["license_notes"]} for r in ds_rows], ["url"])
        source_id = {r["source_file"]: ds[(r["url"],)] for r in ds_rows}
        counts["data_sources"] = len(ds_rows)

        rows = read("institutions")
        inst = upsert(session, Institution, [
            {c: r[c] for c in ("name", "provider_type", "state", "sector", "teqsa_id")}
            for r in rows], ["name"])
        counts["institutions"] = len(rows)

        rows = read("fields_of_study")
        field = upsert(session, FieldOfStudy, [
            {c: r[c] for c in ("name", "broad_field", "field_code")} for r in rows], ["name"])
        counts["fields_of_study"] = len(rows)

        rows = read("citizenship_statuses")
        cit = upsert(session, CitizenshipStatus, [
            {c: r[c] for c in ("status", "country_of_origin")} for r in rows],
            ["status", "country_of_origin"])
        counts["citizenship_statuses"] = len(rows)

        rows = read("policies")
        upsert(session, Policy, [
            {"title": r["title"], "category": r["category"], "summary": r["summary"],
             "full_text": r["full_text"],
             "effective_date": date.fromisoformat(r["effective_date"]) if r["effective_date"] else None,
             "source_url": r["source_url"], "data_source_id": source_id[r["source_file"]]}
            for r in rows], ["title", "source_url"])
        counts["policies"] = len(rows)

        rows = read("enrollment_stats")
        upsert(session, EnrollmentStat, [
            {"institution_id": inst[(r["institution_name"],)],
             "field_of_study_id": field[(r["field_name"],)],
             "citizenship_status_id": cit[(r["status"], r["country_of_origin"])],
             "year": int(r["year"]), "student_count": int(r["student_count"]),
             "data_source_id": source_id[r["source_file"]]}
            for r in rows], ["institution_id", "field_of_study_id", "citizenship_status_id", "year"])
        counts["enrollment_stats"] = len(rows)
    return counts


def main():
    url = "postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("DB_USERNAME", "dashboard"),
        password=os.getenv("DB_PASSWORD", "dashboard"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", "dashboard"),
    )
    for table, n in load(create_engine(url)).items():
        print(f"{table:22s} {n:6,d} rows")


if __name__ == "__main__":
    main()
