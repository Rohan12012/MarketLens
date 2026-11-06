"""MarketLens dashboard. Start with: python -m streamlit run app.py."""
from datetime import date
from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st

from marketlens.analytics import analyze, summarize, validate_weights
from marketlens.charts import allocation_chart, comparison_chart
from marketlens.data import download_history, align_history, history_window, load_prices, parse_symbols
from marketlens.securities import load_directory, search_directory

history_start, history_end = history_window()
if 'portfolio_tickers' not in st.session_state:
    st.session_state['portfolio_tickers'] = 'AAPL,MSFT,GOOGL'

st.set_page_config(page_title='MarketLens | Portfolio research', page_icon='◈', layout='wide')
st.markdown(f'<style>{Path(__file__).with_name("dashboard.css").read_text()}</style>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand-mark">◈ &nbsp; MARKETLENS</div>', unsafe_allow_html=True)
    st.caption('PORTFOLIO RESEARCH')
    st.divider()
    with st.expander('Find US stocks & ETFs'):
        if st.button('Load / refresh listing directory', key='load_directory'):
            try:
                with st.spinner('Loading current US listings…'):
                    st.session_state['directory'], st.session_state['directory_time'] = load_directory(refresh='directory' in st.session_state)
            except Exception as exc:
                st.warning(f'Directory unavailable: {exc}. You can still enter ticker symbols below.')
        if 'directory' in st.session_state:
            directory = st.session_state['directory']
            query = st.text_input('Search company, fund, or ticker', key='security_search')
            exchange = st.selectbox('Listing exchange', ['All exchanges'] + sorted(directory['Exchange'].unique()))
            kind = st.selectbox('Security type', ['All types', 'ETF', 'Stock / other'])
            matches = search_directory(directory, query, exchange, kind)
            st.caption(f'{len(matches):,} matches · directory retrieved {st.session_state["directory_time"][:10]}')
            names = directory.set_index('Price symbol')['Name'].to_dict()
            selected = st.multiselect('Add assets to portfolio', matches['Price symbol'].drop_duplicates().tolist(),
                                      format_func=lambda symbol: f'{symbol} — {names[symbol]}', key='catalog_assets')
            if st.button('Use selected assets', disabled=not selected):
                st.session_state['portfolio_tickers'] = ','.join(selected)
            st.caption('Current listings only. Stock / other also includes preferreds, units, and warrants. Provider symbol support varies.')
        else:
            st.caption('Load the current directory to search by company or fund name across US listing exchanges.')
    with st.form('analysis_settings'):
        st.subheader('Build your portfolio')
        tickers = st.text_input('Assets', key='portfolio_tickers', help='Comma-separated ticker symbols in the same currency. Directory selections replace this field.')
        weight_text = st.text_input('Target weights', '', placeholder='Equal weight by default', help='Decimals in ticker order, e.g. 0.4,0.3,0.3. Must sum to 1.')
        benchmark_text = st.text_input('Benchmark', 'SPY')
        history_mode = st.selectbox('History range', ['Last 50 years', 'Custom dates'])
        left, right = st.columns(2)
        start = left.date_input('Custom start', date.fromisoformat(history_start), min_value=date(1900, 1, 1))
        end = right.date_input('Custom end', date.fromisoformat(history_end), min_value=date(1900, 1, 1), help='Exclusive: this date is not included. These inputs apply to Custom dates only.')
        st.caption('Newer assets use available history. The comparison uses the period shared by every asset and the benchmark.')
        with st.expander('Capital & assumptions'):
            capital = st.number_input('Initial investment ($)', min_value=1., value=10000., step=1000.)
            risk_free = st.number_input('Annual risk-free rate (%)', min_value=0., max_value=100., value=0., step=.25)
            st.caption('Daily rebalancing. No trading costs, taxes, or currency conversion.')
        with st.expander('Use a saved dataset'):
            upload = st.file_uploader('Upload prices.csv', type='csv', help='One Date column and an adjusted-close column for each ticker, including the benchmark.')
            st.caption('Uploaded data uses all dates in the file, overriding the date selection.')
        submitted = st.form_submit_button('Run analysis', type='primary', width='stretch', key='run_analysis')
    st.caption('Yahoo Finance via yfinance · daily adjusted closes')

st.markdown('<div class="eyebrow">RESEARCH WORKSPACE / PORTFOLIO ANALYSIS</div>', unsafe_allow_html=True)
st.title('MarketLens')
st.markdown('<p class="page-intro">Understand the return. See the risk.</p>', unsafe_allow_html=True)

if submitted:
    try:
        assets = parse_symbols(tickers)
        benchmarks = parse_symbols(benchmark_text)
        if len(benchmarks) != 1:
            raise ValueError('Choose exactly one benchmark.')
        benchmark = benchmarks[0]
        weights = [float(w) for w in weight_text.split(',')] if weight_text.strip() else [1 / len(assets)] * len(assets)
        validate_weights(assets, weights)
        with st.spinner('Retrieving prices and calculating results…'):
            requested_start, requested_end = ((history_start, history_end) if history_mode == 'Last 50 years'
                                               else (start.isoformat(), end.isoformat()))
            full_history = (load_prices(StringIO(upload.getvalue().decode('utf-8'))) if upload else
                            download_history(list(dict.fromkeys(assets + [benchmark])), requested_start, requested_end))
            prices, coverage = align_history(full_history)
            result = analyze(prices, assets, weights, benchmark, capital, risk_free / 100)
        st.session_state['analysis'] = (prices, result, assets, weights, benchmark, bool(upload))
        st.session_state['full_history'] = full_history
        st.session_state['coverage'] = coverage
        st.session_state['analysis_risk_free'] = risk_free / 100
    except Exception as exc:
        st.session_state.pop('analysis', None)
        st.session_state.pop('full_history', None)
        st.session_state.pop('coverage', None)
        st.error(f'Analysis could not run: {exc}')

if 'analysis' not in st.session_state:
    st.divider()
    with st.container(border=True):
        st.markdown('<div class="eyebrow">START AN ANALYSIS</div>', unsafe_allow_html=True)
        st.header('A clearer view of your allocation.')
        st.write('Compare your portfolio with a benchmark, examine its worst declines, and inspect the prices behind the results.')
        st.caption('Choose assets and a date range in the sidebar, then select Run analysis.')
    for column, number, title, description in zip(
        st.columns(3), ['01', '02', '03'],
        ['Choose an allocation', 'Compare performance', 'Inspect the risk'],
        ['Enter tickers and target weights. Blank weights split capital equally.',
         'Track portfolio and benchmark growth from the same starting value.',
         'Review volatility, drawdowns, and how asset returns move together.']):
        with column:
            st.markdown(f'<div class="step-number">{number}</div>', unsafe_allow_html=True)
            st.subheader(title)
            st.write(description)
    st.caption('Historical model · daily rebalanced · trading costs and taxes excluded')
    st.stop()

prices, result, assets, weights, benchmark, offline = st.session_state['analysis']
# Keep an already-open dashboard session usable after an application update.
if 'full_history' not in st.session_state:
    st.session_state['full_history'] = prices
    st.session_state['coverage'] = align_history(prices)[1]
metrics = result['metrics']
source = 'Uploaded snapshot' if offline else 'Yahoo Finance'
st.caption(f'{prices.index[0]:%d %b %Y} — {prices.index[-1]:%d %b %Y}  ·  {len(prices):,} observations  ·  {source}  ·  Benchmark: {benchmark}')
st.divider()

metric_specs = [
    ('Total return', 'Change over the selected period'),
    ('Annualized volatility', 'Daily variability, scaled to one year'),
    ('Max drawdown', 'Largest decline from a previous peak'),
    ('Sharpe ratio', 'Excess return per unit of volatility'),
]
for column, (metric, explanation) in zip(st.columns(4), metric_specs):
    value = metrics.loc['Portfolio', metric]
    formatted = 'N/A' if pd.isna(value) else (f'{value:.2f}' if metric == 'Sharpe ratio' else f'{value:.2%}')
    with column.container(border=True):
        st.metric(metric, formatted, help=explanation)
        st.caption(explanation)

performance, risk, history_tab, data = st.tabs(['Overview', 'Risk analysis', 'Individual history', 'Data & downloads'])
with performance:
    main_column, allocation_column = st.columns([3, 1], gap='large')
    with main_column.container(border=True):
        heading, ending = st.columns([2, 1])
        heading.subheader('Portfolio growth')
        heading.caption('Same initial investment · daily rebalanced')
        ending.markdown(f'**${result["portfolio_value"]["Portfolio"].iloc[-1]:,.2f}**')
        ending.caption('Ending portfolio value')
        st.altair_chart(comparison_chart(result['portfolio_value']), width='stretch', theme=None)
    with allocation_column.container(border=True):
        st.subheader('Allocation')
        st.caption(f'{len(assets)} assets · target weights')
        st.altair_chart(allocation_chart(assets, weights), width='stretch', theme=None)
        st.caption('Weights are restored each trading day in this model.')
    st.subheader('Performance comparison')
    display_metrics = metrics.rename(index={'Benchmark': benchmark})
    formats = {c: ('{:.2f}' if c == 'Sharpe ratio' else '{:.2%}') for c in metrics.columns}
    st.dataframe(display_metrics.style.format(formats, na_rep='—'), width='stretch')
    with st.expander('Asset performance'):
        st.dataframe(result['asset_metrics'].style.format(formats, na_rep='—'), width='stretch')
with risk:
    with st.container(border=True):
        st.subheader('Below the previous peak')
        st.caption('Drawdown includes the initial investment. Zero means the series is at its high.')
        st.altair_chart(comparison_chart(result['drawdown'], percentage=True, height=300), width='stretch', theme=None)
    st.subheader('How assets move together')
    st.caption('Daily return correlation · +1 moves together · 0 has no linear relationship · −1 moves oppositely')
    st.dataframe(result['correlation'].style.format('{:.2f}', na_rep='—'), width='stretch')
with history_tab:
    st.subheader('Available history by security')
    st.caption('First available is the earliest price returned for the requested window, not a verified IPO date. Provider coverage can begin later than listing.')
    st.dataframe(st.session_state['coverage'], hide_index=True, width='stretch')
    full_history = st.session_state['full_history']
    history_symbol = st.selectbox('View price history', full_history.columns.tolist())
    individual = full_history[history_symbol].dropna().rename('Adjusted close')
    st.caption(f'{history_symbol} · {individual.index[0]:%d %b %Y} — {individual.index[-1]:%d %b %Y}')
    st.line_chart(individual, color='#45C4A0', width='stretch')
    individual_metrics = pd.DataFrame([summarize(individual.pct_change(fill_method=None).iloc[1:],
                                                st.session_state.get('analysis_risk_free', 0.))],
                                      index=[history_symbol])
    st.dataframe(individual_metrics.style.format(formats, na_rep='—'), width='stretch')
    st.caption('These metrics use this security’s full returned history, rather than the shorter portfolio comparison period.')
    st.download_button('Export individual history ↓', individual.to_csv(index_label='Date'),
                       f'{history_symbol}_history.csv', 'text/csv')
with data:
    st.subheader('Underlying prices')
    st.caption('Provider-adjusted daily closes. Missing, infinite, and nonpositive prices are rejected; no values are filled.')
    st.dataframe(prices.sort_index(ascending=False).style.format('{:,.2f}'), width='stretch')
    st.caption('Portfolio results use the shared date range shown above. Earlier individual history remains available in the Individual history tab.')
    download_prices_column, download_metrics_column, _ = st.columns([1, 1, 2])
    download_prices_column.download_button('Export prices ↓', prices.to_csv(index_label='Date'), 'prices.csv', 'text/csv', width='stretch')
    download_metrics_column.download_button('Export metrics ↓', metrics.to_csv(), 'metrics.csv', 'text/csv', width='stretch')

st.divider()
st.caption('MODEL NOTES  ·  Daily rebalancing · 252 trading days per year · Costs and taxes excluded · No FX conversion')
with st.expander('How to interpret these results'):
    st.write('Adjusted prices reflect provider adjustments for splits and dividends. Annualized estimates can be unstable over short periods. Sharpe uses the chosen risk-free rate converted to daily. All assets must share a currency. Historical results are not forecasts.')
