# Five-year checks

Both planned subperiods have been run from the same input snapshot as the full
study. Each of the 24 cases starts again with $10,000; the second period does not
inherit holdings or capital from the first.

| Window | Actual dates | Price observations | Report folder |
| --- | --- | --- | --- |
| 2016-2020 | 2016-01-04 to 2020-12-31 | 1,259 | `reports/study/20261106T012503Z-1669ce24` |
| 2021-2025 | 2021-01-04 to 2025-12-31 | 1,255 | `reports/study/20261106T012508Z-d9f464da` |

Both runs are also stored in `data/study/study.sqlite`. There are now 72 cases
across the full-period run and these two subperiods. The input checksum was checked
before each run. Starting portfolio values were checked in all 48 new case exports.

To repeat either window:

```bash
python -m marketlens.run_study data/study/20261106T011415Z-bbbd01c9 --window 2016-2020
python -m marketlens.run_study data/study/20261106T011415Z-bbbd01c9 --window 2021-2025
```

These commands create new reports. They do not overwrite the saved runs or import
the new copies into SQLite automatically. Use `python -m marketlens.store_study`
with the new report folder if you want to import a repeated run.

The SQL comparison is documented in [the findings report](findings.md). These
results describe this asset selection and period, not future investment performance.
