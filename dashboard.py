
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# =====================================================
# CONFIGURATION
# =====================================================

API_URL = "http://localhost"
BASE_DIR = Path(__file__).resolve().parent

REPORT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "reports"
    / "cleaning_report.json"
)

st.set_page_config(
    page_title="AUS Higher Ed Smart Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 AUS Higher Ed Smart Dashboard")
st.caption(
    "RMIT University | Backend Data Pipeline Demonstration"
)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

@st.cache_data(ttl=30)
def fetch_data(endpoint):
    response = requests.get(
        f"{API_URL}{endpoint}",
        timeout=20
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def load_cleaning_report(path, modified_time):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# =====================================================
# FETCH DATABASE DATA
# =====================================================

try:
    health = fetch_data("/health/db")
    tables = fetch_data("/tables")
    enrolments = fetch_data("/enrolments/summary")

except (requests.RequestException, ValueError) as error:
    st.error(f"Cannot retrieve data from FastAPI: {error}")
    st.stop()


# =====================================================
# 1. PIPELINE AND DATABASE STATUS
# =====================================================

st.divider()
st.header("1. Pipeline and Database Status")

if health.get("database") == "ok":
    st.success("PostgreSQL database connection successful")
else:
    st.warning("Database health check did not return OK")

table_df = pd.DataFrame(tables)

if not {"table", "row_count"}.issubset(table_df.columns):
    st.error("Unexpected response format from /tables.")
    st.stop()

table_df["row_count"] = pd.to_numeric(
    table_df["row_count"],
    errors="coerce"
).fillna(0).astype(int)

counts = dict(
    zip(table_df["table"], table_df["row_count"])
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Institutions",
    f"{counts.get('institutions', 0):,}"
)

col2.metric(
    "Enrolment Records",
    f"{counts.get('enrollment_stats', 0):,}"
)

col3.metric(
    "Data Sources",
    f"{counts.get('data_sources', 0):,}"
)

col4.metric(
    "Policy Records",
    f"{counts.get('policies', 0):,}"
)


# =====================================================
# 2. STUDENT ENROLMENT ANALYSIS
# =====================================================

st.divider()
st.header("2. Student Enrolment Analysis")

df = pd.DataFrame(enrolments)

required_columns = {
    "year", "student_count", "group"
}

if not df.empty and required_columns.issubset(df.columns):

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    )

    df["student_count"] = pd.to_numeric(
        df["student_count"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["year", "student_count"]
    ).copy()

    if not df.empty:

        df["year"] = df["year"].astype(int)
        years = sorted(df["year"].unique().tolist())

        selected_years = st.multiselect(
            "Select years",
            options=years,
            default=years
        )

        filtered = df[
            df["year"].isin(selected_years)
        ].copy()

        if not filtered.empty:

            chart = px.bar(
                filtered,
                x="year",
                y="student_count",
                color="group",
                barmode="group",
                title="Domestic vs International Enrolments",
                labels={
                    "year": "Year",
                    "student_count": "Student Enrolments",
                    "group": "Citizenship"
                }
            )

            chart.update_xaxes(type="category")

            st.plotly_chart(
                chart,
                width="stretch"
            )

            st.subheader("Enrolment Data")

            st.dataframe(
                filtered,
                width="stretch",
                hide_index=True
            )

        else:
            st.info(
                "Select at least one year to display enrolments."
            )

    else:
        st.warning("No valid enrolment records available.")

else:
    st.warning(
        "No enrolment data available or the API response "
        "does not contain the expected fields."
    )


# =====================================================
# 3. DATABASE TABLE VERIFICATION
# =====================================================

st.divider()
st.header("3. Database Table Verification")

st.write(
    "The dashboard retrieves processed higher-education "
    "records from the existing PostgreSQL database "
    "through the FastAPI backend."
)

st.dataframe(
    table_df.sort_values("table"),
    width="stretch",
    hide_index=True
)


# =====================================================
# 4. TASK 1 - PIPELINE VALIDATION
# =====================================================

st.divider()
st.header("4. Pipeline Validation")

st.write(
    "This section displays the cleaning and validation "
    "results generated by the project's Python data pipeline."
)

if REPORT_PATH.exists():

    try:
        report = load_cleaning_report(
            str(REPORT_PATH),
            REPORT_PATH.stat().st_mtime
        )

        status = report.get("status", "UNKNOWN")
        passed = int(report.get("checks_passed", 0))
        failed = int(report.get("checks_failed", 0))
        warnings = report.get("warnings", [])
        passed_checks = report.get("passed", [])
        failures = report.get("failures", [])

        if status == "PASS":
            st.success(
                "Data Cleaning and Validation Status: PASS"
            )
        else:
            st.warning(
                f"Data Cleaning and Validation Status: {status}"
            )

        val1, val2, val3 = st.columns(3)

        val1.metric("Checks Passed", f"{passed:,}")
        val2.metric("Checks Failed", f"{failed:,}")
        val3.metric(
            "Data Quality Warnings",
            f"{len(warnings):,}"
        )

        st.subheader("Validation Success Rate")

        total_checks = passed + failed

        if total_checks > 0:
            success_rate = passed / total_checks

            st.progress(success_rate)

            st.caption(
                f"{success_rate * 100:.1f}% of recorded "
                "validation checks passed."
            )
        else:
            st.info("No validation checks recorded.")

        st.subheader("Raw Data Integrity")

        raw_integrity = report.get("raw_integrity", {})

        if raw_integrity:

            integrity_df = pd.DataFrame(
                [
                    {
                        "Source File": filename,
                        "Integrity Status": result
                    }
                    for filename, result
                    in raw_integrity.items()
                ]
            )

            st.dataframe(
                integrity_df,
                width="stretch",
                hide_index=True
            )

        else:
            st.info("No raw integrity results available.")

        with st.expander(
            f"View Data Quality Warnings ({len(warnings)})"
        ):

            if warnings:
                for index, warning in enumerate(
                    warnings,
                    start=1
                ):
                    st.write(f"{index}. {warning}")
            else:
                st.success("No warnings recorded.")

        with st.expander("View Passed Validation Checks"):

            if passed_checks:
                for check in passed_checks:
                    st.write(f"✓ {check}")
            else:
                st.info("Detailed checks are unavailable.")

        if failures:
            with st.expander("View Failed Validation Checks"):
                for failure in failures:
                    st.error(str(failure))

        st.caption(
            "These results come from the saved cleaning report. "
            "They describe a recorded pipeline run, not a new "
            "execution or automatic validation of the current database."
        )

    except (OSError, ValueError, TypeError) as error:
        st.error(f"Unable to read cleaning report: {error}")

else:
    st.warning(
        f"Cleaning report not found: {REPORT_PATH}"
    )


# =====================================================
# 5. TASK 2 - INSTITUTION EXPLORER
# =====================================================

st.divider()
st.header("5. Institution Explorer")

st.write(
    "Search and explore Australian higher education "
    "institutions loaded into PostgreSQL."
)

try:
    institutions = fetch_data(
        "/institutions?limit=1000&offset=0"
    )

    institutions_df = pd.DataFrame(institutions)

    required_institution_columns = {
        "name", "provider_type", "state"
    }

    if (
        not institutions_df.empty
        and required_institution_columns.issubset(
            institutions_df.columns
        )
    ):

        institutions_df = institutions_df.copy()

        for column in ["provider_type", "state"]:
            institutions_df[column] = (
                institutions_df[column]
                .fillna("Unknown")
                .astype(str)
            )

        institutions_df["name"] = (
            institutions_df["name"].fillna("").astype(str)
        )

        search_query = st.text_input(
            "Search institution name",
            placeholder="Enter university or institution name..."
        )

        filter1, filter2 = st.columns(2)

        provider_options = sorted(
            institutions_df["provider_type"].unique().tolist()
        )

        state_options = sorted(
            institutions_df["state"].unique().tolist()
        )

        selected_providers = filter1.multiselect(
            "Provider type",
            options=provider_options,
            default=provider_options
        )

        selected_states = filter2.multiselect(
            "State",
            options=state_options,
            default=state_options
        )

        filtered_institutions = institutions_df.copy()

        if search_query.strip():
            filtered_institutions = filtered_institutions[
                filtered_institutions["name"].str.contains(
                    search_query.strip(),
                    case=False,
                    regex=False,
                    na=False
                )
            ]

        filtered_institutions = filtered_institutions[
            filtered_institutions["provider_type"].isin(
                selected_providers
            )
            & filtered_institutions["state"].isin(
                selected_states
            )
        ]

        inst1, inst2, inst3 = st.columns(3)

        inst1.metric(
            "Institutions Retrieved",
            len(institutions_df)
        )

        inst2.metric(
            "Matching Institutions",
            len(filtered_institutions)
        )

        inst3.metric(
            "States/Territories Represented",
            filtered_institutions["state"].nunique()
        )

        if len(institutions_df) != counts.get(
            "institutions", 0
        ):
            st.warning(
                "API institution count differs from the "
                "database table count."
            )

        if not filtered_institutions.empty:

            provider_counts = (
                filtered_institutions["provider_type"]
                .value_counts()
                .reset_index()
            )

            provider_counts.columns = [
                "Provider Type",
                "Institutions"
            ]

            provider_chart = px.bar(
                provider_counts,
                x="Provider Type",
                y="Institutions",
                color="Provider Type",
                title="Institutions by Provider Type"
            )

            st.plotly_chart(
                provider_chart,
                width="stretch"
            )

            st.subheader("Institution Records")

            display_columns = [
                column for column in [
                    "name",
                    "provider_type",
                    "state",
                    "sector",
                    "teqsa_id"
                ]
                if column in filtered_institutions.columns
            ]

            st.dataframe(
                filtered_institutions[display_columns],
                width="stretch",
                hide_index=True
            )

        else:
            st.info(
                "No institutions match the selected filters."
            )

    else:
        st.warning(
            "No institution records or expected fields available."
        )

except (requests.RequestException, ValueError) as error:
    st.error(
        f"Unable to retrieve institutions: {error}"
    )


# =====================================================
# 6. TASK 3 - DATA PROVENANCE
# =====================================================

st.divider()
st.header("6. Data Provenance and Source Tracking")

st.write(
    "This section shows how the data pipeline maintains "
    "traceability through source information, retrieval "
    "timestamps, original URLs and licensing metadata."
)

try:
    sources = fetch_data("/data-sources")
    sources_df = pd.DataFrame(sources)

    required_source_columns = {
        "name", "source_type", "url", "retrieved_at"
    }

    if (
        not sources_df.empty
        and required_source_columns.issubset(
            sources_df.columns
        )
    ):

        sources_df = sources_df.copy()

        sources_df["source_type"] = (
            sources_df["source_type"]
            .fillna("Unknown")
            .astype(str)
        )

        sources_df["name"] = (
            sources_df["name"]
            .fillna("")
            .astype(str)
        )

        sources_df["retrieved_at"] = pd.to_datetime(
            sources_df["retrieved_at"],
            errors="coerce",
            utc=True
        )

        # Source summary metrics
        source1, source2, source3 = st.columns(3)

        source1.metric(
            "Data Sources Retrieved",
            len(sources_df)
        )

        source2.metric(
            "Source Types",
            sources_df["source_type"].nunique()
        )

        valid_dates = sources_df["retrieved_at"].dropna()

        latest_date = (
            valid_dates.max().strftime("%d %b %Y")
            if not valid_dates.empty
            else "Unavailable"
        )

        source3.metric(
            "Latest Recorded Retrieval",
            latest_date
        )

        # Source filters
        source_search = st.text_input(
            "Search datasets",
            placeholder="Enter dataset or source name..."
        )

        source_type_options = sorted(
            sources_df["source_type"].unique().tolist()
        )

        selected_source_types = st.multiselect(
            "Filter by source type",
            options=source_type_options,
            default=source_type_options
        )

        filtered_sources = sources_df[
            sources_df["source_type"].isin(
                selected_source_types
            )
        ].copy()

        if source_search.strip():
            filtered_sources = filtered_sources[
                filtered_sources["name"].str.contains(
                    source_search.strip(),
                    case=False,
                    regex=False,
                    na=False
                )
            ]

        if not filtered_sources.empty:

            # Source type chart
            source_counts = (
                filtered_sources["source_type"]
                .value_counts()
                .reset_index()
            )

            source_counts.columns = [
                "Source Type",
                "Number of Sources"
            ]

            source_chart = px.bar(
                source_counts,
                x="Source Type",
                y="Number of Sources",
                color="Source Type",
                title="Data Sources by Type"
            )

            st.plotly_chart(
                source_chart,
                width="stretch"
            )

            # Dataset provenance table
            st.subheader("Dataset Provenance Records")

            display_sources = filtered_sources.copy()

            display_sources["retrieved_at"] = (
                display_sources["retrieved_at"]
                .dt.strftime("%Y-%m-%d %H:%M UTC")
                .fillna("Unavailable")
            )

            display_columns = [
                column for column in [
                    "name",
                    "source_type",
                    "url",
                    "retrieved_at",
                    "license_notes"
                ]
                if column in display_sources.columns
            ]

            column_settings = {
                "name": st.column_config.TextColumn(
                    "Dataset Name"
                ),
                "source_type": st.column_config.TextColumn(
                    "Source Type"
                ),
                "url": st.column_config.LinkColumn(
                    "Original Data URL"
                ),
                "retrieved_at": st.column_config.TextColumn(
                    "Retrieved At"
                ),
                "license_notes": st.column_config.TextColumn(
                    "Licence / Notes"
                )
            }

            column_settings = {
                key: value
                for key, value in column_settings.items()
                if key in display_columns
            }

            st.dataframe(
                display_sources[display_columns],
                width="stretch",
                hide_index=True,
                column_config=column_settings
            )

        else:
            st.info(
                "No data sources match the selected filters."
            )

        if len(sources_df) != counts.get("data_sources", 0):
            st.warning(
                "The API data-source count differs from "
                "the database table count."
            )

        st.caption(
            "Provenance records are retrieved from the live "
            "FastAPI service. Recorded timestamps and metadata "
            "do not imply a new download or validation occurred."
        )

    else:
        st.warning(
            "No data sources returned or required "
            "metadata fields are missing."
        )

except (requests.RequestException, ValueError) as error:
    st.error(
        f"Unable to retrieve data provenance: {error}"
    )


# =====================================================
# 7. DATA PIPELINE ARCHITECTURE
# =====================================================

st.divider()
st.header("7. Data Pipeline Architecture")

st.info(
    "Government Datasets → Python Data Ingestion → "
    "Cleaning and Transformation → PostgreSQL + pgvector "
    "→ FastAPI → Streamlit"
)

st.caption(
    "AUS Higher Ed Smart Dashboard | "
    "RMIT Data Science Postgraduate Project"
)
