import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ── Page config ───────────────────────────────────────────────────────────────
# Must be the very first Streamlit command called
st.set_page_config(
    page_title='Tea Buyer Forecast',
    page_icon='🍵',
    layout='wide'
)

# ── Password gate (Stateful) ──────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    # Center the form layout (35% left spacing, 30% center box, 35% right spacing)
    pad_left, center_col, pad_right = st.columns([3.5, 3, 3.5])
    
    with center_col:
        st.markdown("<h2 style='text-align: center;'>🔒 Secure Access</h2>", unsafe_allow_html=True)
        
        # Removing st.form completely eliminates the "Press Enter to submit form" text
        password = st.text_input(
            'Enter password', 
            type='password', 
            label_visibility='collapsed'
        )
        
        # Nested columns to cleanly center-align the standard button
        btn_pad_l, btn_col, btn_pad_r = st.columns([1, 1, 1])
        with btn_col:
            login_clicked = st.button('Login', use_container_width=True)
                
        # Validate credentials when the button is clicked
        if login_clicked:
            if password == st.secrets['APP_PASSWORD']:
                st.session_state['authenticated'] = True
                st.rerun()  # Instantly redraws the page to clear the login screen
            else:
                st.error('Incorrect password.')
                
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    forecast    = pd.read_csv('forecast.csv')
    historical  = pd.read_csv('historical.csv')
    return forecast, historical

forecast, historical = load_data()

# ── Main Application Interface ────────────────────────────────────────────────
st.title('🍵 Specialty Tea Buyer Forecast')
st.write('Select a buyer and grade to see their forecast and purchase history.')

# ── Dropdowns ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    buyer_list = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)

with col2:
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
# OUTPUT 1 — Interactive Altair Grouped Dual-Axis Bar Chart
# ═════════════════════════════════════════════════════════════════════════════
st.subheader(f'📊 Monthly forecast — {selected_buyer} · {selected_grade}')

# 1. Left Side Chart: Buy Probability
bar1 = alt.Chart(grp).mark_bar(size=15).encode(
    x=alt.X('month_label:N', title='Month', sort=None),
    xOffset=alt.value(-8),  # Shift this bar slightly to the left
    y=alt.Y('avg_buy_probability:Q', 
            title='Buy probability', 
            axis=alt.Axis(format='%', titleColor='steelblue', labelColor='steelblue'),
            scale=alt.Scale(domain=[0, 1])),
    color=alt.value('steelblue'),
    tooltip=[
        alt.Tooltip('month_label:N', title='Month'),
        alt.Tooltip('avg_buy_probability:Q', title='Buy Probability', format='.1%')
    ]
)

# 2. Right Side Chart: Expected Quantity
bar2 = alt.Chart(grp).mark_bar(size=15).encode(
    x=alt.X('month_label:N', title='Month', sort=None),
    xOffset=alt.value(8),   # Shift this bar slightly to the right
    y=alt.Y('expected_qty:Q', 
            title='Expected quantity (bags)', 
            axis=alt.Axis(titleColor='coral', labelColor='coral')),
    color=alt.value('coral'),
    tooltip=[
        alt.Tooltip('month_label:N', title='Month'),
        alt.Tooltip('expected_qty:Q', title='Expected Qty (bags)', format=',.1f')
    ]
)

# 3. Layer them together with independent Y-scales
interactive_chart = alt.layer(bar1, bar2).resolve_scale(
    y='independent'
).properties(
    width='container',
    height=400
).configure_axisX(
    labelAngle=45
)

st.altair_chart(interactive_chart, use_container_width=True)

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