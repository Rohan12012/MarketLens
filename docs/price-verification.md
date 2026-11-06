# Independent price check: open

A fixed sample was selected before fetching the secondary source:

- Securities: AAPL, MSFT, GOOGL, SPY.
- Dates: January 4, 2016; August 31, 2020; December 31, 2025.
- Total: 12 observations.

The dates cover the study's first observation, an intermediate corporate-action
case, and its final observation. Apple began split-adjusted trading for its 2020
four-for-one split on August 31, according to [Apple's announcement](https://www.apple.com/newsroom/2020/07/apple-reports-third-quarter-results/).
This fact explains the sample choice; it does not independently verify Yahoo's prices.

## Access result

The public Stooq daily-CSV endpoint was probed for AAPL. It returned HTTP 200 with
`text/html` content containing a browser-verification challenge, not price rows.
No challenge was bypassed. The saved response and its hash are local evidence of
the access attempt, not a second set of market observations.

The CSV in `reports/quality/price-check-sample.csv` contains the 12 Yahoo adjusted
closes. Reference prices and differences are blank. Every row is **Not verified**.
`reports/quality/price-verification.json` records the endpoint, timestamp, response
hash, and outcome. Raw source responses stay under ignored `data/verification/`.

Stooq's adjustment basis was not confirmed during this check. Even a successful
CSV response would not establish that its Close field is equivalent to Yahoo's
split-and-dividend-adjusted close. A valid reconciliation needs a documented
matching convention, or an explicit adjustment method with supporting action data.
[Alpha Vantage's documentation](https://www.alphavantage.co/documentation/) similarly
distinguishes raw daily and adjusted endpoints; they cannot be compared blindly.

## Repeat the access probe

```bash
python -m marketlens.price_verification data/study/20261106T011415Z-bbbd01c9
```

It may produce a different access response later. The command never marks prices
verified just because a request succeeds. To finish this check, obtain an accessible,
documented second source, compare the preselected observations, and investigate
differences. No paid account or credentials were requested for this release.
