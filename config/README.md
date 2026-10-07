# config/

Hand-reviewed mappings read by `transform/clean_*.py`. Every row marked `PROPOSED` still needs
team sign-off; the cleaning report lists them as warnings until the status is changed to `AGREED`.

| File | Used for | Rule |
|---|---|---|
| `asced_broad_field_map.csv` | `fields_of_study.broad_field` | ASCED broad field -> STEM / Social Studies / other. Codes come from the CRICOS course register. |
| `institution_crosswalk.csv` | `institutions`, `enrollment_stats` | HESSC institution name -> CRICOS provider code. Matched on the code, never on fuzzy names alone. |
| `country_map.csv` | staging visa / PRISMS tables | Only labels that differ between sources. Standard form = Department of Education (PRISMS) spelling. Unlisted labels pass through unchanged. |

Deliberately **not** mapped (ambiguous, left as the source label): Yugoslavia / Yugoslavia, Fed Republic of /
Serbia and Montenegro, Zaire, East Timor, Gaza Strip and West Bank / Gaza Strip / Palestine, State of /
Palestinian Authority, Other, United Kingdom (Other), United States (Territories), and the Home Affairs
travel-document categories (Refugee, Stateless Person, UN Convention Refugee, UNMIK Travel Document,
United Nations Organisation, Not Specified).
