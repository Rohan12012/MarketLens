"""Browse the recorded concentration and rebalancing study."""
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from marketlens.plot_study import ranking_chart
from marketlens.research import load_research
from marketlens.validation import load_validation

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title='MarketLens | Research study', page_icon='◈', layout='wide')
st.markdown(f'<style>{(ROOT / "dashboard.css").read_text()}</style>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand-mark">◈ &nbsp; MARKETLENS</div>', unsafe_allow_html=True)
    st.caption('PORTFOLIO RESEARCH')
    st.page_link('app.py', label='Portfolio analysis')
    st.page_link('pages/1_Research_study.py', label='Research study')
    st.divider()
    cost_bps = st.select_slider('Trading cost (basis points)', options=[0, 5, 10, 25], value=10, key='study_cost')
    st.caption('Charged on dollars bought and sold. Ten basis points means 0.1%.')
    with st.expander('Study assumptions'):
        st.write('AAPL, MSFT, GOOGL. Each window starts with $10,000.')
        st.write('Equal weight: one-third each. Concentrated: 80% AAPL, 10% MSFT, 10% GOOGL.')
        st.caption('Fractional holdings · No initial or terminal fees · Taxes excluded · 0% risk-free rate')

st.markdown('<div class="workspace-bar"><span>RESEARCH STUDY</span><span class="mode-pill">SAVED RESULTS</span></div>', unsafe_allow_html=True)
st.title('Concentration & rebalancing')
st.write('Does restoring target weights change the returns and risk of a concentrated portfolio?')

try:
    comparison = load_research()
except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
    st.info('Saved study results are not available. The portfolio analysis page can still be used.')
    st.caption(str(exc))
    with st.expander('Set up the study results'):
        st.write('From the project folder, run:')
        st.code('python -m marketlens.build_study', language='bash')
        st.caption('This downloads the fixed study data, checks dates, runs all three windows, and imports the results. Generated data is excluded from Git.')
    st.stop()

st.caption(f'{len(comparison)} recorded cases · 3 windows · Yahoo Finance adjusted prices · Queried from SQLite')
comparison_tab, notes_tab, validation_tab = st.tabs(['Compare results', 'Findings & limitations', 'Validation'])
with comparison_tab:
    with st.container(border=True):
        st.altair_chart(ranking_chart(comparison, cost_bps=cost_bps, dark=True), width='stretch', theme=None)
    st.subheader('Detailed results')
    period = st.selectbox('Period', ['2016–2025', '2016–2020', '2021–2025'], key='study_period')
    labels = comparison.first_date.str[:4] + '–' + comparison.last_date.str[:4]
    selected = comparison.loc[(labels == period) & (comparison.cost_bps == cost_bps)].copy()
    first, last = selected.iloc[0][['first_date', 'last_date']]
    st.caption(f'{first} to {last} · Total period returns, not annualized returns · ${10000:,.0f} initial capital')
    for column, allocation in zip(st.columns(2), ['Equal weight', 'Concentrated']):
        with column.container(border=True):
            st.subheader(allocation)
            table = selected.loc[selected.allocation == allocation,
                                 ['strategy', 'total_return', 'max_drawdown', 'volatility', 'total_cost', 'ending_value_reduction']]
            table = table.rename(columns={'strategy': 'Strategy', 'total_return': 'Total return',
                                          'max_drawdown': 'Max drawdown', 'volatility': 'Annualized volatility',
                                          'total_cost': 'Fees paid', 'ending_value_reduction': 'Ending value reduction'})
            st.dataframe(table.style.format({'Total return': '{:.2%}', 'Max drawdown': '{:.2%}',
                                            'Annualized volatility': '{:.2%}', 'Fees paid': '${:,.2f}',
                                            'Ending value reduction': '${:,.2f}'}), hide_index=True, width='stretch')
    st.caption('Ending value reduction compares each case with its own zero-cost baseline. It includes the effect of fees on later returns, so it differs from fees paid.')
    left, right = st.columns(2)
    left.download_button('Export selected cases', selected.to_csv(index=False),
                         f'study-{period}-{cost_bps}bps.csv', 'text/csv', width='stretch')
    right.download_button('Export all 72 cases', comparison.to_csv(index=False),
                          'study-comparison.csv', 'text/csv', width='stretch')
with notes_tab:
    st.subheader('Findings from the original recorded study')
    st.markdown('''- Buy-and-hold had the highest return in 2016–2020 at every tested rate.
- Monthly rebalancing led the full period at every tested rate.
- Daily led 2021–2025 without costs; monthly led at 5, 10, and 25 basis points.
- Equal weighting did not consistently produce a smaller maximum drawdown.''')
    st.caption('These written findings refer to the original study snapshot and all four cost rates. A rebuild with revised provider data can differ; use Compare results for the currently loaded runs.')
    st.subheader('What this does not establish')
    st.write('Three retrospectively selected stocks cannot establish the best portfolio or future trading rule. All share sector exposure. Trades use adjusted closes, fractional holdings, and hypothetical costs.')
    st.write('Date coverage matches the reference calendar, but individual prices have not been checked against another provider. Strategy rankings show order rather than the size or statistical significance of the difference.')
    st.download_button('Download findings report', (ROOT / 'docs' / 'findings.md').read_text(),
                       'marketlens-findings.md', 'text/markdown')
    with st.expander('Where the results come from'):
        st.write('The page runs docs/study-comparison.sql against the saved SQLite database. It checks the chosen windows and source checksum, then ranks each strategy within its allocation and cost rate.')
        st.caption('Run IDs: config/study-runs.json · Methods: docs/analysis-brief.md · Data audit: docs/data-quality.md')
with validation_tab:
    st.subheader('Recorded validation')
    st.caption('Automated software tests and checks on the actual study data are shown separately. Opening this page does not run tests.')
    try:
        validation = load_validation()
    except (OSError, ValueError, KeyError) as exc:
        validation = None
        st.warning(f'Could not read the validation record: {exc}')
    if validation is None:
        st.info('No validation run has been recorded on this machine.')
        st.code('python -m marketlens.record_validation', language='bash')
    else:
        checked = datetime.fromisoformat(validation['generated_at_utc']).astimezone(ZoneInfo('America/New_York'))
        st.caption(f'Last recorded: {checked:%b %d, %Y at %I:%M %p %Z}')
        if not validation['is_current']:
            st.warning('This record is out of date: code, tests, configuration, SQL, or checked data has changed. Values below describe the earlier run.')
        tests = validation['tests']
        study = validation.get('study', {})
        audit = study.get('audit', {})
        columns = st.columns(4)
        columns[0].metric('Tests passed', f'{tests["passed"]} / {tests["total"]}')
        sessions = f'{audit["observed_sessions"]:,} / {audit["expected_sessions"]:,}' if audit else 'Not checked'
        columns[1].metric('Trading sessions', sessions)
        columns[2].metric('SQL cases checked', str(study.get('cases', 'Not checked')))
        columns[3].metric('Case exports reconciled', str(study.get('accounting_cases', 'Not checked')))
        st.markdown('**Software test suite**')
        if tests['successful']:
            st.success(f'The recorded suite passed. Failures: {tests["failures"]}; errors: {tests["errors"]}; skipped: {tests["skipped"]}.')
        else:
            st.error(f'The recorded suite failed. Failures: {tests["failures"]}; errors: {tests["errors"]}.')
        st.caption('Tests cover portfolio arithmetic, trade timing, fees, SQL joins, data validation, exports, dashboard controls, and rebuild behavior. They use synthetic inputs and mocked downloads.')
        st.markdown('**Actual study data and results**')
        checks = pd.DataFrame(study.get('checks', []))
        if not checks.empty:
            st.table(checks.rename(columns={'check': 'Check', 'status': 'Recorded status', 'detail': 'Evidence'}))
        st.warning('Independent price verification remains open. A secondary-source access probe did not provide comparable prices; no sampled price has been marked independently verified.')
        st.caption('A passed test suite does not prove market prices are accurate. Individual prices have not been independently checked against another provider.')
        if audit:
            with st.expander('Calendar and source details'):
                st.json(audit)
        st.download_button('Download validation record', json.dumps(
            {key: value for key, value in validation.items() if key != 'is_current'}, indent=2),
                           'marketlens-validation.json', 'application/json')
        with st.expander('Refresh this evidence'):
            st.code('python -m marketlens.record_validation', language='bash')
            st.caption('Run locally after code changes or a study rebuild, then refresh this page. This records actual outcomes; it does not hardcode a passing status.')
st.caption('Historical model results · Same initial capital in each window · The five-year runs are independent, not consecutive holdings')
