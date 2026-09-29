"""
AUS Higher Ed Smart Dashboard — Reviewed Extended Schema
P000312DS

Designed from the existing schema and the full collected education-data review.

Original models retained:
- Institution
- FieldOfStudy
- CitizenshipStatus
- EnrollmentStat
- Policy
- DataSource

Added:
- Course
- Location
- CourseLocation
- ExternalStat

The statistical tables use JSONB dimensions so additional categorical
breakdowns can be represented without changing the schema for every dataset.

Review-driven additions include:
- suppressed/not-published value handling (for values such as "np" and "< 5")
- observation geography independent of institution location
- source sheet/table traceability
- flexible support for enrolments, EFTSL, completions and rate-based measures
- source-level disclosure-control / data-quality notes
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    UniqueConstraint,
)

from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Institution
# ---------------------------------------------------------------------------

class Institution(Base):
    """Higher-education provider / institution."""

    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[Optional[str]] = mapped_column(String(50))
    state: Mapped[Optional[str]] = mapped_column(String(20))
    sector: Mapped[Optional[str]] = mapped_column(String(50))
    teqsa_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Collected CRICOS provider information
    cricos_provider_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True
    )
    trading_name: Mapped[Optional[str]] = mapped_column(String(255))
    institution_capacity: Mapped[Optional[int]] = mapped_column(Integer)
    website: Mapped[Optional[str]] = mapped_column(String(1000))

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(
        back_populates="institution"
    )

    courses: Mapped[List["Course"]] = relationship(
        back_populates="institution"
    )

    locations: Mapped[List["Location"]] = relationship(
        back_populates="institution"
    )


# ---------------------------------------------------------------------------
# Field of Study
# ---------------------------------------------------------------------------

class FieldOfStudy(Base):
    """Field-of-education classification."""

    __tablename__ = "fields_of_study"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    broad_field: Mapped[Optional[str]] = mapped_column(String(255))
    narrow_field: Mapped[Optional[str]] = mapped_column(String(255))
    detailed_field: Mapped[Optional[str]] = mapped_column(String(255))

    field_code: Mapped[Optional[str]] = mapped_column(String(20))

    # Dashboard-oriented grouping, e.g. STEM / Social Studies.
    # This is separate from the official ASCED field hierarchy above.
    analysis_group: Mapped[Optional[str]] = mapped_column(String(100))

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(
        back_populates="field_of_study"
    )


# ---------------------------------------------------------------------------
# Citizenship Status
# ---------------------------------------------------------------------------

class CitizenshipStatus(Base):
    """Domestic/international status and optional country."""

    __tablename__ = "citizenship_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    country_of_origin: Mapped[Optional[str]] = mapped_column(
        String(100)
    )

    # Higher-level grouping such as Domestic / International.
    # Keeps detailed statuses such as Australian, New Zealand,
    # Permanent Resident and Humanitarian Visa without losing detail.
    status_group: Mapped[Optional[str]] = mapped_column(String(50))

    enrollments: Mapped[List["EnrollmentStat"]] = relationship(
        back_populates="citizenship_status"
    )


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(Base):
    """Course information collected from sources such as CRICOS."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)

    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id"),
        nullable=False
    )

    field_of_study_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fields_of_study.id"),
        nullable=True
    )

    cricos_course_code: Mapped[Optional[str]] = mapped_column(
        String(30)
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    vet_national_code: Mapped[Optional[str]] = mapped_column(String(50))
    course_level: Mapped[Optional[str]] = mapped_column(String(100))
    language: Mapped[Optional[str]] = mapped_column(String(100))

    duration_weeks: Mapped[Optional[float]] = mapped_column(Float)

    tuition_fee: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    non_tuition_fee: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    estimated_total_cost: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 2)
    )

    foundation_studies: Mapped[Optional[str]] = mapped_column(String(50))
    work_component: Mapped[Optional[str]] = mapped_column(String(50))

    work_component_hours_per_week: Mapped[Optional[float]] = mapped_column(
        Float
    )
    work_component_weeks: Mapped[Optional[float]] = mapped_column(Float)
    work_component_total_hours: Mapped[Optional[float]] = mapped_column(Float)

    expired: Mapped[Optional[str]] = mapped_column(String(20))

    data_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("data_sources.id")
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "cricos_course_code",
            name="uq_institution_cricos_course"
        ),
    )

    institution: Mapped["Institution"] = relationship(
        back_populates="courses"
    )

    field_of_study: Mapped[Optional["FieldOfStudy"]] = relationship()

    data_source: Mapped[Optional["DataSource"]] = relationship()

    locations: Mapped[List["CourseLocation"]] = relationship(
        back_populates="course"
    )


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class Location(Base):
    """Provider campus / delivery location."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)

    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    location_type: Mapped[Optional[str]] = mapped_column(String(100))

    address_line_1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line_2: Mapped[Optional[str]] = mapped_column(String(255))
    address_line_3: Mapped[Optional[str]] = mapped_column(String(255))
    address_line_4: Mapped[Optional[str]] = mapped_column(String(255))

    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(20))
    postcode: Mapped[Optional[str]] = mapped_column(String(20))

    data_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("data_sources.id")
    )

    institution: Mapped["Institution"] = relationship(
        back_populates="locations"
    )

    data_source: Mapped[Optional["DataSource"]] = relationship()

    courses: Mapped[List["CourseLocation"]] = relationship(
        back_populates="location"
    )


# ---------------------------------------------------------------------------
# Course ↔ Location
# ---------------------------------------------------------------------------

class CourseLocation(Base):
    """Locations at which a course is offered."""

    __tablename__ = "course_locations"

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id"),
        primary_key=True
    )

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"),
        primary_key=True
    )

    course: Mapped["Course"] = relationship(
        back_populates="locations"
    )

    location: Mapped["Location"] = relationship(
        back_populates="courses"
    )


# ---------------------------------------------------------------------------
# Higher-Education Statistics
# ---------------------------------------------------------------------------

class EnrollmentStat(Base):
    """
    Flexible higher-education statistical observation.

    Optional dimensions allow institution-level, state-level and
    national aggregate observations.

    Examples of measure_type:
    - enrolment
    - EFTSL
    - completion
    - success_rate
    - retention_rate
    - attrition_rate
    - access_rate
    - participation_rate
    - amount
    - percent_change

    dimensions contains additional breakdowns such as equity group,
    liability status, course level, gender or other source-specific
    categories.
    """

    __tablename__ = "enrollment_stats"

    id: Mapped[int] = mapped_column(primary_key=True)

    institution_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("institutions.id"),
        nullable=True
    )

    field_of_study_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fields_of_study.id"),
        nullable=True
    )

    citizenship_status_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("citizenship_statuses.id"),
        nullable=True
    )

    year: Mapped[Optional[int]] = mapped_column(Integer)

    reporting_period: Mapped[Optional[str]] = mapped_column(
        String(50)
    )

    measure_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Nullable because source publications can contain suppressed or
    # unpublished values such as "< 5" and "np".
    value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    # Original published representation, especially useful when value is NULL.
    # Examples: "< 5", "np", "91.22".
    source_value_text: Mapped[Optional[str]] = mapped_column(String(100))

    # Examples: published, suppressed, not_published, not_applicable.
    observation_status: Mapped[Optional[str]] = mapped_column(String(50))

    observation_comment: Mapped[Optional[str]] = mapped_column(Text)

    unit_of_measure: Mapped[Optional[str]] = mapped_column(
        String(100)
    )

    aggregation_level: Mapped[Optional[str]] = mapped_column(
        String(50)
    )

    # Geography belongs to the observation, not necessarily the institution.
    # Examples: Victoria, Australia, Sri Lanka, Multi-State.
    geography: Mapped[Optional[str]] = mapped_column(String(255))
    geography_type: Mapped[Optional[str]] = mapped_column(String(50))

    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    # Workbook-level traceability. Examples: sheet "13.12", table "Table 13.12".
    source_sheet: Mapped[Optional[str]] = mapped_column(String(255))
    source_table: Mapped[Optional[str]] = mapped_column(String(500))

    data_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("data_sources.id")
    )

    institution: Mapped[Optional["Institution"]] = relationship(
        back_populates="enrollments"
    )

    field_of_study: Mapped[Optional["FieldOfStudy"]] = relationship(
        back_populates="enrollments"
    )

    citizenship_status: Mapped[Optional["CitizenshipStatus"]] = relationship(
        back_populates="enrollments"
    )

    data_source: Mapped[Optional["DataSource"]] = relationship()


# ---------------------------------------------------------------------------
# External Statistics
# ---------------------------------------------------------------------------

class ExternalStat(Base):
    """
    Statistical observations related to the project that do not
    naturally belong to an institution.

    Examples:
    - visa grants
    - visa applications
    - grant rates
    - arrivals
    - departures
    - migration statistics

    dimensions allows source-specific categories such as citizenship,
    visa category, migration type, age group and other breakdowns.
    """

    __tablename__ = "external_stats"

    id: Mapped[int] = mapped_column(primary_key=True)

    statistic_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    time_period: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )

    source_value_text: Mapped[Optional[str]] = mapped_column(String(100))

    unit_of_measure: Mapped[Optional[str]] = mapped_column(
        String(100)
    )

    geography: Mapped[Optional[str]] = mapped_column(
        String(255)
    )

    frequency: Mapped[Optional[str]] = mapped_column(
        String(50)
    )

    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )

    observation_status: Mapped[Optional[str]] = mapped_column(
        String(50)
    )

    observation_comment: Mapped[Optional[str]] = mapped_column(
        Text
    )

    source_sheet: Mapped[Optional[str]] = mapped_column(String(255))
    source_table: Mapped[Optional[str]] = mapped_column(String(500))

    data_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("data_sources.id")
    )

    data_source: Mapped[Optional["DataSource"]] = relationship()


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class Policy(Base):
    """Education / immigration policy or procedural document."""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(50)
    )

    document_id: Mapped[Optional[str]] = mapped_column(
        String(100)
    )

    document_type: Mapped[Optional[str]] = mapped_column(
        String(100)
    )

    summary: Mapped[Optional[str]] = mapped_column(Text)

    full_text: Mapped[Optional[str]] = mapped_column(Text)

    effective_date: Mapped[Optional[date]] = mapped_column(Date)

    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000)
    )

    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536),
        nullable=True
    )

    data_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("data_sources.id")
    )

    data_source: Mapped[Optional["DataSource"]] = relationship()


# ---------------------------------------------------------------------------
# Data Source / Provenance
# ---------------------------------------------------------------------------

class DataSource(Base):
    """Source and provenance information for collected data."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    source_type: Mapped[str] = mapped_column(
        String(50)
    )

    publisher: Mapped[Optional[str]] = mapped_column(
        String(255)
    )

    url: Mapped[Optional[str]] = mapped_column(
        String(1000)
    )

    file_name: Mapped[Optional[str]] = mapped_column(
        String(500)
    )

    checksum: Mapped[Optional[str]] = mapped_column(
        String(128)
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    license_notes: Mapped[Optional[str]] = mapped_column(
        Text
    )

    # Preserve publication-level data-quality information rather than
    # silently altering source values during ingestion.
    disclosure_control_method: Mapped[Optional[str]] = mapped_column(
        String(255)
    )

    data_quality_notes: Mapped[Optional[str]] = mapped_column(Text)