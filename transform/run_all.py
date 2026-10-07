"""Rebuild data/processed/ from the raw layer and validate it.

    python transform/run_all.py

Order matters: institutions before enrolments (enrolments check institution names).
Takes about 15 minutes; the pivot workbooks hold ~10M records between them.
"""

import sys

import clean_abs_nom
import clean_data_sources
import clean_enrolments
import clean_institutions
import clean_policies
import clean_prisms
import clean_visas
import validate_processed

for step in (clean_data_sources, clean_institutions, clean_enrolments, clean_policies,
             clean_abs_nom, clean_visas, clean_prisms):
    step.main()
sys.exit(validate_processed.main())
