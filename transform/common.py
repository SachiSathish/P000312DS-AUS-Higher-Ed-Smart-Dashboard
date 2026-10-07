"""Shared helpers for the cleaning scripts in transform/.

Every clean_*.py script:
  - reads only from the raw layer (data/bronze/, the files fingerprinted in data/MANIFEST.csv)
  - refuses to use a raw file whose SHA-256 no longer matches MANIFEST.csv
  - writes only to data/processed/ (outputs, quarantine/, reports/, dictionaries/)
  - is deterministic: rows are sorted on their grain before writing

Conventions kept everywhere:
  0     = a zero the source actually reported
  blank = unknown / suppressed / not available (never written as 0)
  codes (ASCED, CRICOS, ABS, register IDs) stay text so leading zeroes survive
"""

import csv
import hashlib
import json
import pathlib
import re
import sys
import zipfile

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "bronze"                      # the raw layer; MANIFEST paths are relative to data/
MANIFEST = DATA / "MANIFEST.csv"
CONFIG = ROOT / "config"
PROCESSED = DATA / "processed"
STAGING = PROCESSED / "staging"
QUARANTINE = PROCESSED / "quarantine"
REPORTS = PROCESSED / "reports"
DICTIONARIES = PROCESSED / "dictionaries"

sys.path.insert(0, str(ROOT / "transform"))
import extract_pivot_cache as epc         # noqa: E402  (the project's pivot-cache reader)

# Markers the source agencies use for "suppressed / not published". They become null.
SUPPRESSION_MARKERS = {"<5", "< 5", "np", "n.p.", "*", "-", "–", "—", "..", "x", "n/a", "na"}


# ---------------------------------------------------------------------------
# Raw layer and manifest
# ---------------------------------------------------------------------------

def manifest():
    return pd.read_csv(MANIFEST, dtype=str, keep_default_na=False)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ManifestMismatch(RuntimeError):
    pass


def raw_path(manifest_file):
    """Resolve a MANIFEST.csv `file` value and verify its fingerprint before it is read.

    Raises ManifestMismatch (and nothing is read) if the file is missing, unlisted,
    or its SHA-256 differs from the manifest.
    """
    m = manifest()
    row = m[m["file"] == manifest_file]
    if row.empty:
        raise ManifestMismatch(f"{manifest_file} is not listed in MANIFEST.csv")
    path = DATA / manifest_file
    if not path.exists():
        raise ManifestMismatch(f"{manifest_file} is listed in MANIFEST.csv but missing on disk")
    expected = row.iloc[0]["sha256"].lower()
    actual = sha256(path)
    if actual != expected:
        raise ManifestMismatch(f"{manifest_file}: sha256 {actual} != manifest {expected}")
    return path


# ---------------------------------------------------------------------------
# Pivot workbooks
# ---------------------------------------------------------------------------

def read_pivot_cache(path):
    """All underlying records of a pivot workbook, via transform/extract_pivot_cache.py.

    Every value comes back as text (or None); numeric parsing happens later and is
    reported. Returns (DataFrame, declared_record_count).
    """
    zf = zipfile.ZipFile(path)
    definition, part = epc.cache_parts(zf)
    names, shared, declared = epc.read_fields(zf, definition)
    # Calculated fields (cacheField/@formula, e.g. Home Affairs "Grant Rate") hold no record values
    # and always come last; they are derived ratios, so they are dropped here.
    root = epc.ET.fromstring(zf.read(definition))
    formula = [f.get("name") for f in root.find(f"{epc.NS}cacheFields") if f.get("formula") is not None]
    stored = [n for n in names if n not in formula]
    if names[: len(stored)] != stored:
        raise RuntimeError(f"{path.name}: calculated fields are not at the end of the cache: {formula}")
    df = pd.DataFrame.from_records(list(epc.records(zf, part, shared[: len(stored)])), columns=stored)
    df.attrs["calculated_fields_dropped"] = formula
    if declared and len(df) != declared:
        raise RuntimeError(f"{path.name}: extracted {len(df):,} records, cache declares {declared:,}")
    return df, declared


# ---------------------------------------------------------------------------
# Value cleaning
# ---------------------------------------------------------------------------

def clean_text(s):
    """Trim and collapse whitespace; empty strings become null. Keeps text as text."""
    s = s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    return s.mask(s == "")


def to_number(series, integer=True):
    """Parse a measure column without ever turning a suppression marker into 0.

    Returns (parsed, stats). stats counts: missing (blank in source), suppressed
    (a known marker -> null), unparseable (anything else -> null, reported as an error),
    zeros (genuine zeroes kept as 0).
    """
    s = series.astype("string").str.strip()
    blank = s.isna() | (s == "")
    marker = s.str.lower().isin(SUPPRESSION_MARKERS) & ~blank
    cleaned = s.mask(blank | marker).str.replace(",", "", regex=False)   # "1,234" -> "1234"
    parsed = pd.to_numeric(cleaned, errors="coerce")
    unparseable = parsed.isna() & cleaned.notna()
    if integer:
        frac = parsed.notna() & (parsed % 1 != 0)
        if frac.any():
            raise ValueError(f"{series.name}: {int(frac.sum())} non-integer values in a count column")
        parsed = parsed.astype("Int64")
    stats = {
        "missing_in_source": int(blank.sum()),
        "suppressed_to_null": int(marker.sum()),
        "suppression_markers_seen": sorted(s[marker].str.lower().unique().tolist()),
        "unparseable_to_null": int(unparseable.sum()),
        "unparseable_examples": s[unparseable].unique()[:5].tolist(),
        "explicit_zeros": int((parsed == 0).sum()),
    }
    return parsed, stats


STATE_CODES = {
    "Australian Capital Territory": "ACT", "New South Wales": "NSW", "Northern Territory": "NT",
    "Queensland": "QLD", "South Australia": "SA", "Tasmania": "TAS", "Victoria": "VIC",
    "Western Australia": "WA",
}


# ---------------------------------------------------------------------------
# Config mappings (all reviewed by hand, all in config/)
# ---------------------------------------------------------------------------

def load_config(name):
    return pd.read_csv(CONFIG / name, dtype=str, keep_default_na=False)


def standardise_country(series):
    """Map source country labels to the project's single representation.

    config/country_map.csv lists only labels that differ between sources; anything not
    listed passes through unchanged (and is reported), so nothing is silently merged.
    """
    cmap = load_config("country_map.csv")
    lookup = dict(zip(cmap["source_name"], cmap["standard_name"]))
    s = clean_text(series)
    mapped = s.map(lambda v: lookup.get(v, v) if pd.notna(v) else v)
    changed = sorted(set(s.dropna()) & set(lookup))
    return mapped.astype("string"), changed


# ---------------------------------------------------------------------------
# Duplicates, output, reporting
# ---------------------------------------------------------------------------

def aggregate_grain(df, keys, measures):
    """Sum additive measures over duplicate grain rows. Nulls stay null unless every
    contributor is null (min_count=1); a null contributor next to a number is counted
    and reported, because the sum is then a lower bound."""
    dup_rows = int(df.duplicated(keys, keep=False).sum())
    dup_groups = int(df[df.duplicated(keys, keep=False)].groupby(keys, dropna=False).ngroups) if dup_rows else 0
    partial_null = 0
    if dup_rows:
        flags = df[keys].copy()
        for m in measures:
            flags[f"{m}__null"] = df[m].isna()
            flags[f"{m}__val"] = df[m].notna()
        g = flags.groupby(keys, dropna=False)
        partial = pd.concat([g[f"{m}__null"].any() & g[f"{m}__val"].any() for m in measures], axis=1)
        partial_null = int(partial.any(axis=1).sum())
    out = df.groupby(keys, dropna=False, sort=True, observed=True)[measures].sum(min_count=1).reset_index()
    for m in measures:
        if str(df[m].dtype) == "Int64":
            out[m] = out[m].astype("Int64")
    stats = {
        "duplicate_rows_at_grain_before": dup_rows,
        "duplicate_groups_at_grain_before": dup_groups,
        "rows_collapsed_by_aggregation": len(df) - len(out),
        "groups_with_partial_null_contributors": partial_null,
        "duplicate_rows_at_grain_after": int(out.duplicated(keys).sum()),
    }
    return out, stats


def write_csv(df, path, sort_by=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if sort_by:
        df = df.sort_values(sort_by, kind="mergesort", na_position="last")
    df.to_csv(path, index=False, encoding="utf-8", na_rep="", quoting=csv.QUOTE_MINIMAL,
              lineterminator="\n")
    return len(df)


def category_values(df, cols):
    return {c: sorted(map(str, df[c].dropna().unique().tolist())) for c in cols if c in df.columns}


def write_report(name, report):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with open(REPORTS / f"{name}.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)


def write_dictionary(name, title, notes, rows):
    """rows: (column, meaning, data type, source/transformation, measure, year convention)"""
    DICTIONARIES.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"File: `data/processed/{name}`", ""]
    lines += [n for n in notes] + [""] if notes else []
    lines += ["| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    out = DICTIONARIES / (pathlib.Path(name).stem + ".md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def strip_label(text):
    return re.sub(r"\s+", " ", str(text)).strip()
