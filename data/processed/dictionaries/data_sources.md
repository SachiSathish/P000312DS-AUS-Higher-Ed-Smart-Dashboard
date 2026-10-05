# data_sources

File: `data/processed/data_sources.csv`

Target table `data_sources`. Load key: `source_file` (= MANIFEST.csv `file`).

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| name | Dataset description | text <=255 | MANIFEST description | - | - |
| source_type | api, csv or scrape | text | rule in clean_data_sources.py | - | - |
| url | Download URL | text <=1000 | MANIFEST source_url | - | - |
| retrieved_at | When the file was downloaded (UTC) | datetime YYYY-MM-DD HH:MM:SS | MANIFEST retrieved_utc | - | - |
| license_notes | Licence | text | MANIFEST licence | - | - |
| source_file | MANIFEST.csv file path (load key) | text | MANIFEST file | - | - |
