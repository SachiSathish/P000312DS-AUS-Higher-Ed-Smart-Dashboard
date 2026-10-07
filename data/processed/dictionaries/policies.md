# policies

File: `data/processed/policies.csv`

Target table `policies`. Load key: (`title`, `source_url`) -- titles alone repeat.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| title | Act / instrument / direction title | text <=500 | legislation dump `name`; MD115 PDF heading | - | - |
| category | immigration or education | text | title rule (see script docstring) | - | - |
| summary | Blank | text, nullable | not in sources | - | - |
| full_text | Full text (MD115 only) | text, nullable | pypdf extraction; signature line is OCR-noisy | - | - |
| effective_date | Commencement date (MD115 only) | date YYYY-MM-DD, nullable | 'This Direction commences on ...' | - | calendar date |
| source_url | Canonical URL | text <=1000 | legislation.gov.au/<id>; MD115 from MANIFEST | - | - |
| source_file | MANIFEST.csv path | text | - | - | - |
