# fields_of_study

File: `data/processed/fields_of_study.csv`

Target table `fields_of_study`. Load key: `name`. broad_field mapping is PROPOSED.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| name | ASCED broad field name | text <=255 | HESSC | - | - |
| broad_field | STEM, Social Studies or other | text | config/asced_broad_field_map.csv (PROPOSED) | - | - |
| field_code | 2-digit ASCED broad field code | text, nullable | CRICOS course register labels | - | - |
| source_file | MANIFEST.csv path(s), ';'-separated | text | - | - | - |
