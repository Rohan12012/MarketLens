# MarketLens

Version 1.0.0 · [Release checks](docs/release-check.md) · [Changelog](CHANGELOG.md)

Historical portfolio analysis with Python, SQL, and Streamlit. Explore stocks and
ETFs, compare a portfolio with a benchmark, and inspect a reproducible study of
concentration and rebalancing.

The study asks: **does restoring target weights change the returns and risk of a
concentrated portfolio?** It compares two allocations in AAPL, MSFT, and GOOGL
across three strategies, four cost rates, and three time windows: 72 cases.

## What the study found

At 10 basis points per dollar traded, buy-and-hold had the highest return in
2016–2020, while monthly rebalancing led in 2021–2025 and over 2016–2025. In the
second five-year window, daily led at zero cost but monthly led once costs were
included. Equal weighting did not always produce a smaller maximum drawdown.

These are descriptive results for three retrospectively selected companies, not
an investment recommendation. [Executive summary](docs/executive-summary.md) ·
[Findings and tables](docs/findings.md) · [Study design](docs/analysis-brief.md)

## Run locally

Developed and tested with Python 3.13. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m marketlens.build_study
python -m marketlens.record_validation
python -m streamlit run app.py
```

Building the study needs internet access and creates local data, reports, and a
SQLite database. Downloads may fail or be rate-limited by the provider. To open
just the portfolio tool, skip the build and validation commands. The Research
study page shows setup instructions until its database exists.

The written findings refer to the original saved snapshot. A new download may
contain provider revisions. Rebuilt results are displayed from their own runs;
the app does not replace missing results with sample numbers.

## Dashboard

**Portfolio analysis** starts with no assets. Search matches ticker prefixes,
ignoring case. Select a result to add it, or edit Assets directly. Blank weights
mean an equal allocation. The default request covers 50 years where available;
the first returned price is not necessarily the IPO date.

**Research study** reads the saved SQL results. Change cost assumptions, compare
periods and allocations, inspect rankings, and download CSVs or the findings.

**Validation**, inside Research study, shows the last recorded test run and actual
study checks. It displays timestamps and marks old evidence stale when checked
code or data changes. Tests are never executed automatically for visitors.

## Data and checks

Yahoo Finance prices are retrieved with yfinance. Current US listings come from
Nasdaq Trader's Nasdaq-listed and other-listed files. OTC and historical delisted
securities are not covered. Other listed instruments, such as preferreds or units,
can appear; listing coverage does not guarantee price availability.

The original snapshot has 2,514 observations for 2016–2025, with no missing cells.
All dates match the reference exchange calendar. Accounting checks reconcile each
case's holdings, returns, and trading fees. The rebuilt results match the original
recorded runs. Tests use synthetic examples with known answers and temporary
SQLite databases; they do not establish provider accuracy.

**Independent price verification remains open.** A preselected 12-point sample was
prepared, but the secondary-source probe returned a browser-verification page,
not comparable prices. No observation is marked independently verified.
[Date audit](docs/data-quality.md) · [Price-check status](docs/price-verification.md)

## Methods and limitations

The portfolio dashboard and CLI use daily rebalancing without fees. The separate
study supports buy-and-hold, monthly, and daily rebalancing with costs on purchases
plus sales. Starting purchases and terminal liquidation are excluded from study
costs. Fees come out of invested capital.

Prices are adjusted for splits and dividends. All assets must share a currency;
there is no FX conversion. The model uses fractional holdings and adjusted-close
execution prices. It excludes taxes, market impact, and actual fill reconstruction.
The study uses 252 trading days and a fixed 0% risk-free rate. Current stock
selection introduces hindsight and survivorship bias; three related stocks do
not establish broad diversification. No statistical significance or future
performance claim has been established. [Calculation notes](docs/methodology.md)

## Tests and commands

```bash
python -m unittest discover -s tests -v
```

Tests run without live market requests. To update the dashboard's evidence:

```bash
python -m marketlens.record_validation
```

[Command guide](docs/usage.md) · [Code walkthrough](docs/learning-guide.md) ·
[Interview guide](docs/interview-guide.md)

## Code map

| Location | Purpose |
| --- | --- |
| `app.py`, `pages/` | Portfolio, research, and validation views |
| `main.py` | Portfolio CLI and exports |
| `marketlens/data.py`, `securities.py` | Prices, listing lookup, validation, snapshots |
| `marketlens/analytics.py`, `simulation.py` | Returns, risk, holdings, and fee accounting |
| `marketlens/study.py`, `run_study.py` | Study combinations and window exports |
| `marketlens/store_study.py`, `docs/*.sql` | SQLite schema, imports, joins, and rankings |
| `marketlens/build_study.py` | One-command study setup |
| `marketlens/validation.py`, `record_validation.py` | Recorded test and data-quality evidence |
| `tests/` | Arithmetic, SQL, data, export, setup, and UI checks |

Exact development versions are in `requirements-lock.txt`; direct dependency ranges
are in `requirements.txt`. Generated data, reports, secrets, and environments are
excluded from Git. Yahoo data may be revised or unavailable. Review provider terms
before redistributing data or using it commercially.

## Sources

- [yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- [Nasdaq Trader directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [Exchange calendar reference](https://github.com/gerrymanoim/exchange_calendars)
- [Streamlit documentation](https://docs.streamlit.io/)
