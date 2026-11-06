# Trading-date audit

The study snapshot was checked against the XNYS regular-session calendar from
`exchange-calendars` 4.13.2 for January 1, 2016 through January 1, 2026, end exclusive.
This is a reference calendar for the selected US-market study, not a price source.

| Check | Result |
| --- | ---: |
| Expected sessions | 2,514 |
| Observed dates | 2,514 |
| Missing sessions | 0 |
| Unexpected dates | 0 |
| Input checksum matches snapshot metadata | Yes |

Matching counts alone would not be enough: one missing weekday and one extra
weekend row could cancel out. The audit compares the actual date sets in both
directions. It does not add rows, fill prices, or change the study snapshot.

The saved audit is `reports/quality/20261106T011415Z-bbbd01c9-calendar.json`.
Repeat it with:

```bash
python -m marketlens.audit_calendar data/study/20261106T011415Z-bbbd01c9
```

The command exits with status 1 if dates are missing or unexpected. Unit tests
cover a missing weekday, an unexpected weekend row, and the New Year holiday.

The calendar is maintained by the library's contributors and may be revised.
Record its version when repeating the audit. A matching schedule does not verify
price accuracy, corporate-action adjustments, or whether an individual security
was halted on a session. Independent price checks are still outstanding.

Reference: [exchange-calendars](https://github.com/gerrymanoim/exchange_calendars).
