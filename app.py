import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# ── Password gate ─────────────────────────────────────────────────────────────
# password = st.text_input('Enter password to access the app', type='password')
# if password != st.secrets['APP_PASSWORD']:
#     st.warning('Incorrect password. Please try again.')
#     st.stop()

password = st.text_input('Enter password', type='password')
if password != st.secrets['APP_PASSWORD']:
    st.warning('Incorrect password.')
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    forecast    = pd.read_csv('forecast.csv')
    historical  = pd.read_csv('historical.csv')
    return forecast, historical

forecast, historical = load_data()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Tea Buyer Forecast',
    page_icon='🍵',
    layout='wide'
)

st.title('🍵 Specialty Tea Buyer Forecast')
st.write('Select a buyer and grade to see their forecast and purchase history.')

# ── Dropdowns ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    # All unique buyers, sorted alphabetically, each appearing only once
    buyer_list = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)

with col2:
    # Only show grades that exist for the selected buyer
    grade_list = sorted(
        forecast[forecast['Buyer_Name'] == selected_buyer]['Grade']
        .unique().tolist()
    )
    selected_grade = st.selectbox('Select grade', grade_list)

# ── Filter forecast data ──────────────────────────────────────────────────────
grp = (
    forecast[
        (forecast['Buyer_Name'] == selected_buyer) &
        (forecast['Grade']      == selected_grade)
    ]
    .sort_values(['year', 'month'])
    .reset_index(drop=True)
)

if grp.empty:
    st.warning('No forecast data found for this combination.')
    st.stop()

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# OUTPUT 1 — Bar chart
# ═════════════════════════════════════════════════════════════════════════════
st.subheader(f'📊 Monthly forecast — {selected_buyer} · {selected_grade}')

fig, ax1 = plt.subplots(figsize=(14, 5))
x      = range(len(grp))
bar_w  = 0.4

# Left axis — buy probability
ax1.bar(x, grp['avg_buy_probability'],
        width=bar_w, color='steelblue', alpha=0.8,
        label='Buy probability')
ax1.set_ylabel('Buy probability', color='steelblue', fontsize=11)
ax1.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
ax1.set_ylim(0, 1)
ax1.tick_params(axis='y', labelcolor='steelblue')

# Right axis — expected quantity
ax2 = ax1.twinx()
ax2.bar([i + bar_w for i in x], grp['expected_qty'],
        width=bar_w, color='coral', alpha=0.8,
        label='Expected qty (bags)')
ax2.set_ylabel('Expected quantity (bags)', color='coral', fontsize=11)
ax2.tick_params(axis='y', labelcolor='coral')

ax1.set_xticks([i + bar_w / 2 for i in x])
ax1.set_xticklabels(grp['month_label'], rotation=45, ha='right')

legend_handles = [
    plt.Rectangle((0,0),1,1, color='steelblue', alpha=0.8),
    plt.Rectangle((0,0),1,1, color='coral',     alpha=0.8)
]
ax1.legend(legend_handles,
           ['Buy probability', 'Expected qty (bags)'],
           loc='upper left')

plt.tight_layout()
st.pyplot(fig)

# ═════════════════════════════════════════════════════════════════════════════
# OUTPUT 2 — Forecast table
# ═════════════════════════════════════════════════════════════════════════════
st.subheader('📋 Forecast table')

def likelihood(p):
    if p >= 0.7:   return '🟢 High'
    elif p >= 0.4: return '🟡 Medium'
    else:          return '🔴 Low'

forecast_table = grp[[
    'month_label',
    'avg_buy_probability',
    'expected_qty',
    'probability_wtd_qty'
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
    'Likelihood':           'Likelihood',
    'expected_qty':         'Expected qty (bags)',
    'probability_wtd_qty':  'Prob-weighted qty'
})

st.dataframe(forecast_table, use_container_width=True, hide_index=True)

st.download_button(
    label='⬇ Download forecast as CSV',
    data=forecast_table.to_csv(index=False),
    file_name=f'{selected_buyer}_{selected_grade}_forecast.csv',
    mime='text/csv',
    key='download_forecast'
)

# ═════════════════════════════════════════════════════════════════════════════
# OUTPUT 3 — Historical data table
# ═════════════════════════════════════════════════════════════════════════════
st.subheader('📂 Historical purchase data')
st.write('Actual purchase records used to train the model for this buyer and grade.')

hist = (
    historical[
        (historical['Buyer_Name'] == selected_buyer) &
        (historical['Grade']      == selected_grade)
    ]
    .sort_values(['year', 'month'])
    .reset_index(drop=True)
)

if hist.empty:
    st.info('No historical data found for this buyer and grade combination.')
else:
    # Build a clean readable version for display
    hist_display = hist[[
        'year', 'month', 'Qty', 'Average', 'purchased'
    ]].copy()

    hist_display['Month'] = pd.to_datetime(
        hist_display[['year','month']].assign(day=1)
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