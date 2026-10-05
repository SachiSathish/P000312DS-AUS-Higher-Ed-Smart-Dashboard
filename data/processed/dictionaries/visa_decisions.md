# Student visas -- decisions

File: `data/processed/staging/visa_decisions.csv`

STAGING -- no target table in models.py. Grain: every column except the measures and source_file.
Grant rate is not stored; derive it from visa_decisions (granted / (granted + refused)).

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| financial_year | Financial year of decision | text YYYY-YY | Financial Year of Decision | - | financial year (Jul-Jun) |
| quarter | Financial-year quarter (Q1 = Jul-Sep) | text Q1-Q4 | Financial Year Quarter | - | financial year |
| month | Calendar month number (7 = July) | integer 1-12 | Month 'M01 Jul' -> 7 | - | calendar month |
| client_location | Applicant in / outside Australia | text | Client Location | - | - |
| lodgement_channel | Internet / Paper | text | Lodgement Channel | - | - |
| sector | Education sector of the visa | text | Sector | - | - |
| applicant_type | Primary / Secondary applicant | text | Applicant Type | - | - |
| provider_state | Provider's registered state | text | Education Provider Registered State | - | - |
| gender | Gender | text | Gender | - | - |
| age_group | Age group | text | Age Group | - | - |
| citizenship_country | Citizenship, project standard spelling | text | Citizenship Country via config/country_map.csv | - | - |
| citizenship_country_source | Citizenship as published | text | Citizenship Country | - | - |
| granted | Number of applications granted | integer, nullable | Grant Total | count (decision) | financial year |
| refused | Number of applications refused | integer, nullable | Refused Total | count (decision) | financial year |
| source_file | MANIFEST.csv path | text | - | - | - |
