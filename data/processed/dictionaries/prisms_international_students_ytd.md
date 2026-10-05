# PRISMS international students (YTD)

File: `data/processed/staging/prisms_international_students_ytd.csv`

STAGING -- no target table in models.py. Grain: every column except the two measures and source_file.
Values are cumulative year-to-date. Never add months together.

| Column | Meaning | Data type | Source/Transformation | Measure | Year convention |
|---|---|---|---|---|---|
| year | Reporting year | integer | Year | - | calendar year |
| month | YTD up to this month (1-12) | integer | Month name -> number | - | calendar month |
| citizenship_country | Nationality, project standard spelling | text | Nationality via config/country_map.csv | - | - |
| citizenship_country_source | Nationality as published | text | Nationality | - | - |
| state | State/territory of study (NAT = national) | text | State | - | - |
| sector | Education sector | text | Sector | - | - |
| provider_type | public or private | text | ProviderType: Government->public, Non Government->private | - | - |
| new_to_australia | Student new to Australia | true/false | New_to_Australia | - | - |
| ends_this_year | Course ends this year (blank = not reported) | true/false, nullable | Ends_This_Year | - | - |
| ytd_enrolments | Enrolments YTD | integer, nullable | DATA_YTD_Enrolments | YTD enrolments | calendar YTD |
| ytd_commencements | Commencements YTD | integer, nullable | DATA_YTD_Commencements | YTD commencements | calendar YTD |
| source_file | MANIFEST.csv path | text | - | - | - |
