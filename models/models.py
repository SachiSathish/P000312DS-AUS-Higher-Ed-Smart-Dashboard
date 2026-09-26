"""
AUS Higher Ed Smart Dashboard — Draft Schema (SQLAlchemy 2.0 style)
P000312DS

Design: star-schema-ish.
- Dimension tables: Institution, FieldOfStudy, CitizenshipStatus
- Fact table: EnrollmentStat — one row per (institution, field of study,
  citizenship status, year) combination, so demographics / fields of
  study / provider-type questions can all be answered by slicing the
  same fact table instead of four disconnected datasets.
- Policy is kept separate (it's document-like, not tabular) with a
  pgvector embedding column for RAG/semantic search over policy text.
- DataSource logs where every row came from, since Han wants
  multi-source / multi-modal data and provenance matters for the report.
"""

from datetime import date, datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, Date, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


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
    Immigration / education policy document or summary. Embedding column
    lets the AI layer do semantic search / RAG over policy text later.
    """
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50))  # 'immigration' | 'education'
    summary: Mapped[Optional[str]] = mapped_column(Text)
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Adjust dimension (1536 shown for OpenAI-style embeddings) once the
    # embedding model is chosen.
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

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
