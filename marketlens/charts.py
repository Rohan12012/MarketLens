"""Shared chart styling for the dashboard."""
import altair as alt

PORTFOLIO = '#45C4A0'
BENCHMARK = '#91A4C0'


def style(chart):
    return (chart.configure_view(stroke=None)
            .configure_axis(labelColor='#94A3B8', titleColor='#94A3B8',
                            gridColor='#232D39', domain=False, ticks=False,
                            labelPadding=10, titlePadding=14)
            .configure_legend(labelColor='#C9D4E2', title=None, orient='top',
                              symbolStrokeWidth=3, padding=12)
            .configure(background='transparent'))


def comparison_chart(frame, percentage=False, height=340):
    """Plot portfolio and benchmark values over time."""
    long = frame.rename_axis('Date').reset_index().melt('Date', var_name='Series', value_name='Value')
    # Inline values avoid Altair's default row limit for long price histories.
    source = alt.InlineData(values=long.assign(Date=long.Date.dt.strftime('%Y-%m-%d')).to_dict('records'))
    chart = alt.Chart(source).mark_line(strokeWidth=2.4).encode(
        x=alt.X('Date:T', title=None, axis=alt.Axis(format='%b %Y', grid=False, tickCount=6)),
        y=alt.Y('Value:Q', title=None, scale=alt.Scale(zero=False),
                axis=alt.Axis(format='.0%' if percentage else '$,.0f')),
        color=alt.Color('Series:N', scale=alt.Scale(domain=['Portfolio', 'Benchmark'],
                                                   range=[PORTFOLIO, BENCHMARK])),
        strokeDash=alt.StrokeDash('Series:N', legend=None,
                                 scale=alt.Scale(domain=['Portfolio', 'Benchmark'], range=[[1, 0], [5, 4]])),
        tooltip=[alt.Tooltip('Date:T', format='%b %d, %Y'), 'Series:N',
                 alt.Tooltip('Value:Q', format='.2%' if percentage else '$,.2f')],
    ).properties(height=height).interactive(bind_y=False)
    return style(chart)


def allocation_chart(assets, weights):
    source = alt.InlineData(values=[{'Asset': a, 'Weight': w} for a, w in zip(assets, weights)])
    chart = alt.Chart(source).mark_bar(color=PORTFOLIO, cornerRadiusEnd=4, size=18).encode(
        x=alt.X('Weight:Q', title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='.0%')),
        y=alt.Y('Asset:N', title=None, sort=None, axis=alt.Axis(grid=False)),
        tooltip=['Asset:N', alt.Tooltip('Weight:Q', format='.1%')],
    ).properties(height=max(150, 35 * len(assets)))
    return style(chart)


def correlation_chart(correlation):
    """Show correlations as labeled cells; leave undefined values blank."""
    rows = []
    for left in correlation.index:
        for right in correlation.columns:
            value = correlation.loc[left, right]
            defined = value == value  # NaN correlations occur for constant returns.
            rows.append({'Asset': left, 'Other': right,
                         'Correlation': float(value) if defined else None,
                         'Label': f'{value:.2f}' if defined else '—'})
    base = alt.Chart(alt.InlineData(values=rows)).encode(
        x=alt.X('Other:N', title=None, sort=list(correlation.columns),
                axis=alt.Axis(labelAngle=0, orient='top', grid=False)),
        y=alt.Y('Asset:N', title=None, sort=list(correlation.index), axis=alt.Axis(grid=False)),
        tooltip=['Asset:N', 'Other:N', alt.Tooltip('Correlation:Q', format='.2f')],
    )
    cells = base.mark_rect(stroke='#0D1117', strokeWidth=3, cornerRadius=4).encode(
        color=alt.Color('Correlation:Q', scale=alt.Scale(domain=[-1, 0, 1],
                        range=['#4D6DAD', '#192431', '#277D69']), legend=None))
    labels = base.mark_text(color='#E5EBF1', fontSize=12).encode(text='Label:N')
    return style((cells + labels).properties(height=max(180, len(correlation) * 50)))
