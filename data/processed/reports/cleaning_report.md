# Cleaning report -- PASS

186 checks passed, 0 failed. Schema: `models/models.py` (models.py copied unchanged from SachiSathish/P000312DS-AUS-Higher-Ed-Smart-Dashboard, branch main, commit 4dfd89d (2026-10-04); identical to main HEAD c8671d2 on 2026-10-04).

## Row reconciliation

| Output | Target table | Source file(s) | Raw rows | Processed rows | Removed | Aggregated away | Dup before | Dup after | Suppressed->null | Measure | Year convention |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---|---|
| `institutions.csv` | institutions | bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx<br>bronze/cricos-register/cricos_institutions_asat-2026-08-09.csv<br>bronze/cricos-register/cricos_courses_asat-2026-08-09.csv | 1,554 | 178 | blank_trailing_rows: 2; exact_duplicate_rows: 0; cricos_secondary_registrations_of_listed_universities: 2; cricos_not_higher_education: 1,367; quarantined_no_provider_type: 0; quarantined_name_collisions: 5 | 0 | 0 | 0 | 0 | n/a (dimension table) | n/a; CRICOS register as at 2026-08-09 |
| `fields_of_study.csv` | fields_of_study | bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx<br>bronze/cricos-register/cricos_courses_asat-2026-08-09.csv | 14 | 14 | mapping rows not used by HESSC: 0 | 0 | 0 | 0 | 0 | n/a (dimension) | n/a |
| `citizenship_statuses.csv` | citizenship_statuses | bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx | 2 | 2 | 0 | 0 | 0 | 0 | 0 | n/a (dimension) | n/a |
| `enrollment_stats.csv` | enrollment_stats | bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx | 235,292 | 4,381 | quarantined: HESSC group of many providers, not one institution; provider_type mixed: 14,365; quarantined: institution not in institutions.csv (not on CRICOS, provider_type unknown): 109 | 216,437 | 220,769 | 0 | 0 | Enrolment Count (all-student headcount of course enrolments; commencing + continuing; not EFTSL) | calendar year (HESSC reference year), 2020-2024 |
| `policies.csv` | policies | bronze/legislation-policy/legislation_overseas-students-titles_asat-2026-08-09.json<br>bronze/legislation-policy/homeaffairs_ministerial-direction-115_2025-11-14.pdf | 171 | 138 | exact duplicate records (same register id, title, collection): 33 | 0 | 33 | 0 | 0 | n/a (documents) | effective_date = commencement date (MD115 only) |
| `data_sources.csv` | data_sources | MANIFEST.csv | 20 | 20 | 0 | 0 | 0 | 0 | 0 | n/a | retrieved_at in UTC |
| `staging/prisms_international_students_ytd.csv` | staging (none) | bronze/education-international/education_intl-students-ytd-all_2026-05.xlsx | 3,583,979 | 3,583,979 | 0 | 0 | 0 | 0 | 0 | YTD enrolments and YTD commencements (a student in two courses = two enrolments) | calendar year, year-to-date to `month` |
| `staging/visa_lodgements.csv` | staging (none) | bronze/homeaffairs-visas/homeaffairs_student-visas-lodged_asat-2026-06-30.xlsx | 2,096,102 | 2,096,102 | 0 | 0 | 0 | 0 | 0 | lodged: count of visa applications (lodgement event) | Australian financial year (Jul-Jun) of lodgement, e.g. 2024-25 |
| `staging/visa_grants.csv` | staging (none) | bronze/homeaffairs-visas/homeaffairs_student-visas-granted_asat-2026-06-30.xlsx | 2,292,011 | 2,292,011 | 0 | 0 | 0 | 0 | 0 | granted: count of visa applications (grant event) | Australian financial year (Jul-Jun) of grant, e.g. 2024-25 |
| `staging/visa_decisions.csv` | staging (none) | bronze/homeaffairs-visas/homeaffairs_student-visa-grant-rates_asat-2026-06-30.xlsx | 2,064,231 | 2,064,231 | 0 | 0 | 0 | 0 | 0 | granted: count of visa applications (decision event), refused: count of visa applications (decision event) | Australian financial year (Jul-Jun) of decision, e.g. 2024-25 |
| `staging/abs_nom_financial_year.csv` | staging (none) | bronze/abs-migration/abs_nom-arrivals-departures-by-visa_financial-year.csv | 5,814 | 5,814 | 0 | 0 | 0 | 0 | 0 | persons (NOM arrivals / departures) | financial year ending 30 June (TIME_PERIOD 2005 -> 2004-05) |
| `staging/abs_nom_calendar_year.csv` | staging (none) | bronze/abs-migration/abs_nom-arrivals-departures-by-visa_calendar-year.csv | 5,814 | 5,814 | 0 | 0 | 0 | 0 | 0 | persons (NOM arrivals / departures) | calendar year |

## Failures

None.

## Warnings

- raw layer has 4 files not in MANIFEST.csv (not used): ['bronze/education-international-2025-12/education_intl-student-ytd_2025-12_all-data.xlsx', 'bronze/education-international-2025-12/education_intl-student-ytd_2025-12_latest-data.xlsx', 'bronze/education-international-2025-12/education_intl-student-ytd_2025-12_summary-infographic.pdf', 'bronze/education-international-2025-12/manifest.csv']
- institutions.csv: HESSC institution 'Batchelor Institute of Indigenous Tertiary Education' is not on CRICOS: provider_type unknown, not loaded (its enrolments go to quarantine)
- institutions.csv: HESSC institution 'Carnegie Mellon University Australia' is not on CRICOS: provider_type unknown, not loaded (its enrolments go to quarantine)
- institutions.csv: 2 names shared by 5 CRICOS providers; quarantined (see quarantine/institutions_name_collisions.csv)
- institutions.csv: teqsa_id is blank for every row: TEQSA register not collected
- institutions.csv: sector is blank for every row: no source distinguishes university / TAFE / other
- fields_of_study.csv: broad_field mapping is PROPOSED (config/asced_broad_field_map.csv); needs team sign-off
- citizenship_statuses.csv: country_of_origin blank: HESSC has no country dimension
- enrollment_stats.csv: fields_of_study.broad_field uses config/asced_broad_field_map.csv, status PROPOSED -- needs team sign-off
- enrollment_stats.csv: Quarantined enrolments by year (share of all HESSC enrolments): 2020: 126,068 (7.8%), 2021: 117,530 (7.3%), 2022: 114,812 (7.4%), 2023: 138,525 (8.7%), 2024: 162,348 (9.7%)
- enrollment_stats.csv: country_of_origin is blank for every citizenship row: HESSC has no country dimension
- policies.csv: 17 titles repeat (e.g. several 'Overseas Students Charge Regulations (Amendment)'); they are different instruments -- load key must be (title, source_url), not title alone
- policies.csv: legislation rows have no summary, full_text or effective_date: the titles dump does not carry them
- policies.csv: category is assigned by the title rule in clean_policies.py; check immigration_titles
- data_sources.csv: source_type 'scrape' is used for direct xlsx/pdf downloads: the schema has no 'download' value -- team decision needed
- staging/prisms_international_students_ytd.csv: country mapping config/country_map.csv is PROPOSED
- staging/prisms_international_students_ytd.csv: YTD cumulative values: do not sum across months
- staging/prisms_international_students_ytd.csv: state 'NAT' kept as published (national / no single state)
- staging/visa_lodgements.csv: country mapping config/country_map.csv is PROPOSED
- staging/visa_lodgements.csv: 'Not Specified' / 'Not Available' categories kept as published
- staging/visa_grants.csv: country mapping config/country_map.csv is PROPOSED
- staging/visa_grants.csv: 'Not Specified' / 'Not Available' categories kept as published
- staging/visa_decisions.csv: country mapping config/country_map.csv is PROPOSED
- staging/visa_decisions.csv: 'Not Specified' / 'Not Available' categories kept as published
- staging/abs_nom_financial_year.csv: visa_group_code 1: differs from its components on 176 rows -> kept, is_aggregate=true
- staging/abs_nom_financial_year.csv: visa_group_code 9: differs from its components on 154 rows -> kept, is_aggregate=true
- staging/abs_nom_financial_year.csv: visa_group_code 16: differs from its components on 152 rows -> kept, is_aggregate=true
- staging/abs_nom_financial_year.csv: region_code AUS: differs from its components on 353 rows -> kept, is_aggregate=true
- staging/abs_nom_financial_year.csv: ABS values are rounded to the nearest 10
- staging/abs_nom_calendar_year.csv: visa_group_code 1: differs from its components on 177 rows -> kept, is_aggregate=true
- staging/abs_nom_calendar_year.csv: visa_group_code 9: differs from its components on 127 rows -> kept, is_aggregate=true
- staging/abs_nom_calendar_year.csv: visa_group_code 16: differs from its components on 170 rows -> kept, is_aggregate=true
- staging/abs_nom_calendar_year.csv: region_code AUS: differs from its components on 383 rows -> kept, is_aggregate=true
- staging/abs_nom_calendar_year.csv: ABS values are rounded to the nearest 10

## Transformations

- `institutions.csv`: CRICOS Government -> public, Private -> private; HESSC names kept as the canonical name for the universities HESSC lists; CRICOS registrations sharing a crosswalked university's CRICOS name dropped as secondary registrations; whitespace trimmed/collapsed; codes kept as text
- `fields_of_study.csv`: ASCED broad field names from HESSC; codes from CRICOS; broad_field from config
- `citizenship_statuses.csv`: Domestic -> domestic, Overseas -> international
- `enrollment_stats.csv`: Citizenship Domestic -> domestic, Overseas -> international; field = Broad_Field_of_Education_Primary; field_code from the CRICOS ASCED labels; summed over gender, course level, attendance mode/type, commencing status, special course, state; HESSC provider groups, institutions without provider_type, and null counts -> quarantine
- `policies.csv`: title whitespace collapsed; category by title rule; source_url from register id; MD115 text extracted with pypdf
- `data_sources.csv`: description -> name; retrieved_utc -> retrieved_at (UTC, no offset)
- `staging/prisms_international_students_ytd.csv`: Month name -> month number; ProviderType Government->public, Non Government->private; Yes/No -> true/false; country standardised (raw kept in citizenship_country_source)
- `staging/visa_lodgements.csv`: 'Q1 (Jul-Sep)' -> Q1; 'M01 Jul' -> calendar month 7; country standardised (raw kept in citizenship_country_source); rows summed over identical dimension values
- `staging/visa_grants.csv`: 'Q1 (Jul-Sep)' -> Q1; 'M01 Jul' -> calendar month 7; country standardised (raw kept in citizenship_country_source); rows summed over identical dimension values
- `staging/visa_decisions.csv`: 'Q1 (Jul-Sep)' -> Q1; 'M01 Jul' -> calendar month 7; country standardised (raw kept in citizenship_country_source); rows summed over identical dimension values
- `staging/abs_nom_financial_year.csv`: SDMX labelled CSV reduced to one value per row; ABS codes kept as text; redundant aggregate rows removed / non-reconciling ones flagged
- `staging/abs_nom_calendar_year.csv`: SDMX labelled CSV reduced to one value per row; ABS codes kept as text; redundant aggregate rows removed / non-reconciling ones flagged

## Category values

- `institutions.csv` **provider_type**: private, public
- `institutions.csv` **state**: ACT, NSW, NT, QLD, SA, TAS, VIC, WA
- `institutions.csv` **sector**: 
- `institutions.csv` **teqsa_id**: 
- `institutions.csv` **cricos_provider_code**: 00002J, 00003G, 00004G, 00005F, 00008C, 00012G, 00017B, 00025B, 00026A, 00092B, 00098G, 00099F, 00102E, 00103D, 00109J, 00111D, 00113B, 00114A, 00115M, 00116K, 00117J, 00120C, 00121B, 00122A, 00123M ... (178 values)
- `fields_of_study.csv` **broad_field**: STEM, Social Studies, other
- `fields_of_study.csv` **field_code**: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12
- `citizenship_statuses.csv` **status**: domestic, international
- `citizenship_statuses.csv` **country_of_origin**: 
- `enrollment_stats.csv` **institution_name**: Australian Catholic University, Avondale University, Bond University, CQUniversity, Charles Darwin University, Charles Sturt University, Curtin University, Deakin University, Edith Cowan University, Federation University Australia, Flinders University, Griffith University, James Cook University, La Trobe University, Macquarie University, Monash University, Murdoch University, Queensland University of Technology, RMIT University, Southern Cross University, Swinburne University of Technology, The Australian National University, The University of Adelaide, The University of Melbourne, The University of New England ... (42 values)
- `enrollment_stats.csv` **field_name**: Agriculture, Environmental and Related Studies, Architecture and Building, Creative Arts, Education, Engineering and Related Technologies, Food, Hospitality and Personal Services, Health, Information Technology, Management and Commerce, Mixed Field Programmes, Natural and Physical Sciences, Non-Award Courses, Not provided, Society and Culture
- `enrollment_stats.csv` **field_code**: 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12
- `enrollment_stats.csv` **status**: domestic, international
- `enrollment_stats.csv` **country_of_origin**: 
- `enrollment_stats.csv` **year**: 2020, 2021, 2022, 2023, 2024
- `policies.csv` **category**: education, immigration
- `policies.csv` **summary**: 
- `policies.csv` **effective_date**: 2025-11-14
- `data_sources.csv` **source_type**: api, csv, scrape
- `data_sources.csv` **retrieved_at**: 2026-08-08 14:26:36, 2026-08-08 14:26:37, 2026-08-08 14:26:39, 2026-08-08 14:26:42
- `data_sources.csv` **license_notes**: CC BY 2.5 AU, CC BY 3.0 AU, CC BY 4.0
- `staging/prisms_international_students_ytd.csv` **year**: 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026
- `staging/prisms_international_students_ytd.csv` **month**: 1, 10, 11, 12, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/prisms_international_students_ytd.csv` **citizenship_country**: Afghanistan, Albania, Algeria, Andorra, Angola, Anguilla, Antigua and Barbuda, Argentina, Armenia, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bermuda, Bhutan, Bolivia, Bosnia and Herzegovina, Botswana, Bouvet Island ... (220 values)
- `staging/prisms_international_students_ytd.csv` **state**: ACT, NAT, NSW, NT, QLD, SA, TAS, VIC, WA
- `staging/prisms_international_students_ytd.csv` **sector**: ELICOS, Higher Education, Non-award, Schools, VET
- `staging/prisms_international_students_ytd.csv` **provider_type**: private, public
- `staging/prisms_international_students_ytd.csv` **new_to_australia**: false, true
- `staging/prisms_international_students_ytd.csv` **ends_this_year**: false, true
- `staging/visa_lodgements.csv` **financial_year**: 2005-06, 2006-07, 2007-08, 2008-09, 2009-10, 2010-11, 2011-12, 2012-13, 2013-14, 2014-15, 2015-16, 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26
- `staging/visa_lodgements.csv` **quarter**: Q1, Q2, Q3, Q4
- `staging/visa_lodgements.csv` **month**: 1, 10, 11, 12, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/visa_lodgements.csv` **client_location**: In Australia, Outside Australia
- `staging/visa_lodgements.csv` **lodgement_channel**: Internet, Paper
- `staging/visa_lodgements.csv` **sector**: Foreign Affairs or Defence Sector, Higher Education Sector, Independent ELICOS Sector, Non-Award Sector, Postgraduate Research Sector, Schools Sector, Vocational Education and Training Sector
- `staging/visa_lodgements.csv` **applicant_type**: Primary, Secondary
- `staging/visa_lodgements.csv` **provider_state**: ACT, NSW, NT, Not Available, QLD, SA, TAS, VIC, WA
- `staging/visa_lodgements.csv` **gender**: Female, Male, Not Specified
- `staging/visa_lodgements.csv` **age_group**: 0 to 4 years, 10 to 14 years, 15 to 19 years, 20 to 24 years, 25 to 29 years, 30 to 34 years, 35 to 39 years, 40 to 44 years, 45 to 49 years, 5 to 9 years, 50 to 54 years, 55 and over, Not Specified
- `staging/visa_lodgements.csv` **citizenship_country**: Afghanistan, Albania, Algeria, Andorra, Angola, Anguilla, Antigua and Barbuda, Argentina, Armenia, Aruba, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bermuda, Bhutan, Bolivia, Bonaire, Saint Eustatius & Saba, Bosnia and Herzegovina ... (235 values)
- `staging/visa_grants.csv` **financial_year**: 2005-06, 2006-07, 2007-08, 2008-09, 2009-10, 2010-11, 2011-12, 2012-13, 2013-14, 2014-15, 2015-16, 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26
- `staging/visa_grants.csv` **quarter**: Q1, Q2, Q3, Q4
- `staging/visa_grants.csv` **month**: 1, 10, 11, 12, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/visa_grants.csv` **client_location**: In Australia, Outside Australia
- `staging/visa_grants.csv` **lodgement_channel**: Internet, Paper
- `staging/visa_grants.csv` **sector**: Foreign Affairs or Defence Sector, Higher Education Sector, Independent ELICOS Sector, Non-Award Sector, Postgraduate Research Sector, Schools Sector, Vocational Education and Training Sector
- `staging/visa_grants.csv` **applicant_type**: Primary, Secondary
- `staging/visa_grants.csv` **provider_state**: ACT, NSW, NT, Not Available, QLD, SA, TAS, VIC, WA
- `staging/visa_grants.csv` **gender**: Female, Male, Not Specified
- `staging/visa_grants.csv` **age_group**: 0 to 4 years, 10 to 14 years, 15 to 19 years, 20 to 24 years, 25 to 29 years, 30 to 34 years, 35 to 39 years, 40 to 44 years, 45 to 49 years, 5 to 9 years, 50 to 54 years, 55 and over, Not Specified
- `staging/visa_grants.csv` **last_visa_category**: Crew and Transit, Offshore Humanitarian, Other Temporary, Other visas / No Previous Visa, Special Category, Student, Temporary Graduate, Temporary Protection, Temporary Resident (Other Employment), Temporary Resident (Skilled Employment), Visitor, Working Holiday Maker
- `staging/visa_grants.csv` **citizenship_country**: Afghanistan, Albania, Algeria, Andorra, Angola, Anguilla, Antigua and Barbuda, Argentina, Armenia, Aruba, Australia, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bermuda, Bhutan, Bolivia, Bonaire, Saint Eustatius & Saba ... (232 values)
- `staging/visa_decisions.csv` **financial_year**: 2005-06, 2006-07, 2007-08, 2008-09, 2009-10, 2010-11, 2011-12, 2012-13, 2013-14, 2014-15, 2015-16, 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24, 2024-25, 2025-26
- `staging/visa_decisions.csv` **quarter**: Q1, Q2, Q3, Q4
- `staging/visa_decisions.csv` **month**: 1, 10, 11, 12, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/visa_decisions.csv` **client_location**: In Australia, Outside Australia
- `staging/visa_decisions.csv` **lodgement_channel**: Internet, Paper
- `staging/visa_decisions.csv` **sector**: Foreign Affairs or Defence Sector, Higher Education Sector, Independent ELICOS Sector, Non-Award Sector, Postgraduate Research Sector, Schools Sector, Vocational Education and Training Sector
- `staging/visa_decisions.csv` **applicant_type**: Primary, Secondary
- `staging/visa_decisions.csv` **provider_state**: ACT, NSW, NT, Not Available, QLD, SA, TAS, VIC, WA
- `staging/visa_decisions.csv` **gender**: Female, Male, Not Specified
- `staging/visa_decisions.csv` **age_group**: 0 to 4 years, 10 to 14 years, 15 to 19 years, 20 to 24 years, 25 to 29 years, 30 to 34 years, 35 to 39 years, 40 to 44 years, 45 to 49 years, 5 to 9 years, 50 to 54 years, 55 and over, Not Specified
- `staging/visa_decisions.csv` **citizenship_country**: Afghanistan, Albania, Algeria, Andorra, Angola, Anguilla, Antigua and Barbuda, Argentina, Armenia, Aruba, Australia, Austria, Azerbaijan, Bahamas, Bahrain, Bangladesh, Barbados, Belarus, Belgium, Belize, Benin, Bermuda, Bhutan, Bolivia, Bonaire, Saint Eustatius & Saba ... (233 values)
- `staging/abs_nom_financial_year.csv` **financial_year**: 2004-05, 2005-06, 2006-07, 2007-08, 2008-09, 2009-10, 2010-11, 2011-12, 2012-13, 2013-14, 2014-15, 2015-16, 2016-17, 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23
- `staging/abs_nom_financial_year.csv` **visa_group_code**: 1, 10, 11, 12, 13, 14, 15, 16, 17, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/abs_nom_financial_year.csv` **visa_group**: Australian Citizen, New Zealand Citizen (subclass 444), Other Visas, Permanent visa - Family, Permanent visa - Other permanent visas, Permanent visa - Skill, Permanent visa - Special Eligibility and humanitarian, Permanent visa - Total, Temporary visa - Higher education sector, Temporary visa - Other temporary visas, Temporary visa - Student other, Temporary visa - Temporary work (skilled), Temporary visa - Total, Temporary visa - Visitor, Temporary visa - Vocational Education and Training sector, Temporary visa - Working Holiday, Total
- `staging/abs_nom_financial_year.csv` **migration_type_code**: 1, 2
- `staging/abs_nom_financial_year.csv` **migration_type**: NOM arrivals, NOM departures
- `staging/abs_nom_financial_year.csv` **region_code**: 1, 2, 3, 4, 5, 6, 7, 8, AUS
- `staging/abs_nom_financial_year.csv` **region**: Australia, Australian Capital Territory, New South Wales, Northern Territory, Queensland, South Australia, Tasmania, Victoria, Western Australia
- `staging/abs_nom_financial_year.csv` **is_aggregate**: false, true
- `staging/abs_nom_calendar_year.csv` **calendar_year**: 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
- `staging/abs_nom_calendar_year.csv` **visa_group_code**: 1, 10, 11, 12, 13, 14, 15, 16, 17, 2, 3, 4, 5, 6, 7, 8, 9
- `staging/abs_nom_calendar_year.csv` **visa_group**: Australian Citizen, New Zealand Citizen (subclass 444), Other Visas, Permanent visa - Family, Permanent visa - Other permanent visas, Permanent visa - Skill, Permanent visa - Special Eligibility and humanitarian, Permanent visa - Total, Temporary visa - Higher education sector, Temporary visa - Other temporary visas, Temporary visa - Student other, Temporary visa - Temporary work (skilled), Temporary visa - Total, Temporary visa - Visitor, Temporary visa - Vocational Education and Training sector, Temporary visa - Working Holiday, Total
- `staging/abs_nom_calendar_year.csv` **migration_type_code**: 1, 2
- `staging/abs_nom_calendar_year.csv` **migration_type**: NOM arrivals, NOM departures
- `staging/abs_nom_calendar_year.csv` **region_code**: 1, 2, 3, 4, 5, 6, 7, 8, AUS
- `staging/abs_nom_calendar_year.csv` **region**: Australia, Australian Capital Territory, New South Wales, Northern Territory, Queensland, South Australia, Tasmania, Victoria, Western Australia
- `staging/abs_nom_calendar_year.csv` **is_aggregate**: false, true

## Raw layer integrity

- `bronze/homeaffairs-visas/homeaffairs_student-visas-lodged_asat-2026-06-30.xlsx`: ok
- `bronze/homeaffairs-visas/homeaffairs_student-visas-granted_asat-2026-06-30.xlsx`: ok
- `bronze/homeaffairs-visas/homeaffairs_student-visa-grant-rates_asat-2026-06-30.xlsx`: ok
- `bronze/homeaffairs-visas/homeaffairs_pivot-table-user-guide_v4.pdf`: ok
- `bronze/cricos-register/cricos_institutions_asat-2026-08-09.csv`: ok
- `bronze/cricos-register/cricos_courses_asat-2026-08-09.csv`: ok
- `bronze/cricos-register/cricos_locations_asat-2026-08-09.csv`: ok
- `bronze/cricos-register/cricos_course-locations_asat-2026-08-09.csv`: ok
- `bronze/cricos-register/cricos_providers-courses-locations_asat-2026-07-01.xlsx`: ok
- `bronze/abs-migration/abs_nom-arrivals-departures-by-visa_calendar-year.csv`: ok
- `bronze/abs-migration/abs_nom-arrivals-departures-by-visa_financial-year.csv`: ok
- `bronze/legislation-policy/homeaffairs_ministerial-direction-115_2025-11-14.pdf`: ok
- `bronze/education-international/education_intl-students-ytd-latest_2026-05.xlsx`: ok
- `bronze/education-international/education_intl-students-ytd-all_2026-05.xlsx`: ok
- `bronze/education-international/education_intl-students-summary-infographic_2026-05.pdf`: ok
- `bronze/education-higher-ed/education_he-student-enrolments-pivot_2024.xlsx`: ok
- `bronze/education-higher-ed/education_he-student-load-pivot_2024.xlsx`: ok
- `bronze/education-higher-ed/education_he-course-completions-pivot_2024.xlsx`: ok
- `bronze/education-higher-ed/education_he-student-summary-time-series_2024.xlsx`: ok
- `bronze/legislation-policy/legislation_overseas-students-titles_asat-2026-08-09.json`: ok

## Checks passed

- raw layer: 20/20 MANIFEST files match sha256
- to_number: <5/np/-/../* -> null, '0' -> 0, '1,234' -> 1234 (never marker -> 0)
- models.py allowed values parsed: {'institutions.provider_type': ['private', 'public'], 'fields_of_study.broad_field': ['STEM', 'Social Studies', 'other'], 'citizenship_statuses.status': ['domestic', 'international'], 'policies.category': ['education', 'immigration'], 'data_sources.source_type': ['api', 'csv', 'scrape']}
- institutions.csv: no index/Unnamed columns
- institutions.csv: no 'nan'/'None'/'<NA>' strings written 
- institutions.csv: no suppression markers left in measure columns 
- institutions.csv: cricos_provider_code matches \d{5}[A-Z] (text codes intact)
- institutions.csv: every row has source_file and every path is in MANIFEST.csv
- institutions.csv: no case/spacing variants of the same category 
- institutions.csv: columns == ['name', 'provider_type', 'state', 'sector', 'teqsa_id', 'cricos_provider_code', 'source_file']
- institutions.csv: name has no nulls (NOT NULL in institutions.name)
- institutions.csv: name <= 255 chars (max 69)
- institutions.csv: provider_type has no nulls (NOT NULL in institutions.provider_type)
- institutions.csv: provider_type <= 50 chars (max 7)
- institutions.csv: provider_type values ['private', 'public'] within models.py ['private', 'public']
- institutions.csv: state <= 10 chars (max 3)
- institutions.csv: sector <= 50 chars (max 0)
- institutions.csv: teqsa_id <= 50 chars (max 0)
- institutions.csv: load key ['name'] unique: 0 duplicates
- fields_of_study.csv: no index/Unnamed columns
- fields_of_study.csv: no 'nan'/'None'/'<NA>' strings written 
- fields_of_study.csv: no suppression markers left in measure columns 
- fields_of_study.csv: field_code matches \d{2} (text codes intact)
- fields_of_study.csv: every row has source_file and every path is in MANIFEST.csv
- fields_of_study.csv: no case/spacing variants of the same category 
- fields_of_study.csv: columns == ['name', 'broad_field', 'field_code', 'source_file']
- fields_of_study.csv: name has no nulls (NOT NULL in fields_of_study.name)
- fields_of_study.csv: name <= 255 chars (max 46)
- fields_of_study.csv: broad_field has no nulls (NOT NULL in fields_of_study.broad_field)
- fields_of_study.csv: broad_field <= 50 chars (max 14)
- fields_of_study.csv: broad_field values ['STEM', 'Social Studies', 'other'] within models.py ['STEM', 'Social Studies', 'other']
- fields_of_study.csv: field_code <= 20 chars (max 2)
- fields_of_study.csv: load key ['name'] unique: 0 duplicates
- citizenship_statuses.csv: no index/Unnamed columns
- citizenship_statuses.csv: no 'nan'/'None'/'<NA>' strings written 
- citizenship_statuses.csv: no suppression markers left in measure columns 
- citizenship_statuses.csv: every row has source_file and every path is in MANIFEST.csv
- citizenship_statuses.csv: no case/spacing variants of the same category 
- citizenship_statuses.csv: columns == ['status', 'country_of_origin', 'source_file']
- citizenship_statuses.csv: status has no nulls (NOT NULL in citizenship_statuses.status)
- citizenship_statuses.csv: status <= 20 chars (max 13)
- citizenship_statuses.csv: status values ['domestic', 'international'] within models.py ['domestic', 'international']
- citizenship_statuses.csv: country_of_origin <= 100 chars (max 0)
- citizenship_statuses.csv: load key ['status', 'country_of_origin'] unique: 0 duplicates
- enrollment_stats.csv: no index/Unnamed columns
- enrollment_stats.csv: no 'nan'/'None'/'<NA>' strings written 
- enrollment_stats.csv: no suppression markers left in measure columns 
- enrollment_stats.csv: student_count is a non-negative integer where present
- enrollment_stats.csv: field_code matches \d{2} (text codes intact)
- enrollment_stats.csv: every row has source_file and every path is in MANIFEST.csv
- enrollment_stats.csv: no case/spacing variants of the same category 
- enrollment_stats.csv: columns == ['institution_name', 'field_name', 'field_code', 'status', 'country_of_origin', 'year', 'student_count', 'source_file']
- enrollment_stats.csv: institution_name has no nulls (NOT NULL in enrollment_stats.institution_id)
- enrollment_stats.csv: field_name has no nulls (NOT NULL in enrollment_stats.field_of_study_id)
- enrollment_stats.csv: year has no nulls (NOT NULL in enrollment_stats.year)
- enrollment_stats.csv: year is integer
- enrollment_stats.csv: student_count has no nulls (NOT NULL in enrollment_stats.student_count)
- enrollment_stats.csv: student_count is integer
- enrollment_stats.csv: unique constraint uq_enrollment_grain on ['institution_name', 'field_name', 'status', 'country_of_origin', 'year']: 0 duplicates
- policies.csv: no index/Unnamed columns
- policies.csv: no 'nan'/'None'/'<NA>' strings written 
- policies.csv: no suppression markers left in measure columns 
- policies.csv: effective_date matches \d{4}-\d{2}-\d{2} (text codes intact)
- policies.csv: every row has source_file and every path is in MANIFEST.csv
- policies.csv: no case/spacing variants of the same category 
- policies.csv: columns == ['title', 'category', 'summary', 'full_text', 'effective_date', 'source_url', 'source_file']
- policies.csv: title has no nulls (NOT NULL in policies.title)
- policies.csv: title <= 500 chars (max 214)
- policies.csv: category has no nulls (NOT NULL in policies.category)
- policies.csv: category <= 50 chars (max 11)
- policies.csv: category values ['education', 'immigration'] within models.py ['education', 'immigration']
- policies.csv: effective_date is a YYYY-MM-DD date
- policies.csv: source_url <= 1000 chars (max 83)
- policies.csv: load key ['title', 'source_url'] unique: 0 duplicates
- data_sources.csv: no index/Unnamed columns
- data_sources.csv: no 'nan'/'None'/'<NA>' strings written 
- data_sources.csv: no suppression markers left in measure columns 
- data_sources.csv: retrieved_at matches \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (text codes intact)
- data_sources.csv: every row has source_file and every path is in MANIFEST.csv
- data_sources.csv: no case/spacing variants of the same category 
- data_sources.csv: columns == ['name', 'source_type', 'url', 'retrieved_at', 'license_notes', 'source_file']
- data_sources.csv: name has no nulls (NOT NULL in data_sources.name)
- data_sources.csv: name <= 255 chars (max 76)
- data_sources.csv: source_type has no nulls (NOT NULL in data_sources.source_type)
- data_sources.csv: source_type <= 50 chars (max 6)
- data_sources.csv: source_type values ['api', 'csv', 'scrape'] within models.py ['api', 'csv', 'scrape']
- data_sources.csv: url <= 1000 chars (max 192)
- data_sources.csv: retrieved_at has no nulls (NOT NULL in data_sources.retrieved_at)
- data_sources.csv: retrieved_at is a datetime
- data_sources.csv: load key ['source_file'] unique: 0 duplicates
- enrollment_stats: every institution_name exists in institutions.csv
- enrollment_stats: every (field_name, field_code) exists in fields_of_study.csv
- enrollment_stats: every citizenship key exists in citizenship_statuses.csv
- institutions.csv: every source_file resolves to a data_sources.csv row
- fields_of_study.csv: every source_file resolves to a data_sources.csv row
- citizenship_statuses.csv: every source_file resolves to a data_sources.csv row
- enrollment_stats.csv: every source_file resolves to a data_sources.csv row
- policies.csv: every source_file resolves to a data_sources.csv row
- staging/prisms_international_students_ytd.csv: no index/Unnamed columns
- staging/prisms_international_students_ytd.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/prisms_international_students_ytd.csv: no suppression markers left in measure columns 
- staging/prisms_international_students_ytd.csv: ytd_enrolments is a non-negative integer where present
- staging/prisms_international_students_ytd.csv: ytd_commencements is a non-negative integer where present
- staging/prisms_international_students_ytd.csv: every row has source_file and every path is in MANIFEST.csv
- staging/prisms_international_students_ytd.csv: no case/spacing variants of the same category 
- staging/prisms_international_students_ytd.csv: grain ['year', 'month', 'citizenship_country', 'state', 'sector', 'provider_type', 'new_to_australia', 'ends_this_year'] unique: 0 duplicates
- staging/visa_lodgements.csv: no index/Unnamed columns
- staging/visa_lodgements.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/visa_lodgements.csv: no suppression markers left in measure columns 
- staging/visa_lodgements.csv: lodged is a non-negative integer where present
- staging/visa_lodgements.csv: financial_year matches \d{4}-\d{2} (text codes intact)
- staging/visa_lodgements.csv: quarter matches Q[1-4] (text codes intact)
- staging/visa_lodgements.csv: financial_year labels are consecutive years
- staging/visa_lodgements.csv: every row has source_file and every path is in MANIFEST.csv
- staging/visa_lodgements.csv: no case/spacing variants of the same category 
- staging/visa_lodgements.csv: grain ['financial_year', 'quarter', 'month', 'client_location', 'lodgement_channel', 'sector', 'applicant_type', 'provider_state', 'gender', 'age_group', 'citizenship_country'] unique: 0 duplicates
- staging/visa_grants.csv: no index/Unnamed columns
- staging/visa_grants.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/visa_grants.csv: no suppression markers left in measure columns 
- staging/visa_grants.csv: granted is a non-negative integer where present
- staging/visa_grants.csv: financial_year matches \d{4}-\d{2} (text codes intact)
- staging/visa_grants.csv: quarter matches Q[1-4] (text codes intact)
- staging/visa_grants.csv: financial_year labels are consecutive years
- staging/visa_grants.csv: every row has source_file and every path is in MANIFEST.csv
- staging/visa_grants.csv: no case/spacing variants of the same category 
- staging/visa_grants.csv: grain ['financial_year', 'quarter', 'month', 'client_location', 'lodgement_channel', 'sector', 'applicant_type', 'provider_state', 'gender', 'age_group', 'last_visa_category', 'citizenship_country'] unique: 0 duplicates
- staging/visa_decisions.csv: no index/Unnamed columns
- staging/visa_decisions.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/visa_decisions.csv: no suppression markers left in measure columns 
- staging/visa_decisions.csv: granted is a non-negative integer where present
- staging/visa_decisions.csv: refused is a non-negative integer where present
- staging/visa_decisions.csv: financial_year matches \d{4}-\d{2} (text codes intact)
- staging/visa_decisions.csv: quarter matches Q[1-4] (text codes intact)
- staging/visa_decisions.csv: financial_year labels are consecutive years
- staging/visa_decisions.csv: every row has source_file and every path is in MANIFEST.csv
- staging/visa_decisions.csv: no case/spacing variants of the same category 
- staging/visa_decisions.csv: grain ['financial_year', 'quarter', 'month', 'client_location', 'lodgement_channel', 'sector', 'applicant_type', 'provider_state', 'gender', 'age_group', 'citizenship_country'] unique: 0 duplicates
- staging/abs_nom_financial_year.csv: no index/Unnamed columns
- staging/abs_nom_financial_year.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/abs_nom_financial_year.csv: no suppression markers left in measure columns 
- staging/abs_nom_financial_year.csv: persons is a non-negative integer where present
- staging/abs_nom_financial_year.csv: financial_year matches \d{4}-\d{2} (text codes intact)
- staging/abs_nom_financial_year.csv: visa_group_code matches \d{1,2} (text codes intact)
- staging/abs_nom_financial_year.csv: migration_type_code matches [12] (text codes intact)
- staging/abs_nom_financial_year.csv: region_code matches [1-8]|AUS (text codes intact)
- staging/abs_nom_financial_year.csv: financial_year labels are consecutive years
- staging/abs_nom_financial_year.csv: every row has source_file and every path is in MANIFEST.csv
- staging/abs_nom_financial_year.csv: no case/spacing variants of the same category 
- staging/abs_nom_financial_year.csv: grain ['financial_year', 'visa_group_code', 'migration_type_code', 'region_code'] unique: 0 duplicates
- staging/abs_nom_calendar_year.csv: no index/Unnamed columns
- staging/abs_nom_calendar_year.csv: no 'nan'/'None'/'<NA>' strings written 
- staging/abs_nom_calendar_year.csv: no suppression markers left in measure columns 
- staging/abs_nom_calendar_year.csv: persons is a non-negative integer where present
- staging/abs_nom_calendar_year.csv: visa_group_code matches \d{1,2} (text codes intact)
- staging/abs_nom_calendar_year.csv: migration_type_code matches [12] (text codes intact)
- staging/abs_nom_calendar_year.csv: region_code matches [1-8]|AUS (text codes intact)
- staging/abs_nom_calendar_year.csv: every row has source_file and every path is in MANIFEST.csv
- staging/abs_nom_calendar_year.csv: no case/spacing variants of the same category 
- staging/abs_nom_calendar_year.csv: grain ['calendar_year', 'visa_group_code', 'migration_type_code', 'region_code'] unique: 0 duplicates
- visas: granted by financial year agrees between grants and decisions workbooks (21 years)
- institutions.csv: report row count matches file (178)
- institutions.csv: duplicates after cleaning = 0
- fields_of_study.csv: report row count matches file (14)
- fields_of_study.csv: duplicates after cleaning = 0
- citizenship_statuses.csv: report row count matches file (2)
- citizenship_statuses.csv: duplicates after cleaning = 0
- enrollment_stats.csv: report row count matches file (4,381)
- enrollment_stats.csv: duplicates after cleaning = 0
- policies.csv: report row count matches file (138)
- policies.csv: duplicates after cleaning = 0
- data_sources.csv: report row count matches file (20)
- data_sources.csv: duplicates after cleaning = 0
- staging/prisms_international_students_ytd.csv: report row count matches file (3,583,979)
- staging/prisms_international_students_ytd.csv: duplicates after cleaning = 0
- staging/visa_lodgements.csv: report row count matches file (2,096,102)
- staging/visa_lodgements.csv: duplicates after cleaning = 0
- staging/visa_grants.csv: report row count matches file (2,292,011)
- staging/visa_grants.csv: duplicates after cleaning = 0
- staging/visa_decisions.csv: report row count matches file (2,064,231)
- staging/visa_decisions.csv: duplicates after cleaning = 0
- staging/abs_nom_financial_year.csv: report row count matches file (5,814)
- staging/abs_nom_financial_year.csv: duplicates after cleaning = 0
- staging/abs_nom_calendar_year.csv: report row count matches file (5,814)
- staging/abs_nom_calendar_year.csv: duplicates after cleaning = 0
- enrollment_stats: loaded 7,394,208 + quarantined 659,283 == raw 8,053,491
- PRISMS: 15 published YTD-May sector totals reproduced exactly
