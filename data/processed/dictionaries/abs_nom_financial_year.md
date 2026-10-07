# ABS NOM by visa group -- financial year

File: `data/processed/staging/abs_nom_financial_year.csv`

STAGING -- no target table in models.py. Grain: year x visa_group_code x migration_type_code x region_code.
Rows with is_aggregate = true are totals that do not equal their parts; exclude them before summing.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| financial_year | Reference year | text YYYY-YY | TIME_PERIOD | - | financial year ending 30 June |
| visa_group_code | ABS visa / citizenship group code | text | MEASURE | - | - |
| visa_group | Visa / citizenship group | text | Visa and Citizenship Groups | - | - |
| migration_type_code | ABS code (1 arrivals, 2 departures) | text | MIGRATIONTYPE | - | - |
| migration_type | NOM arrivals or NOM departures | text | Migration Type | - | - |
| region_code | ABS state code (AUS = Australia) | text | REGION | - | - |
| region | State / territory or Australia | text | Region | - | - |
| persons | Number of people | integer, nullable | OBS_VALUE | persons, rounded to 10 | financial_year |
| is_aggregate | true for total rows kept because they do not reconcile | true/false | reconciliation | - | - |
| source_file | MANIFEST.csv path | text | - | - | - |
