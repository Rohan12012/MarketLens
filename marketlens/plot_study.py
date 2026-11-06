"""Build a browser-viewable chart from the SQL study comparison."""
import argparse
from pathlib import Path

import altair as alt

from marketlens.compare_periods import compare_periods

ROOT = Path(__file__).resolve().parents[1]


def ranking_chart(comparison):
    data = comparison.copy()
    data['Period'] = data['first_date'].str[:4] + '–' + data['last_date'].str[:4]
    rate = alt.param('cost_rate', value=10,
                     bind=alt.binding_select(options=[0, 5, 10, 25], name='Cost per traded dollar (bps): '))
    chart = alt.Chart(data).add_params(rate).transform_filter(
        alt.datum.cost_bps == rate
    ).mark_line(point=alt.OverlayMarkDef(size=90), strokeWidth=2.5).encode(
        x=alt.X('Period:N', sort=['2016–2020', '2021–2025', '2016–2025'], title=None,
                axis=alt.Axis(labelAngle=0, labelPadding=12)),
        y=alt.Y('return_rank:Q', title='Return rank · 1 = highest',
                scale=alt.Scale(domain=[3.2, 0.8]), axis=alt.Axis(values=[1, 2, 3])),
        color=alt.Color('strategy:N', title=None,
                        scale=alt.Scale(domain=['Buy-and-hold', 'Monthly', 'Daily'],
                                        range=['#61748C', '#16876D', '#8959AF']),
                        legend=alt.Legend(orient='bottom')),
        strokeDash=alt.StrokeDash('strategy:N', legend=None,
                                 scale=alt.Scale(domain=['Buy-and-hold', 'Monthly', 'Daily'],
                                                 range=[[1, 0], [7, 3], [2, 3]])),
        tooltip=[alt.Tooltip('allocation:N', title='Allocation'), 'Period:N',
                 alt.Tooltip('strategy:N', title='Strategy'),
                 alt.Tooltip('cost_bps:Q', title='Cost (bps)'),
                 alt.Tooltip('total_return:Q', title='Total return', format='.2%'),
                 alt.Tooltip('max_drawdown:Q', title='Max drawdown', format='.2%'),
                 alt.Tooltip('total_cost:Q', title='Fees paid', format='$,.2f')],
    ).properties(width=350, height=270).facet(
        column=alt.Column('allocation:N', title=None, sort=['Equal weight', 'Concentrated'])
    ).properties(title=alt.TitleParams(
        text='The strategy ranking changes with the period and trading costs',
        subtitle=['AAPL / MSFT / GOOGL · each window starts with $10,000',
                  'Separate comparison windows, not a continuous investment path. Hover for total returns.',
                  'Ranks show order, not the size of the return difference. Full-period returns span ten years.'],
        anchor='start', fontSize=19, subtitleFontSize=11, subtitlePadding=8,
    ))
    return (chart.configure_view(stroke=None)
            .configure_axis(domain=False, tickSize=0, gridColor='#E4E9EF',
                            labelColor='#455468', titleColor='#455468', titlePadding=12)
            .configure_header(labelFontSize=14, labelFontWeight='bold', labelPadding=18)
            .configure_legend(labelFontSize=12, padding=18)
            .configure(background='#FFFFFF', padding=28))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('full_run')
    parser.add_argument('first_run')
    parser.add_argument('second_run')
    parser.add_argument('--database', type=Path, default=ROOT / 'data' / 'study' / 'study.sqlite')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'study' / 'strategy-rankings.html')
    args = parser.parse_args()
    data = compare_periods(args.database, args.full_run, args.first_run, args.second_run)
    chart = ranking_chart(data)
    chart.to_dict(validate=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    chart.save(args.output, embed_options={'actions': False})
    print(f'Saved chart from {len(data)} SQL result rows: {args.output}')
