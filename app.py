import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title('🍵 Specialty Tea Buyer Forecast')
st.write('Select a buyer, grade, and year to see their monthly forecast.')

# ── Three dropdowns: Buyer | Grade | Year ─────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    buyer_list     = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)

with col2:
    grade_list     = sorted(
        forecast[forecast['Buyer_Name'] == selected_buyer]['Grade']
        .unique().tolist()
    )
    selected_grade = st.selectbox('Select grade', grade_list)

with col3:
    # Hardcoded year list — 2023 to 2030
    selected_year = st.selectbox('Select year', list(range(2023, 2031)))

# ── Month scaffold — all 12 months for the selected year ─────────────────────
month_order    = ['Jan','Feb','Mar','Apr','May','Jun',
                  'Jul','Aug','Sep','Oct','Nov','Dec']
all_months     = pd.DataFrame({'month': range(1, 13)})
all_months['month_label'] = pd.to_datetime(
    all_months[['month']].assign(year=selected_year, day=1)
).dt.strftime('%b')

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# HISTORICAL YEARS (2023 – 2025) — Single bar: actual quantity per month
# ═════════════════════════════════════════════════════════════════════════════
if selected_year <= 2025:

    st.subheader(
        f'📊 Monthly sales — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    # Pull actual purchased rows for this buyer / grade / year
    hist_year = (
        historical[
            (historical['Buyer_Name'] == selected_buyer) &
            (historical['Grade']      == selected_grade)  &
            (historical['year']       == selected_year)   &
            (historical['purchased']  == 1)
        ]
        [['month', 'Qty']]
        .copy()
    )

    # Merge onto full 12-month scaffold so missing months show as 0
    hist_plot = all_months.merge(hist_year, on='month', how='left')
    hist_plot['Qty'] = hist_plot['Qty'].fillna(0).astype(int)

    # ── Bar chart ─────────────────────────────────────────────────────────────
    bar_hist = alt.Chart(hist_plot).mark_bar(color='steelblue').encode(
        x=alt.X('month_label:N', title='Month', sort=month_order),
        y=alt.Y('Qty:Q', title='Qty sold (bags)'),
        tooltip=[
            alt.Tooltip('month_label:N', title='Month'),
            alt.Tooltip('Qty:Q',         title='Qty sold (bags)')
        ]
    ).properties(
        width='container',
        height=400
    ).configure_axisX(
        labelAngle=0
    )

    st.altair_chart(bar_hist, use_container_width=True)

    # ── Historical table ──────────────────────────────────────────────────────
    st.subheader('📋 Monthly sales table')

    hist_table = hist_plot[['month_label', 'Qty']].rename(columns={
        'month_label': 'Month',
        'Qty':         'Qty sold (bags)'
    })

    st.dataframe(hist_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇ Download as CSV',
        data=hist_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_sales.csv',
        mime='text/csv',
        key='download_hist_year'
    )

    # ── Full historical table (all years) ─────────────────────────────────────
    st.subheader('📂 Historical purchase data (all years)')
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
        st.info('No historical data found for this buyer and grade combination.')
    else:
        hist_display = hist_all[['year', 'month', 'Qty', 'Average', 'purchased']].copy()
        hist_display['Month'] = pd.to_datetime(
            hist_display[['year', 'month']].assign(day=1)
        ).dt.strftime('%b %Y')
        hist_display['Purchased'] = hist_display['purchased'].map(
            {1: '✅ Yes', 0: '❌ No'}
        )
        hist_display['Qty']     = hist_display['Qty'].astype(int)
        hist_display['Average'] = hist_display['Average'].round(2)
        hist_display = hist_display[['Month', 'Purchased', 'Qty', 'Average']].rename(
            columns={'Qty': 'Qty purchased (bags)', 'Average': 'Avg price'}
        )
        st.dataframe(hist_display, use_container_width=True, hide_index=True)

        st.download_button(
            label='⬇ Download historical data as CSV',
            data=hist_display.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_history.csv',
            mime='text/csv',
            key='download_history'
        )

# ═════════════════════════════════════════════════════════════════════════════
# FORECAST YEARS (2026 – 2030) — Three bars: probability | qty | weighted qty
# ═════════════════════════════════════════════════════════════════════════════
else:

    st.subheader(
        f'📊 Monthly forecast — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    # Pull forecast rows for this buyer / grade / year
    fcst_year = (
        forecast[
            (forecast['Buyer_Name'] == selected_buyer) &
            (forecast['Grade']      == selected_grade)  &
            (forecast['year']       == selected_year)
        ]
        [['month', 'avg_buy_probability', 'expected_qty', 'probability_wtd_qty']]
        .copy()
    )

    # Merge onto full 12-month scaffold so missing months show as 0
    fcst_plot = all_months.merge(fcst_year, on='month', how='left')
    fcst_plot['avg_buy_probability'] = fcst_plot['avg_buy_probability'].fillna(0)
    fcst_plot['expected_qty']        = fcst_plot['expected_qty'].fillna(0)
    fcst_plot['probability_wtd_qty'] = fcst_plot['probability_wtd_qty'].fillna(0)

    # ── Reshape to long format for grouped bar chart ──────────────────────────
    # Altair grouped bars require long-form data with a "metric" column
    # We use two separate Y scales: probability (0–1) and quantity (bags)
    # so we must layer two charts: one for probability, one for quantities

    # Probability chart (left bars)
    bar_prob = alt.Chart(fcst_plot).mark_bar(size=12).encode(
        x=alt.X('month_label:N', title='Month', sort=month_order),
        xOffset=alt.value(-13),
        y=alt.Y(
            'avg_buy_probability:Q',
            title='Buy probability',
            axis=alt.Axis(format='%', titleColor='steelblue',
                          labelColor='steelblue'),
            scale=alt.Scale(domain=[0, 1])
        ),
        color=alt.value('steelblue'),
        tooltip=[
            alt.Tooltip('month_label:N',         title='Month'),
            alt.Tooltip('avg_buy_probability:Q', title='Buy probability',
                        format='.1%')
        ]
    )

    # Expected qty chart (middle bars)
    bar_qty = alt.Chart(fcst_plot).mark_bar(size=12).encode(
        x=alt.X('month_label:N', title='Month', sort=month_order),
        xOffset=alt.value(0),
        y=alt.Y(
            'expected_qty:Q',
            title='Quantity (bags)',
            axis=alt.Axis(titleColor='coral', labelColor='coral')
        ),
        color=alt.value('coral'),
        tooltip=[
            alt.Tooltip('month_label:N',  title='Month'),
            alt.Tooltip('expected_qty:Q', title='Expected qty (bags)',
                        format=',.1f')
        ]
    )

    # Weighted qty chart (right bars)
    bar_wtd = alt.Chart(fcst_plot).mark_bar(size=12).encode(
        x=alt.X('month_label:N', title='Month', sort=month_order),
        xOffset=alt.value(13),
        y=alt.Y(
            'probability_wtd_qty:Q',
            # Shares the same right-axis scale as expected_qty
            axis=None
        ),
        color=alt.value('seagreen'),
        tooltip=[
            alt.Tooltip('month_label:N',          title='Month'),
            alt.Tooltip('probability_wtd_qty:Q',  title='Prob-weighted qty',
                        format=',.1f')
        ]
    )

    # Layer all three — probability on independent left axis,
    # qty and weighted qty share the right axis
    chart = alt.layer(bar_prob, bar_qty, bar_wtd).resolve_scale(
        y='independent'
    ).properties(
        width='container',
        height=400
    ).configure_axisX(
        labelAngle=0
    )

    # Manual legend note since Altair colour legends don't work well on layered charts
    leg1, leg2, leg3, _ = st.columns([1, 1, 1, 5])
    leg1.markdown('🟦 Buy probability')
    leg2.markdown('🟥 Expected qty')
    leg3.markdown('🟩 Prob-weighted qty')

    st.altair_chart(chart, use_container_width=True)

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
        forecast_table['expected_qty'].round(0).astype(int)
    )
    forecast_table['probability_wtd_qty'] = (
        forecast_table['probability_wtd_qty'].round(0).astype(int)
    )

    forecast_table = forecast_table.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Buy probability',
        'expected_qty':         'Expected qty (bags)',
        'probability_wtd_qty':  'Prob-weighted qty',
    })[[
        'Month', 'Buy probability', 'Likelihood',
        'Expected qty (bags)', 'Prob-weighted qty'
    ]]

    st.dataframe(forecast_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇ Download forecast as CSV',
        data=forecast_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_forecast.csv',
        mime='text/csv',
        key='download_forecast'
    )

    # ── Historical table ──────────────────────────────────────────────────────
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
        st.info('No historical data found for this buyer and grade combination.')
    else:
        hist_display = hist_all[['year', 'month', 'Qty', 'Average', 'purchased']].copy()
        hist_display['Month'] = pd.to_datetime(
            hist_display[['year', 'month']].assign(day=1)
        ).dt.strftime('%b %Y')
        hist_display['Purchased'] = hist_display['purchased'].map(
            {1: '✅ Yes', 0: '❌ No'}
        )
        hist_display['Qty']     = hist_display['Qty'].astype(int)
        hist_display['Average'] = hist_display['Average'].round(2)
        hist_display = hist_display[['Month', 'Purchased', 'Qty', 'Average']].rename(
            columns={'Qty': 'Qty purchased (bags)', 'Average': 'Avg price'}
        )
        st.dataframe(hist_display, use_container_width=True, hide_index=True)

        st.download_button(
            label='⬇ Download historical data as CSV',
            data=hist_display.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_history.csv',
            mime='text/csv',
            key='download_history'
        )