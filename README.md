# MarketLens

Compare a weighted stock portfolio with a market benchmark using historical daily
prices. MarketLens calculates returns and risk, plots performance in Streamlit,
and saves the inputs and settings needed to repeat an analysis.

The main question is: **How did a chosen allocation perform relative to its
benchmark, and how much risk did it take?**

## Run locally

Developed with Python 3.13. From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

Open the URL printed in the terminal. Enter ticker symbols, choose dates and
weights, and click **Run analysis**. Blank weights use equal allocations.
The first analysis requires an internet connection to Yahoo Finance.

To search by company or fund name, expand **Find US stocks & ETFs** and click
**Load / refresh listing directory**. Filter by exchange or ETF status, select
securities, then click **Use selected assets**. This replaces the Assets field;
weights follow that field's ticker order. You can also type symbols directly.

The directory combines Nasdaq Trader's Nasdaq-listed and other-exchange-listed
files, excluding test issues. It covers current listings from those feeds, not
historical delistings or OTC securities. The non-ETF category also includes
preferreds, warrants, units, and other listed securities. Some symbols may not have
Yahoo price coverage. Share-class dots are converted to hyphens (`BRK.B` → `BRK-B`);
other instrument suffixes may need a manually entered provider symbol. Directory
data is cached for one day; clicking refresh after loading requests a fresh copy.

The default history range requests the last 50 years. **Individual history** shows
each security's actual returned coverage. **Custom dates** uses the date inputs.
The first available price is not a verified IPO date; provider history can begin later.

`requirements-lock.txt` records the development environment. `requirements.txt`
lists the direct dependencies and their supported version ranges.

## What it does

- Downloads adjusted daily close prices through yfinance.
- Searches current US listings by ticker or security name, with exchange and ETF filters.
- Requests up to 50 years and preserves individual security histories.
- Rejects missing, nonpositive, or infinite prices and duplicate or unsorted dates.
- Compares a long-only portfolio with one benchmark over the same observations.
- Calculates total return, annualized return and volatility, Sharpe ratio,
  maximum drawdown, and asset return correlations.
- Displays portfolio value, drawdowns, and allocations; exports prices and metrics.
- Saves timestamped snapshots and reports through the command line.

## Run an analysis from the terminal

```bash
python main.py \
  --tickers AAPL,MSFT,GOOGL \
  --weights 0.4,0.3,0.3 \
  --benchmark SPY \
  --start 2024-01-01 \
  --end 2025-01-01
```

The end date is exclusive. Weights must be nonnegative and sum to 1.
Without explicit dates, the CLI requests the last 50 years through the exclusive
current New York date. Use `--years 10` for a shorter lookback.
Optional arguments include `--initial-value 10000` and `--risk-free 0.04`.
The risk-free rate is an annual decimal: `0.04` means 4%. The dashboard accepts
that rate as a percentage instead. Run `python main.py --help` for all options.

Each successful run writes two folders with the same run ID:

| Folder | Contents |
| --- | --- |
| `data/snapshots/<run-id>/` | Shared prices, full available history, per-security coverage, and metadata with package versions and a shared-price CSV checksum |
| `reports/<run-id>/` | Portfolio and asset metrics, daily returns, portfolio values, drawdowns, correlations, and analysis settings |

Repeat an analysis using the saved data:

```bash
python main.py \
  --input data/snapshots/<run-id>/prices.csv \
  --tickers AAPL,MSFT,GOOGL \
  --weights 0.4,0.3,0.3 \
  --benchmark SPY
```

Replace `<run-id>` with a folder created by a previous run. Offline mode uses all
rows in the supplied file; `--start` and `--end` apply only to downloads.

The dashboard also accepts a saved `prices.csv`. It must have one header row,
a `Date` column, and an adjusted-close column for every asset and the benchmark.
The early tutorial file `data/raw/AAPL.csv` uses a different, multirow header and
cannot be loaded directly.

## Portfolio assumptions

This is a historical model with **daily rebalancing**: target weights are restored
each day. It excludes trading costs, slippage, taxes, deposits, withdrawals, and
currency conversion. Assets must share a currency. It does not track actual holdings.

Returns use provider-adjusted prices for splits and dividends. Individual histories
are preserved, while portfolio comparisons use the dates shared by every selected
asset and the benchmark. A newer asset or benchmark can shorten the comparison.
No pre-listing prices are filled or invented. Missing observations inside each
security's available history or inside the shared comparison stop the analysis.

Annualized figures assume 252 trading days. Estimates from short samples can be
unstable, and choosing today's stocks to study the past can introduce selection
and survivorship bias. Validation checks data structure, not provider accuracy.

See [the calculation notes](docs/methodology.md) for formulas and edge cases.
Historical results are not forecasts.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests cover known return calculations, first-day drawdowns, invalid prices and
weights, snapshot round trips, CLI exports, and dashboard interactions. They use
synthetic arithmetic examples and mocked downloads, so no network is required.
GitHub Actions runs the suite on pushes and pull requests.

## Code map

| File | Responsibility |
| --- | --- |
| `main.py` | CLI arguments, snapshots, and report exports |
| `app.py` | Dashboard inputs, charts, and downloads |
| `marketlens/data.py` | Price retrieval, validation, and snapshot metadata |
| `marketlens/securities.py` | US listing directory, caching, and name/ticker search |
| `marketlens/analytics.py` | Returns, portfolio calculations, and risk metrics |
| `tests/` | Calculation, validation, CLI, and dashboard tests |

The [learning guide](docs/learning-guide.md) walks through the code. An optional
[SQL exercise](docs/analysis.sql) summarizes exported daily returns; the application
itself uses pandas, not a database.

Generated data, reports, and the virtual environment are excluded from Git.
Yahoo Finance data may be revised or unavailable, and requests may be rate-limited.
yfinance is an unofficial library; check the provider's terms before redistributing
data or using it commercially.

References: [yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
and [Streamlit documentation](https://docs.streamlit.io/).
Listing fields: [Nasdaq Trader symbol directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs).
