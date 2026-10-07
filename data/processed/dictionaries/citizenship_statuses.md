# citizenship_statuses

File: `data/processed/citizenship_statuses.csv`

Target table `citizenship_statuses`. Load key: (`status`, `country_of_origin`).

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| status | domestic or international | text <=20 | HESSC Citizenship | - | - |
| country_of_origin | Blank (HESSC has no country) | text <=100, nullable | - | - | - |
| source_file | MANIFEST.csv path | text | - | - | - |
