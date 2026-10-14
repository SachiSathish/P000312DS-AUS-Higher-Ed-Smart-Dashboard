"""
AUS Higher Ed Smart Dashboard — Draft Schema (SQLAlchemy 2.0 style)
P000312DS

Design: star-schema-ish.
- Dimension tables: Institution, FieldOfStudy, CitizenshipStatus
- Fact table: EnrollmentStat — one row per (institution, field of study,
  citizenship status, year) combination, so demographics / fields of
  study / provider-type questions can all be answered by slicing the
  same fact table instead of four disconnected datasets.
- Policy is kept separate (it's document-like, not tabular). Its full_text
  is stored so embeddings can be generated from it later if needed — see
  the PolicyEmbedding blueprint at the bottom of this file.
- DataSource logs where every row came from, since Han wants
  multi-source / multi-modal data and provenance matters for the report.
- Immigration and international-student data (Home Affairs student visas,
  ABS net overseas migration, PRISMS) are stored at full published detail
  in their own fact tables (VisaLodgement, VisaGrant, VisaDecision,
  MigrationFlow, IntlStudentEnrolment). Each source is a separate published
  cube with its own grain and year convention, so they are not forced into
  EnrollmentStat; citizenship_country uses one agreed spelling
  (config/country_map.csv) so the sources can be compared by country.
  Summary views for the dashboard are created in the migration.
"""

from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, SmallInteger, Float, Boolean, Date, DateTime, ForeignKey, Text,
    UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dimension tables
# ---------------------------------------------------------------------------

class Institution(Base):
    """A higher education provider """
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50))  # 'public' | 'private'
    state: Mapped[Optional[str]] = mapped_column(String(10))  # e.g. VIC, NSW
    sector: Mapped[Optional[str]] = mapped_column(String(50))  # e.g. university, TAFE, RTO
    teqsa_id: Mapped[Optional[str]] = mapped_column(String(50))  # provider registry ref, if available

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(back_populates="institution")


class FieldOfStudy(Base):
    """Academic field, tagged with broad categories."""
    __tablename__ = "fields_of_study"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    broad_field: Mapped[str] = mapped_column(String(50))  # 'STEM' | 'Social Studies' | other
    field_code: Mapped[Optional[str]] = mapped_column(String(20))  # ASCED code, if used

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(back_populates="field_of_study")


class CitizenshipStatus(Base):
    """Lookup: domestic vs international, plus optional country of origin."""
    __tablename__ = "citizenship_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'domestic' | 'international'
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(100))  # null for domestic

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(back_populates="citizenship_status")


# ---------------------------------------------------------------------------
# Fact table
# ---------------------------------------------------------------------------

class EnrollmentStat(Base):
    """
    One row = enrollment count for a given institution + field of study +
    citizenship status + year. This is the central table the dashboard
    queries against for demographics, fields-of-study, and provider-type
    breakdowns - they're all just different group-bys over this table.
    """
    __tablename__ = "enrollment_stats"
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "field_of_study_id", "citizenship_status_id", "year",
            name="uq_enrollment_grain",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    field_of_study_id: Mapped[int] = mapped_column(ForeignKey("fields_of_study.id"))
    citizenship_status_id: Mapped[int] = mapped_column(ForeignKey("citizenship_statuses.id"))
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    student_count: Mapped[int] = mapped_column(Integer, nullable=False)

    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))

    institution: Mapped["Institution"] = relationship(back_populates="enrollments")
    field_of_study: Mapped["FieldOfStudy"] = relationship(back_populates="enrollments")
    citizenship_status: Mapped["CitizenshipStatus"] = relationship(back_populates="enrollments")
    data_source: Mapped[Optional["DataSource"]] = relationship()


# ---------------------------------------------------------------------------
# Policy documents (separate — text/document data, not tabular stats)
# ---------------------------------------------------------------------------

class Policy(Base):
    """
    Immigration / education policy document or summary.
    full_text is kept so a future embeddings table can be built from it
    without changing this table (see PolicyEmbedding below).
    """
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50))  # 'immigration' | 'education'
    summary: Mapped[Optional[str]] = mapped_column(Text)
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))

    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))
    data_source: Mapped[Optional["DataSource"]] = relationship()


# ---------------------------------------------------------------------------
# Provenance — every row should be traceable to where it came from
# ---------------------------------------------------------------------------

class DataSource(Base):
    """Logs where a batch of data came from — required since Han wants
    multiple sources and the report needs to justify/cite them."""
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "ABS Higher Ed Stats 2024"
    source_type: Mapped[str] = mapped_column(String(50))  # 'api' | 'csv' | 'scrape'
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    license_notes: Mapped[Optional[str]] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Immigration and international-student fact tables
# ---------------------------------------------------------------------------
# Loaded from data/processed/staging/ by transform/load_staging.py, one row per
# row of the cleaned file. Columns follow data/processed/dictionaries/*.md.
# Measures are nullable: blank in the source means unknown, never 0.

class VisaDetailMixin:
    """Columns shared by the three Home Affairs student visa tables."""
    id: Mapped[int] = mapped_column(primary_key=True)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. '2024-25'
    quarter: Mapped[str] = mapped_column(String(2), nullable=False)          # Q1 = Jul-Sep
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)         # 7 = July
    client_location: Mapped[Optional[str]] = mapped_column(String(50))   # In / Outside Australia
    lodgement_channel: Mapped[Optional[str]] = mapped_column(String(30))  # Internet / Paper
    sector: Mapped[Optional[str]] = mapped_column(String(100))            # e.g. Higher Education Sector
    applicant_type: Mapped[Optional[str]] = mapped_column(String(30))     # Primary / Secondary
    provider_state: Mapped[Optional[str]] = mapped_column(String(30))
    gender: Mapped[Optional[str]] = mapped_column(String(30))
    age_group: Mapped[Optional[str]] = mapped_column(String(30))
    citizenship_country: Mapped[Optional[str]] = mapped_column(String(100))   # agreed spelling
    citizenship_country_source: Mapped[Optional[str]] = mapped_column(String(150))  # as published
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))


class VisaLodgement(VisaDetailMixin, Base):
    """Student visa applications lodged (Home Affairs BP0015)."""
    __tablename__ = "visa_lodgements"
    __table_args__ = (
        Index("ix_visa_lodgements_year", "financial_year"),
        Index("ix_visa_lodgements_country", "citizenship_country"),
    )

    lodged: Mapped[Optional[int]] = mapped_column(Integer)


class VisaGrant(VisaDetailMixin, Base):
    """Student visas granted, with the visa held before the grant."""
    __tablename__ = "visa_grants"
    __table_args__ = (
        Index("ix_visa_grants_year", "financial_year"),
        Index("ix_visa_grants_country", "citizenship_country"),
    )

    last_visa_category: Mapped[Optional[str]] = mapped_column(String(100))
    granted: Mapped[Optional[int]] = mapped_column(Integer)


class VisaDecision(VisaDetailMixin, Base):
    """Student visa decisions. Grant rate = granted / (granted + refused);
    it is derived, never stored."""
    __tablename__ = "visa_decisions"
    __table_args__ = (
        Index("ix_visa_decisions_year", "financial_year"),
        Index("ix_visa_decisions_country", "citizenship_country"),
    )

    granted: Mapped[Optional[int]] = mapped_column(Integer)
    refused: Mapped[Optional[int]] = mapped_column(Integer)


class MigrationFlow(Base):
    """ABS net overseas migration (NOM) arrivals and departures by visa group.
    Both ABS releases share this table: period_type says whether period is a
    financial year ('2004-05') or a calendar year ('2004').
    Rows with is_aggregate = true are published totals that do not equal
    their parts -- exclude them before summing."""
    __tablename__ = "migration_flows"
    __table_args__ = (
        Index("ix_migration_flows_period", "period_type", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'financial' | 'calendar'
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    visa_group_code: Mapped[Optional[str]] = mapped_column(String(20))
    visa_group: Mapped[Optional[str]] = mapped_column(String(100))
    migration_type_code: Mapped[Optional[str]] = mapped_column(String(10))  # 1 arrivals, 2 departures
    migration_type: Mapped[Optional[str]] = mapped_column(String(30))
    region_code: Mapped[Optional[str]] = mapped_column(String(10))           # AUS = Australia
    region: Mapped[Optional[str]] = mapped_column(String(50))
    persons: Mapped[Optional[int]] = mapped_column(Integer)        # rounded to 10 by ABS
    is_aggregate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))


class IntlStudentEnrolment(Base):
    """PRISMS international student enrolments, cumulative year-to-date.
    Each month's values already include earlier months: never add months
    together -- use the latest month of each year."""
    __tablename__ = "intl_student_enrolments"
    __table_args__ = (
        Index("ix_intl_student_enrolments_year", "year", "month"),
        Index("ix_intl_student_enrolments_country", "citizenship_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)   # YTD up to this month
    citizenship_country: Mapped[Optional[str]] = mapped_column(String(100))
    citizenship_country_source: Mapped[Optional[str]] = mapped_column(String(150))
    state: Mapped[Optional[str]] = mapped_column(String(10))                     # NAT = national
    sector: Mapped[Optional[str]] = mapped_column(String(50))
    provider_type: Mapped[Optional[str]] = mapped_column(String(20))             # public | private
    new_to_australia: Mapped[Optional[bool]] = mapped_column(Boolean)
    ends_this_year: Mapped[Optional[bool]] = mapped_column(Boolean)    # blank = not reported
    ytd_enrolments: Mapped[Optional[int]] = mapped_column(Integer)
    ytd_commencements: Mapped[Optional[int]] = mapped_column(Integer)
    data_source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_sources.id"))


# ---------------------------------------------------------------------------
# FUTURE: embeddings (not part of the current schema)
# ---------------------------------------------------------------------------
# The project doesn't use embeddings or LLMs. If a future team needs semantic
# search over policy text, embeddings go in their OWN table rather than as a
# column on policies. That way:
#   - no existing table changes, so it's one new migration that's easy to undo
#   - several embedding models (and dimensions) can coexist for comparison
#   - long documents can be split into chunks, one row per chunk
#
# To add it:
#   1. Add `pgvector` to api/requirements.txt, then `docker compose up -d --build`
#      (the db service already uses the pgvector/pgvector image, so the
#      database side needs no change).
#   2. Uncomment the import and class below.
#   3. Run `make migration_revision` and name it e.g. "add policy embeddings".
#   4. Edit the new migration file (Alembic doesn't add these itself):
#        - with the other imports at the top:   import pgvector.sqlalchemy
#        - first line inside upgrade():         op.execute("CREATE EXTENSION IF NOT EXISTS vector")
#   5. Run `make migration_head`.
#
# from pgvector.sqlalchemy import Vector
#
# class PolicyEmbedding(Base):
#     """One embedding per chunk of a policy's full_text, per model."""
#     __tablename__ = "policy_embeddings"
#     __table_args__ = (
#         UniqueConstraint("policy_id", "model_name", "chunk_index",
#                          name="uq_policy_embedding_chunk"),
#     )
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     policy_id: Mapped[int] = mapped_column(
#         ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)
#     model_name: Mapped[str] = mapped_column(String(100), nullable=False)
#     chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
#     chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
#     # Set the dimension to match the chosen model's output size.
#     embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=False)
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
#
#     policy: Mapped["Policy"] = relationship()
