# institutions

File: `data/processed/institutions.csv`

Target table `institutions`. Load key: `name` (the loader assigns `id`).
Scope: higher-education providers only -- see the rule in transform/clean_institutions.py.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| name | Institution name (HESSC spelling for HESSC universities, CRICOS spelling otherwise) | text <=255 | HESSC Institution / CRICOS Institution Name, whitespace collapsed | - | - |
| provider_type | public or private | text: public\|private | CRICOS Institution Type: Government->public, Private->private | - | - |
| state | State of the registered postal address | text <=10, nullable | CRICOS Postal Address State | - | as at 2026-08-09 |
| sector | Provider sector | text, blank | No source available | - | - |
| teqsa_id | TEQSA provider ID | text, blank | TEQSA register not collected | - | - |
| cricos_provider_code | CRICOS provider code (natural key for joins; not a models.py column) | text, 5 digits + letter | CRICOS Provider Code; HESSC rows via config/institution_crosswalk.csv | - | - |
| source_file | MANIFEST.csv path(s) the row came from, ';'-separated | text | - | - | - |
