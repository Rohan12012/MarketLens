"""MarketLens dashboard. Start with: python -m streamlit run app.py."""
from datetime import date
from io import StringIO
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from marketlens.analytics import analyze, summarize, validate_weights
from marketlens.charts import allocation_chart, comparison_chart, correlation_chart
from marketlens.data import download_history, align_history, history_window, load_prices, parse_symbols
from marketlens.securities import load_directory

history_start, history_end = history_window()
if 'portfolio_tickers' not in st.session_state:
    st.session_state['portfolio_tickers'] = ''
# Clear the old starter tickers once for sessions opened before the update.
if 'empty_portfolio_default' not in st.session_state:
    if st.session_state['portfolio_tickers'] == 'AAPL,MSFT,GOOGL':
        st.session_state['portfolio_tickers'] = ''
    st.session_state['empty_portfolio_default'] = True

st.set_page_config(page_title='MarketLens | Portfolio research', page_icon='◈', layout='wide')
st.markdown(f'<style>{Path(__file__).with_name("dashboard.css").read_text()}</style>', unsafe_allow_html=True)

def add_search_selection():
    """Add the selected ticker, then clear the search."""
    symbol = st.session_state.get('ticker_search')
    if not symbol:
        return
    try:
        text = st.session_state['portfolio_tickers'].strip()
        assets = parse_symbols(text) if text else []
        if symbol in assets:
            st.session_state['search_notice'] = ('info', f'{symbol} is already in your portfolio.')
        else:
            st.session_state['portfolio_tickers'] = ','.join(assets + [symbol])
            st.session_state['search_notice'] = ('success', f'Added {symbol}')
    except ValueError:
        st.session_state['search_notice'] = ('warning', 'Check the symbols in Assets before adding another.')
    st.session_state['ticker_search'] = None


with st.sidebar:
    st.markdown('<div class="brand-mark">◈ &nbsp; MARKETLENS</div>', unsafe_allow_html=True)
    st.caption('PORTFOLIO RESEARCH')
    st.divider()
    try:
        if 'directory' not in st.session_state:
            with st.spinner('Loading securities…'):
                st.session_state['directory'], _ = load_directory()
        directory = st.session_state['directory'].drop_duplicates('Price symbol')
        labels = {row['Price symbol']: f"{row['Symbol']} — {row['Name']} · {'ETF' if row['Type'] == 'ETF' else 'Listed security'}"
                  for row in directory.to_dict('records')}
        st.selectbox('Search stocks & ETFs', directory['Price symbol'].tolist(),
                     index=None, key='ticker_search', placeholder='Type a ticker, e.g. AAPL',
                     format_func=lambda symbol: labels.get(symbol, symbol), filter_mode='prefix',
                     on_change=add_search_selection, icon=':material/search:')
    except Exception as exc:
        st.warning(f'Search is unavailable: {exc}. Enter tickers in Assets below.')
    if 'search_notice' in st.session_state:
        kind, message = st.session_state.pop('search_notice')
        getattr(st, kind)(message)
    with st.form('analysis_settings'):
        st.subheader('Build your portfolio')
        tickers = st.text_input('Assets', key='portfolio_tickers', placeholder='Select a stock or ETF above', help='Your selected tickers, in weight order. Edit this list to remove assets or enter symbols directly.')
        history_mode = st.selectbox('History range', ['Last 50 years', 'Custom dates'])
        st.caption('Leave weights blank to split capital equally.')
        with st.expander('Custom dates'):
            left, right = st.columns(2)
            start = left.date_input('Start', date.fromisoformat(history_start), min_value=date(1900, 1, 1))
            end = right.date_input('End', date.fromisoformat(history_end), min_value=date(1900, 1, 1))
            st.caption('Choose Custom dates above to use this range. The end date is excluded.')
        with st.expander('Portfolio settings'):
            weight_text = st.text_input('Target weights', '', key='portfolio_weights', placeholder='Equal weight', help='Decimals in Assets order, e.g. 0.4,0.3,0.3. Must sum to 1.')
            benchmark_text = st.text_input('Benchmark', 'SPY')
            capital = st.number_input('Initial investment ($)', min_value=1., value=10000., step=1000.)
            risk_free = st.number_input('Annual risk-free rate (%)', min_value=0., max_value=100., value=0., step=.25)
        with st.expander('Import saved prices'):
            upload = st.file_uploader('Upload prices.csv', type='csv', help='One Date column and an adjusted-close column for each ticker and the benchmark.')
            st.caption('Uses every date in the uploaded file.')
        submitted = st.form_submit_button('Run analysis', type='primary', width='stretch', key='run_analysis')
    st.caption('Yahoo Finance via yfinance · daily adjusted closes')

st.markdown('<div class="workspace-bar"><span>PORTFOLIO</span><span class="mode-pill">HISTORICAL DATA</span></div>', unsafe_allow_html=True)
st.title('MarketLens')
st.markdown('<p class="page-intro">Historical returns and risk, compared with your benchmark.</p>', unsafe_allow_html=True)

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
    with st.container(border=True):
        st.markdown('<div class="empty-hero"><div class="empty-icon">↗</div><div class="eyebrow">NO ASSETS YET</div><h2>Add your first<br>stock or ETF.</h2><p>Search for a ticker on the left to build your allocation.<br>Then run an analysis to compare its returns and risk.</p><div class="empty-tag">Up to 50 years, depending on available data</div></div>', unsafe_allow_html=True)
    for column, icon, title, description in zip(
        st.columns(3), ['↗', '◷', '⇄'],
        ['Performance', 'Downside risk', 'Benchmark comparison'],
        ['Follow the growth of your chosen allocation over time.',
         'See the depth of past declines and day-to-day variability.',
         'Measure your allocation against a reference investment.']):
        with column.container(border=True):
            st.markdown(f'<div class="feature-icon">{icon}</div>', unsafe_allow_html=True)
            st.subheader(title)
            st.caption(description)
    st.caption('Daily rebalanced model · Adjusted close prices · No trading costs or taxes')
    st.stop()

prices, result, assets, weights, benchmark, offline = st.session_state['analysis']
# Older sessions may only have the shared price table.
if 'full_history' not in st.session_state:
    st.session_state['full_history'] = prices
    st.session_state['coverage'] = align_history(prices)[1]
metrics = result['metrics']
source = 'Uploaded snapshot' if offline else 'Yahoo Finance'
st.caption(f'{prices.index[0]:%d %b %Y} — {prices.index[-1]:%d %b %Y}  ·  {len(prices):,} observations  ·  {source}  ·  Benchmark: {benchmark}')

metric_specs = [
    ('Total return', 'Change over the selected period'),
    ('Annualized volatility', 'Daily variability, scaled to one year'),
    ('Max drawdown', 'Largest decline from a previous peak'),
    ('Sharpe ratio', 'Excess return per unit of volatility'),
]
for column, (metric, explanation) in zip(st.columns(4), metric_specs):
    value = metrics.loc['Portfolio', metric]
    reference = metrics.loc['Benchmark', metric]
    formatted = 'N/A' if pd.isna(value) else (f'{value:.2f}' if metric == 'Sharpe ratio' else f'{value:.2%}')
    with column.container(border=True):
        st.metric(metric, formatted, help=explanation)
        reference_text = 'N/A' if pd.isna(reference) else (f'{reference:.2f}' if metric == 'Sharpe ratio' else f'{reference:.2%}')
        st.caption(f'{benchmark}: {reference_text}')

formats = {c: ('{:.2f}' if c == 'Sharpe ratio' else '{:.2%}') for c in metrics.columns}
performance, risk, history_tab, data = st.tabs(['Performance', 'Risk', 'Asset history', 'Data & exports'])
with performance:
    main_column, allocation_column = st.columns([2.7, 1], gap='medium')
    with main_column.container(border=True):
        values = result['portfolio_value']
        ending_value = values['Portfolio'].iloc[-1]
        starting_value = values['Portfolio'].iloc[0]
        gain = ending_value - starting_value
        tone = 'gain' if gain >= 0 else 'loss'
        st.markdown(f'<div class="eyebrow">PORTFOLIO VALUE</div><div class="balance">${ending_value:,.2f}</div><div class="balance-detail"><span class="{tone}">{gain:+,.2f} USD ({metrics.loc["Portfolio", "Total return"]:+.2%})</span><span>over the analysis period</span></div>', unsafe_allow_html=True)
        chart_mode = st.radio('Chart view', ['Portfolio value', 'Cumulative return'], horizontal=True, label_visibility='collapsed', key='chart_view')
        chart_values = values if chart_mode == 'Portfolio value' else values / values.iloc[0] - 1
        st.altair_chart(comparison_chart(chart_values, percentage=chart_mode != 'Portfolio value', height=390), width='stretch', theme=None)
        st.caption(f'Initial investment ${starting_value:,.0f} · Benchmark {benchmark} · Shared dates for every asset')
    with allocation_column.container(border=True):
        st.subheader('Your allocation')
        st.caption(f'{len(assets)} selected assets')
        st.altair_chart(allocation_chart(assets, weights), width='stretch', theme=None)
        for asset, weight in zip(assets, weights):
            asset_return = result['asset_metrics'].loc[asset, 'Total return']
            tone = 'gain' if asset_return >= 0 else 'loss'
            st.markdown(f'<div class="holding-row"><div><strong>{escape(asset)}</strong><span>{weight:.1%} target weight</span></div><div class="{tone}">{asset_return:+.2%}</div></div>', unsafe_allow_html=True)
        st.caption('All returns use the same dates. Weights reset daily.')
    with st.container(border=True):
        st.subheader('Portfolio vs. benchmark')
        st.caption('Returns and risk over the same dates')
        display_metrics = metrics.rename(index={'Benchmark': benchmark})
        st.dataframe(display_metrics.style.format(formats, na_rep='—'), width='stretch')
    with st.expander('Performance by asset'):
        st.dataframe(result['asset_metrics'].style.format(formats, na_rep='—'), width='stretch')
with risk:
    with st.container(border=True):
        st.subheader('Below the previous peak')
        st.caption('Decline from the previous peak, including starting capital. Zero means a new or matched high.')
        st.altair_chart(comparison_chart(result['drawdown'], percentage=True, height=300), width='stretch', theme=None)
    st.subheader('How assets move together')
    st.caption('Daily return correlation · +1 moves together · 0 has no linear relationship · −1 moves oppositely')
    st.altair_chart(correlation_chart(result['correlation']), width='stretch', theme=None)
with history_tab:
    st.subheader('Available history by security')
    st.caption('First available is the earliest returned price in this window. It may be later than the IPO.')
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
    st.caption('Metrics here use this asset’s full returned history. The portfolio comparison may cover fewer dates.')
    st.download_button('Export individual history ↓', individual.to_csv(index_label='Date'),
                       f'{history_symbol}_history.csv', 'text/csv')
with data:
    st.subheader('Underlying prices')
    st.caption('Adjusted daily closes. Missing or invalid prices stop the analysis; they are not filled.')
    st.dataframe(prices.sort_index(ascending=False).style.format('{:,.2f}'), width='stretch')
    st.caption('Portfolio results use the shared date range. See Asset history for earlier prices.')
    download_prices_column, download_metrics_column, _ = st.columns([1, 1, 2])
    download_prices_column.download_button('Export prices ↓', prices.to_csv(index_label='Date'), 'prices.csv', 'text/csv', width='stretch')
    download_metrics_column.download_button('Export metrics ↓', metrics.to_csv(), 'metrics.csv', 'text/csv', width='stretch')

st.divider()
st.caption('MODEL NOTES  ·  Daily rebalancing · 252 trading days per year · Costs and taxes excluded · No FX conversion')
with st.expander('How to interpret these results'):
    st.write('Prices include provider adjustments for splits and dividends. Annualized estimates from short periods can be misleading. Sharpe uses your annual risk-free rate converted to daily. Use assets in the same currency. Past results do not predict future returns.')
