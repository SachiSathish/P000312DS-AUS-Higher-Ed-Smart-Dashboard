# enrollment_stats

File: `data/processed/enrollment_stats.csv`

Target table `enrollment_stats`. Grain: institution x field x citizenship x year (unique).
The loader resolves `institution_name` -> institutions.name, `field_name` -> fields_of_study.name, (`status`, `country_of_origin`) -> citizenship_statuses, `source_file` -> data_sources.
Excluded rows (provider groups, Batchelor, Carnegie Mellon) are in quarantine/enrollment_stats_quarantine.csv.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| institution_name | Institution (load key) | text <=255 | HESSC Institution | - | - |
| field_name | ASCED broad field of the primary course field (load key) | text | HESSC Broad_Field_of_Education_Primary | - | - |
| field_code | 2-digit ASCED broad field code; blank for Non-Award / Not provided | text '01'-'12' | CRICOS ASCED labels | - | - |
| status | domestic or international | text | HESSC Citizenship: Domestic->domestic, Overseas->international | - | - |
| country_of_origin | Always blank (no country in HESSC) | text, blank | - | - | - |
| year | Reference year | integer | HESSC Year | - | calendar year |
| student_count | Course enrolments, all students | integer >= 0, not null | sum of HESSC Enrolment Count over the grain | headcount enrolments (commencing + continuing); not EFTSL | calendar year |
| source_file | MANIFEST.csv path | text | - | - | - |
