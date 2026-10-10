import os
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from models.models import (
    Institution,
    FieldOfStudy,
    CitizenshipStatus,
    EnrollmentStat,
    Policy,
    DataSource,
)


# --------------------------------------------------
# Database configuration
# --------------------------------------------------

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@db:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

app = FastAPI(
    title="AUS Higher Ed Smart Dashboard API",
    version="1.0.0",
)


# --------------------------------------------------
# Database session dependency
# --------------------------------------------------

def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=1000)]
Offset = Annotated[int, Query(ge=0)]


# --------------------------------------------------
# Pydantic response models
# --------------------------------------------------

class DatabaseHealth(BaseModel):
    database: Literal["ok"]


class TableCount(BaseModel):
    table: str
    row_count: int


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    state: str | None
    sector: str | None
    teqsa_id: str | None


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    broad_field: str
    field_code: str | None


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    summary: str | None
    full_text: str | None
    effective_date: date | None
    source_url: str | None
    data_source_id: int | None


class DataSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    url: str | None
    retrieved_at: datetime
    license_notes: str | None


class GroupBy(str, Enum):
    citizenship = "citizenship"
    broad_field = "broad_field"
    provider_type = "provider_type"


class EnrollmentSummaryOut(BaseModel):
    year: int
    group: str
    student_count: int


# --------------------------------------------------
# Error handling
# --------------------------------------------------

def query_or_503(action):
    try:
        return action()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable or query failed",
        ) from exc


def not_found(rows):
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No matching records found",
        )
    return rows


# --------------------------------------------------
# 1. Database health
# --------------------------------------------------

@app.get("/health/db", response_model=DatabaseHealth)
def health_db(db: DB):

    def run():
        db.execute(text("SELECT 1"))
        return DatabaseHealth(database="ok")

    return query_or_503(run)


# --------------------------------------------------
# 2. Tables and row counts
# --------------------------------------------------

@app.get("/tables", response_model=list[TableCount])
def tables(db: DB):

    def run():
        from sqlalchemy import MetaData, Table

        names = sorted(
            inspect(db.get_bind()).get_table_names(schema="public")
        )

        results = []

        for name in names:
            table = Table(
                name,
                MetaData(),
                schema="public",
                autoload_with=db.get_bind(),
            )

            count = db.scalar(
                select(func.count()).select_from(table)
            )

            results.append(
                TableCount(
                    table=name,
                    row_count=count or 0,
                )
            )

        return not_found(results)

    return query_or_503(run)


# --------------------------------------------------
# 3. Institutions
# --------------------------------------------------

@app.get("/institutions", response_model=list[InstitutionOut])
def institutions(
    db: DB,
    provider_type: str | None = None,
    state: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
):

    def run():
        stmt = select(Institution)

        if provider_type is not None:
            stmt = stmt.where(
                Institution.provider_type == provider_type
            )

        if state is not None:
            stmt = stmt.where(
                Institution.state == state
            )

        rows = db.scalars(
            stmt.order_by(Institution.id)
            .limit(limit)
            .offset(offset)
        ).all()

        return not_found(rows)

    return query_or_503(run)


# --------------------------------------------------
# 4. Fields of study
# --------------------------------------------------

@app.get("/fields-of-study", response_model=list[FieldOut])
def fields_of_study(
    db: DB,
    limit: Limit = 100,
    offset: Offset = 0,
):

    def run():
        stmt = (
            select(FieldOfStudy)
            .order_by(FieldOfStudy.id)
            .limit(limit)
            .offset(offset)
        )

        rows = db.scalars(stmt).all()

        return not_found(rows)

    return query_or_503(run)


# --------------------------------------------------
# 5. Enrolment summary
# --------------------------------------------------

@app.get(
    "/enrolments/summary",
    response_model=list[EnrollmentSummaryOut],
    description=(
        "Student enrolment totals by year and selected group. "
        "Grouped HESSC providers are expected to be excluded "
        "by the upstream cleaning pipeline."
    ),
)
def enrolments_summary(
    db: DB,
    group_by: GroupBy = GroupBy.citizenship,
    year: int | None = Query(default=None, ge=1900, le=2200),
    limit: Limit = 100,
    offset: Offset = 0,
):

    def run():
        dimension = {
            GroupBy.citizenship: CitizenshipStatus.status,
            GroupBy.broad_field: FieldOfStudy.broad_field,
            GroupBy.provider_type: Institution.provider_type,
        }[group_by]

        stmt = (
            select(
                EnrollmentStat.year.label("year"),
                dimension.label("group"),
                func.sum(
                    EnrollmentStat.student_count
                ).label("student_count"),
            )
            .join(
                Institution,
                EnrollmentStat.institution_id == Institution.id,
            )
            .join(
                FieldOfStudy,
                EnrollmentStat.field_of_study_id == FieldOfStudy.id,
            )
            .join(
                CitizenshipStatus,
                EnrollmentStat.citizenship_status_id
                == CitizenshipStatus.id,
            )
        )

        if year is not None:
            stmt = stmt.where(
                EnrollmentStat.year == year
            )

        stmt = (
            stmt.group_by(
                EnrollmentStat.year,
                dimension,
            )
            .order_by(
                EnrollmentStat.year,
                dimension,
            )
            .limit(limit)
            .offset(offset)
        )

        rows = [
            EnrollmentSummaryOut(
                year=row.year,
                group=row.group,
                student_count=int(row.student_count),
            )
            for row in db.execute(stmt).all()
        ]

        return not_found(rows)

    return query_or_503(run)


# --------------------------------------------------
# 6. Policies
# --------------------------------------------------

@app.get("/policies", response_model=list[PolicyOut])
def policies(
    db: DB,
    category: str | None = None,
    q: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
):

    def run():
        stmt = select(Policy)

        if category is not None:
            stmt = stmt.where(
                Policy.category == category
            )

        if q is not None:
            stmt = stmt.where(
                Policy.title.ilike("%" + q + "%")
            )

        rows = db.scalars(
            stmt.order_by(Policy.id)
            .limit(limit)
            .offset(offset)
        ).all()

        return not_found(rows)

    return query_or_503(run)


# --------------------------------------------------
# 7. Data sources
# --------------------------------------------------

@app.get("/data-sources", response_model=list[DataSourceOut])
def data_sources(
    db: DB,
    limit: Limit = 100,
    offset: Offset = 0,
):

    def run():
        stmt = (
            select(DataSource)
            .order_by(DataSource.id)
            .limit(limit)
            .offset(offset)
        )

        rows = db.scalars(stmt).all()

        return not_found(rows)

    return query_or_503(run)