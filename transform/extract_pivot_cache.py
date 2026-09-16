"""Extract the full dataset from an Excel pivot-cache workbook.

The Department of Education and Home Affairs publish their statistics as pivot
workbooks. The visible worksheet is a saved pivot *view*; the underlying records
live in xl/pivotCache/pivotCacheRecords*.xml and are not reachable through
pandas.read_excel(), which returns the view and raises no error.

This reads the cache directly:
  - pivotCacheDefinition gives the field names and their shared-item lookup lists
  - pivotCacheRecords holds one <r> per record, with a child per field:
        <x v="N"/>  index into that field's shared items
        <n v="1.0"/> numeric literal      <s v="text"/> string literal
        <b v="1"/>   boolean             <m/>          missing
Records are streamed with iterparse so a 150 MB part does not need to fit in memory.

Usage:
    python extract_pivot_cache.py <workbook.xlsx> [-o out.csv] [--parquet] [--limit N]
"""

import argparse
import csv
import pathlib
import zipfile
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def cache_parts(zf):
    """Return (definition, records) part names for the workbook's pivot cache."""
    definition = next(n for n in zf.namelist() if "pivotCacheDefinition" in n and n.endswith(".xml"))
    records = next(n for n in zf.namelist() if "pivotCacheRecords" in n and n.endswith(".xml"))
    return definition, records


def read_fields(zf, definition):
    """Field names plus, for each, the ordered shared-item values (empty if literal)."""
    root = ET.fromstring(zf.read(definition))
    names, shared = [], []
    for field in root.find(f"{NS}cacheFields"):
        names.append(field.get("name"))
        items = field.find(f"{NS}sharedItems")
        # <m/> entries are nulls in the lookup list and must keep their position
        shared.append([el.get("v") for el in items] if items is not None and len(items) else [])
    return names, shared, int(root.get("recordCount") or 0)


def records(zf, part, shared, limit=None):
    """Yield one list of values per <r> element."""
    yielded = 0
    with zf.open(part) as handle:
        for _, elem in ET.iterparse(handle, events=("end",)):
            if elem.tag != f"{NS}r":
                continue
            row = []
            for i, cell in enumerate(elem):
                tag = cell.tag[len(NS):]
                if tag == "x":                              # shared-item index, absent means 0
                    idx = int(cell.get("v") or 0)
                    lookup = shared[i] if i < len(shared) else []
                    row.append(lookup[idx] if idx < len(lookup) else None)
                elif tag == "m":                            # missing
                    row.append(None)
                else:                                       # n / s / b / d literal
                    row.append(cell.get("v"))
            yield row
            elem.clear()                                    # free the parsed subtree
            yielded += 1
            if limit and yielded >= limit:                  # count records, not XML elements
                return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("-o", "--out")
    ap.add_argument("--parquet", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    src = pathlib.Path(args.workbook)
    zf = zipfile.ZipFile(src)
    definition, part = cache_parts(zf)
    names, shared, expected = read_fields(zf, definition)

    print(f"{src.name}")
    print(f"  {len(names)} fields, {expected:,} records declared")

    out = pathlib.Path(args.out) if args.out else src.with_suffix(
        ".parquet" if args.parquet else ".csv")

    if args.parquet:
        import pyarrow as pa
        import pyarrow.parquet as pq
        rows, writer, batch = 0, None, []
        for row in records(zf, part, shared, args.limit):
            batch.append(row)
            rows += 1
            if len(batch) >= 100_000:
                table = pa.table({n: [r[i] for r in batch] for i, n in enumerate(names)})
                writer = writer or pq.ParquetWriter(out, table.schema, compression="snappy")
                writer.write_table(table)
                batch = []
        if batch:
            table = pa.table({n: [r[i] for r in batch] for i, n in enumerate(names)})
            writer = writer or pq.ParquetWriter(out, table.schema, compression="snappy")
            writer.write_table(table)
        if writer:
            writer.close()
    else:
        rows = 0
        with open(out, "w", newline="", encoding="utf8") as fh:
            w = csv.writer(fh)
            w.writerow(names)
            for row in records(zf, part, shared, args.limit):
                w.writerow(row)
                rows += 1

    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  wrote {rows:,} rows -> {out.name} ({size_mb:,.1f} MB)")
    if args.limit:
        print(f"  (--limit set: stopped early, {expected:,} records available)")
    elif expected and rows != expected:
        print(f"  WARNING: expected {expected:,} records, extracted {rows:,}")
    else:
        print("  record count matches the workbook's declared total")


if __name__ == "__main__":
    main()
