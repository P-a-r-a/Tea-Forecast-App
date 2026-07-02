import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Tea Buyer Forecast',
    page_icon='🍵',
    layout='wide'
)

# ── Password gate ─────────────────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    pad_left, center_col, pad_right = st.columns([3.5, 3, 3.5])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>🔒 Secure Access</h2>",
                    unsafe_allow_html=True)
        with st.form(key='login_form', clear_on_submit=False):
            password = st.text_input('Enter password', type='password',
                                     label_visibility='collapsed')
            btn_pad_l, btn_col, btn_pad_r = st.columns([1, 1, 1])
            with btn_col:
                submit_button = st.form_submit_button(
                    label='Login', use_container_width=True)
        if submit_button:
            if password == st.secrets['APP_PASSWORD']:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error('Incorrect password.')
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    forecast   = pd.read_csv('forecast.csv')
    historical = pd.read_csv('historical.csv')
    return forecast, historical

forecast, historical = load_data()

# ── Constants ─────────────────────────────────────────────────────────────────
ALL_GRADES  = ['GOLDENTIPS', 'INNOVATIVE', 'SILVERTIPS']
MONTH_ORDER = ['Jan','Feb','Mar','Apr','May','Jun',
               'Jul','Aug','Sep','Oct','Nov','Dec']
ALL_MONTHS  = pd.DataFrame({
    'month':       range(1, 13),
    'month_label': MONTH_ORDER
})

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title('🍵 Specialty Tea Buyer Forecast')
st.write('Select a buyer, year, and grade to see their monthly forecast.')

# ── Three dropdowns: Buyer | Year | Grade ─────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    buyer_list     = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)

with col2:
    selected_year  = st.selectbox('Select year', list(range(2023, 2031)))

with col3:
    selected_grade = st.selectbox('Select grade', ALL_GRADES)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# HISTORICAL YEARS (2023 – 2025)
# ═════════════════════════════════════════════════════════════════════════════
if selected_year <= 2025:

    hist_raw = historical[
        (historical['Buyer_Name'] == selected_buyer) &
        (historical['Grade']      == selected_grade)  &
        (historical['year']       == selected_year)
    ].copy()

    if hist_raw.empty:
        st.info(
            f'**{selected_buyer}** had no activity related to '
            f'**{selected_grade}** in **{selected_year}**.'
        )
        st.stop()

    # Merge onto 12-month scaffold
    hist_plot = ALL_MONTHS.merge(
        hist_raw[['month', 'Qty', 'Average', 'purchased']],
        on='month', how='left'
    )
    hist_plot['Qty']       = hist_plot['Qty'].fillna(0).astype(float)
    hist_plot['purchased'] = hist_plot['purchased'].fillna(0).astype(int)

    # Average price only on purchased months — 0 otherwise
    hist_plot['Average'] = np.where(
        hist_plot['purchased'] == 1,
        hist_plot['Average'].fillna(0),
        0.0
    )

    # ── Dual bar chart (Altair) ───────────────────────────────────────────────
    st.subheader(
        f'📊 Monthly sales — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    bar_qty = alt.Chart(hist_plot).mark_bar(size=14).encode(
        x=alt.X('month_label:N', title='Month', sort=MONTH_ORDER),
        xOffset=alt.value(-8),
        y=alt.Y(
            'Qty:Q',
            title='Qty sold (bags)',
            axis=alt.Axis(titleColor='steelblue', labelColor='steelblue')
        ),
        color=alt.value('steelblue'),
        tooltip=[
            alt.Tooltip('month_label:N', title='Month'),
            alt.Tooltip('Qty:Q',         title='Qty sold (bags)',
                        format=',.0f')
        ]
    )

    bar_avg = alt.Chart(hist_plot).mark_bar(size=14).encode(
        x=alt.X('month_label:N', title='Month', sort=MONTH_ORDER),
        xOffset=alt.value(8),
        y=alt.Y(
            'Average:Q',
            title='Avg price',
            axis=alt.Axis(titleColor='coral', labelColor='coral')
        ),
        color=alt.value('coral'),
        tooltip=[
            alt.Tooltip('month_label:N', title='Month'),
            alt.Tooltip('Average:Q',     title='Avg price', format=',.2f')
        ]
    )

    chart_hist = alt.layer(bar_qty, bar_avg).resolve_scale(
        y='independent'
    ).properties(
        width='container',
        height=400
    ).configure_axisX(labelAngle=0)

    leg1, leg2, _ = st.columns([1, 1, 6])
    leg1.markdown('🟦 Qty sold (bags)')
    leg2.markdown('🟥 Avg price')

    st.altair_chart(chart_hist, use_container_width=True)

    # ── Single table — mirrors chart data ─────────────────────────────────────
    st.subheader('📋 Monthly sales table')

    sales_table = hist_plot[['month_label', 'Qty', 'Average']].copy()
    sales_table['Qty']     = sales_table['Qty'].astype(int)
    sales_table['Average'] = sales_table['Average'].round(2)
    sales_table = sales_table.rename(columns={
        'month_label': 'Month',
        'Qty':         'Qty sold (bags)',
        'Average':     'Avg price'
    })

    st.dataframe(sales_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇ Download as CSV',
        data=sales_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_sales.csv',
        mime='text/csv',
        key='download_sales'
    )

# ═════════════════════════════════════════════════════════════════════════════
# FORECAST YEARS (2026 – 2030)
# ═════════════════════════════════════════════════════════════════════════════
else:

    fcst_raw = forecast[
        (forecast['Buyer_Name'] == selected_buyer) &
        (forecast['Grade']      == selected_grade)  &
        (forecast['year']       == selected_year)
    ].copy()

    if fcst_raw.empty:
        st.info(
            f'**{selected_buyer}** had no activity related to '
            f'**{selected_grade}** in **{selected_year}**.'
        )
        st.stop()

    # Merge onto 12-month scaffold
    fcst_plot = ALL_MONTHS.merge(
        fcst_raw[['month', 'avg_buy_probability',
                  'expected_qty', 'probability_wtd_qty']],
        on='month', how='left'
    )
    fcst_plot['avg_buy_probability'] = fcst_plot['avg_buy_probability'].fillna(0)
    fcst_plot['expected_qty']        = fcst_plot['expected_qty'].fillna(0)
    fcst_plot['probability_wtd_qty'] = fcst_plot['probability_wtd_qty'].fillna(0)

    # ── Triple bar chart (Plotly) ─────────────────────────────────────────────
    st.subheader(
        f'📊 Monthly forecast — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    fig = go.Figure()

    # Bar 1 — Buy probability (left y-axis)
    fig.add_trace(go.Bar(
        name='Buy probability',
        x=fcst_plot['month_label'],
        y=fcst_plot['avg_buy_probability'],
        marker_color='steelblue',
        yaxis='y1',
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Buy probability: %{y:.1%}'
            '<extra></extra>'
        )
    ))

    # Bar 2 — Predicted qty (right y-axis)
    # Tooltip shows both predicted qty and weighted qty
    fig.add_trace(go.Bar(
        name='Predicted qty (bags)',
        x=fcst_plot['month_label'],
        y=fcst_plot['expected_qty'],
        marker_color='coral',
        yaxis='y2',
        customdata=fcst_plot['probability_wtd_qty'],
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Predicted qty: %{y:,.1f} bags<br>'
            'Weighted qty: %{customdata:,.1f} bags'
            '<extra></extra>'
        )
    ))

    # Bar 3 — Weighted qty (right y-axis, same scale as predicted qty)
    # Tooltip also shows both values
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Buy probability',
        x=fcst_plot['month_label'],
        y=fcst_plot['avg_buy_probability'],
        marker_color='steelblue',
        hovertemplate='<b>%{x}</b><br>Buy probability: %{y:.1%}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Predicted qty (bags)',
        x=fcst_plot['month_label'],
        y=fcst_plot['expected_qty'],
        marker_color='coral',
        customdata=fcst_plot['probability_wtd_qty'],
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Predicted qty: %{y:,.1f} bags<br>'
            'Weighted qty: %{customdata:,.1f} bags'
            '<extra></extra>'
        )
    ))

    fig.add_trace(go.Bar(
        name='Weighted qty (bags)',
        x=fcst_plot['month_label'],
        y=fcst_plot['probability_wtd_qty'],
        marker_color='seagreen',
        customdata=fcst_plot['expected_qty'],
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Predicted qty: %{customdata:,.1f} bags<br>'
            'Weighted qty: %{y:,.1f} bags'
            '<extra></extra>'
        )
    ))

    fig.update_layout(barmode='group', height=450)
    fig.update_xaxes(
        categoryorder='array',
        categoryarray=MONTH_ORDER,
        title_text='Month'
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Filter toggle ─────────────────────────────────────────────────────────────
    show_above_50 = st.toggle(
        'Show only months where buy probability > 50%',
        value=False
    )

    display_table = forecast_table.copy()

    if show_above_50:
        # Filter on the numeric probability before it was converted to string
        mask = fcst_plot['avg_buy_probability'] > 0.5
        display_table = forecast_table[mask.values].reset_index(drop=True)

        if display_table.empty:
            st.info(
                f'No months in {selected_year} where **{selected_buyer}** '
                f'has a predicted buy probability above 50% for **{selected_grade}**.'
            )
            st.stop()

    # ── Forecast table ────────────────────────────────────────────────────────────
    st.subheader('📋 Forecast table')
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇ Download forecast as CSV',
        data=display_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_forecast.csv',
        mime='text/csv',
        key='download_forecast'
)

    # ── Forecast table ────────────────────────────────────────────────────────
    st.subheader('📋 Forecast table')

    def likelihood(p):
        if p >= 0.7:   return '🟢 High'
        elif p >= 0.4: return '🟡 Medium'
        else:          return '🔴 Low'

    forecast_table = fcst_plot[[
        'month_label', 'avg_buy_probability',
        'expected_qty', 'probability_wtd_qty'
    ]].copy()

    forecast_table['Likelihood'] = (
        forecast_table['avg_buy_probability'].apply(likelihood)
    )
    forecast_table['avg_buy_probability'] = (
        forecast_table['avg_buy_probability'] * 100
    ).round(1).astype(str) + '%'
    forecast_table['expected_qty']        = (
        forecast_table['expected_qty'].round(1)
    )
    forecast_table['probability_wtd_qty'] = (
        forecast_table['probability_wtd_qty'].round(1)
    )

    forecast_table = forecast_table.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Buy probability',
        'expected_qty':         'Predicted qty (bags)',
        'probability_wtd_qty':  'Weighted qty (bags)',
    })[[
        'Month', 'Buy probability', 'Likelihood',
        'Predicted qty (bags)', 'Weighted qty (bags)'
    ]]

    st.dataframe(forecast_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇ Download forecast as CSV',
        data=forecast_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_forecast.csv',
        mime='text/csv',
        key='download_forecast'
    )

    # ── Historical reference table ────────────────────────────────────────────
    st.subheader('📂 Historical purchase data')
    st.write('Actual purchase records used to train the model for this buyer and grade.')

    hist_all = (
        historical[
            (historical['Buyer_Name'] == selected_buyer) &
            (historical['Grade']      == selected_grade)
        ]
        .sort_values(['year', 'month'])
        .reset_index(drop=True)
    )

    if hist_all.empty:
        st.info(
            f'No historical purchase data found for '
            f'**{selected_buyer}** · **{selected_grade}**.'
        )
    else:
        hist_display = hist_all[
            ['year', 'month', 'Qty', 'Average', 'purchased']
        ].copy()

        hist_display['Month'] = pd.to_datetime(
            hist_display[['year', 'month']].assign(day=1)
        ).dt.strftime('%b %Y')

        hist_display['Purchased'] = hist_display['purchased'].map(
            {1: '✅ Yes', 0: '❌ No'}
        )
        hist_display['Qty']     = hist_display['Qty'].astype(int)
        hist_display['Average'] = hist_display['Average'].round(2)

        hist_display = hist_display[[
            'Month', 'Purchased', 'Qty', 'Average'
        ]].rename(columns={
            'Qty':     'Qty purchased (bags)',
            'Average': 'Avg price'
        })

        st.dataframe(hist_display, use_container_width=True, hide_index=True)

        st.download_button(
            label='⬇ Download historical data as CSV',
            data=hist_display.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_history.csv',
            mime='text/csv',
            key='download_history'
        )