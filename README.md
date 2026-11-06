# MarketLens

MarketLens compares a stock or ETF portfolio with a benchmark using historical
prices. The dashboard shows returns, drawdowns, volatility, and correlations.
The command-line tool saves the data and settings alongside its reports.

A separate study is in progress: how do concentrated allocations and rebalancing
frequency change returns and risk? The full-period and five-year comparisons are complete;
[the first findings report](docs/findings.md) is available. See [the study plan](docs/analysis-brief.md)
and [the run record](docs/study-run.md).

## Run it

Developed with Python 3.13. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

Open the local URL printed in the terminal. Search for a ticker, select a result,
and click **Run analysis**. Assets start empty. Leave weights blank for an equal
allocation, or enter decimal weights in the same order as the tickers.

Search matches the start of the ticker, ignoring case. Names appear in results
but are not searched. Edit **Assets** to remove a selection or enter a symbol
manually. The listing directory loads automatically and is cached for one day.

The default request covers 50 years. Newer securities use whatever history the
provider returns. The portfolio comparison uses the dates shared by every asset
and the benchmark. **Asset history** shows each security's longer individual
history. Its first returned price is not necessarily its IPO date.

For a specific period, select **Custom dates** and enter dates in that section.
**Portfolio settings** contains weights, benchmark, capital, and the risk-free rate.
**Import saved prices** lets you run from a previous snapshot without downloading
prices again. The directory search still needs a connection or a local cache.

## Command line

```bash
python main.py \
  --tickers AAPL,MSFT,GOOGL \
  --weights 0.4,0.3,0.3 \
  --benchmark SPY \
  --start 2024-01-01 \
  --end 2025-01-01
```

The end date is exclusive. Weights must be nonnegative and sum to 1. Without dates,
the request runs from 50 years ago to today in New York, excluding today's session.
Use `--years 10` for a shorter lookback.

`--initial-value` defaults to 10000. `--risk-free 0.04` means a 4% annual rate;
the dashboard accepts percentages instead, so enter `4` there. Run
`python main.py --help` for all arguments.

A successful run creates matching folders:

| Location | Files |
| --- | --- |
| `data/snapshots/<run-id>/` | Shared prices, full available history, coverage, and source metadata |
| `reports/<run-id>/` | Metrics, daily returns, portfolio values, drawdowns, correlations, and settings |

Metadata includes observation dates, retrieval time, package versions, and a
checksum of the shared prices file. To repeat a run with saved prices:

```bash
python main.py \
  --input data/snapshots/<run-id>/prices.csv \
  --tickers AAPL,MSFT,GOOGL \
  --weights 0.4,0.3,0.3 \
  --benchmark SPY
```

Replace `<run-id>` with an existing folder. Offline mode uses every row in the
file; date arguments apply only to downloads. Both the CLI and dashboard expect
one header row, a `Date` column, and one adjusted-close column per asset and
benchmark. The early tutorial file `data/raw/AAPL.csv` has multiple header rows
and cannot be loaded directly.

## Assumptions

The dashboard and CLI model daily rebalancing without trading costs, taxes,
slippage, deposits, or withdrawals. All assets must use the same currency; there
is no currency conversion. This is a model portfolio, not a record of actual trades.

Prices are adjusted by the provider for splits and dividends. The downloader
checks for missing, infinite, and nonpositive prices, duplicate dates, and date
order. It rejects gaps within an asset's history and within the shared comparison
period. The study snapshot also matches all expected dates in a separate
[calendar audit](docs/data-quality.md). Passing these checks does not prove that
prices are correct.

Annualization assumes 252 trading days. Short samples can give unstable estimates.
Picking current stocks to study the past also introduces selection and survivorship
bias. See [the calculation notes](docs/methodology.md) for the formulas.

The listing directory comes from Nasdaq Trader's Nasdaq-listed and other-listed
files. It excludes test issues, historical delistings, and OTC securities. It also
contains preferreds, warrants, and units. Listing coverage does not guarantee Yahoo
price coverage. Share-class dots are changed to hyphens (`BRK.B` becomes `BRK-B`);
other suffixes may need a manually entered provider symbol.

Yahoo data may be revised, unavailable, or rate-limited. yfinance is unofficial.
Check the provider's terms before redistributing data or using it commercially.

## Tests and code

```bash
python -m unittest discover -s tests -v
```

Tests use made-up prices with known answers and mocked downloads. They cover
returns, fee accounting, trading dates, validation, saved files, study combinations,
and dashboard interactions. They do not need a network connection. GitHub Actions
runs the same suite on pushes and pull requests.

| File | Purpose |
| --- | --- |
| `app.py` | Dashboard |
| `main.py` | CLI and report exports |
| `marketlens/data.py` | Price downloads, validation, and snapshots |
| `marketlens/securities.py` | Listing directory and ticker lookup |
| `marketlens/analytics.py` | Dashboard returns and risk calculations |
| `marketlens/simulation.py` | Buy-and-hold, monthly, and daily strategies with turnover and costs |
| `marketlens/study.py` | The 24-case allocation and strategy comparison |
| `marketlens/store_study.py` | SQLite imports and cost-scenario queries |

`requirements-lock.txt` records the installed development versions.
`requirements.txt` lists direct dependencies with version ranges. Data, reports,
and the virtual environment are excluded from Git.

The [code walkthrough](docs/learning-guide.md) is a starting point for reading the
project. Study reports can now be loaded into SQLite:

```bash
python -m marketlens.store_study reports/study/20261106T011618Z-d2aba2dd
```

This stores the run and its 24 cases in `data/study/study.sqlite`, then runs
[the SQL comparison](docs/analysis.sql) at 10 basis points. The query joins each
scenario to its zero-cost baseline. Ending-value reduction includes the effect
of fees on later returns, so it can differ from the dollar fees paid.
The [schema](docs/study-schema.sql) defines keys, relationships, and constraints.
Price calculations still run in Python; SQL stores and queries the study results.

## Sources

- [yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
- [Nasdaq Trader directory fields](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [Streamlit documentation](https://docs.streamlit.io/)
