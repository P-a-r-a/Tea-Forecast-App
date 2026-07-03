import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from fpdf import FPDF
import tempfile
import os
import urllib.request
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Tea Buyer Forecast',
    page_icon='♨️',
    layout='wide',
    initial_sidebar_state='expanded'
)

# ── Initial loading screen overlay ─────────────────────────────────────────────────────
st.markdown("""
<div id="initial-page-overlay">
    <div class="loader">
        <div class="cup">
            <div class="cup-handle"></div>
            <div class="smoke one"></div>
            <div class="smoke two"></div>
            <div class="smoke three"></div>
        </div>
        <div class="load">Loading...</div>
    </div>
</div>

<style>
    /* Full-screen overlay container that positions your loader exactly in the center */
    #initial-page-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 99999;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        animation: smoothFadeOut 3.5s forwards;
        pointer-events: none;
    }

    /* Your exact custom Loader CSS */
    .loader {
        width: 200px;
        height: 200px;
        position: relative;
        animation: shake 3s infinite ease-in-out;
    }

    .cup {
        position: absolute;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 40px;
        height: 30px;
        background-color: #5b4022cb;
        border: 1px solid #2e2e2e;
        border-radius: 3px 3px 10px 10px;
        z-index: 1;
        animation: cupPulse 6s infinite ease-in-out;
    }

    .cup::before {
        content: "";
        position: absolute;
        bottom: -5px;
        width: calc(100% - 2px);
        height: 6px;
        background: #5b4022cb;
        border: 1px solid #2e2e2e;
        border-top: none;
        border-radius: 50%;
        z-index: -1;
        animation: cupPulse 6s infinite ease-in-out;
    }

    .cup::after {
        content: "";
        position: absolute;
        top: -2px;
        left: 1px;
        width: calc(100% - 2px);
        height: 4px;
        background: #da8920ca;
        border: 1px solid #2e2e2e;
        border-radius: 50%;
        animation: coffeeGlow 6s infinite ease-in-out;
    }

    .cup-handle {
        position: absolute;
        top: 5px;
        right: -10px;
        width: 10px;
        height: 15px;
        border: 2px solid #2e2e2e;
        border-left: none;
        border-radius: 0 10px 10px 0;
        background: transparent;
    }

    .smoke {
        position: absolute;
        bottom: 100%;
        left: 50%;
        width: 10px;
        height: 25px;
        background: rgba(150, 150, 150, 0.5); /* Boosted visibility against dark background */
        border-radius: 50%;
        transform: translateX(-50%);
        animation: rise 3s infinite ease-in-out;
        filter: blur(5px); /* Slightly reduced blur to keep it sharp on screens */
    }

    .smoke.one { animation-delay: 0s; }
    .smoke.two { animation-delay: 0.8s; }
    .smoke.three { animation-delay: 1.6s; }

    .load {
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        font-size: 12px;
        color: #ffffff; /* Changed to white to match your #111 screen background */
        opacity: 0.7;
    }

    /* Keyframe Animations */
    @keyframes rise {
        0% {
            transform: translate(-50%, 0) scale(0.4);
            opacity: 0;
        }
        30% {
            opacity: 0.7;
        }
        60% {
            opacity: 0.4;
        }
        100% {
            transform: translate(-50%, -120px) scale(1);
            opacity: 0;
        }
    }

    @keyframes shake {
        0% { transform: translateX(0) translateY(0) rotate(0); }
        25% { transform: translateX(-4px) translateY(-2px) rotate(-2deg); }
        50% { transform: translateX(0) translateY(0) rotate(0); }
        75% { transform: translateX(4px) translateY(-2px) rotate(2deg); }
        100% { transform: translateX(0) translateY(0) rotate(0); }
    }

    @keyframes cupPulse {
        0%, 100% { background-color: #5b4022cb; }
        50% { background-color: #f5f5f5bd; }
    }

    @keyframes coffeeGlow {
        0%, 100% { background: #da8920ca; }
        50% { background: #fed197d5; }
    }

    /* Graceful fade out to natively transition into your app layout */
    @keyframes smoothFadeOut {
        0% { opacity: 1; visibility: visible; }
        75% { opacity: 1; visibility: visible; }
        99% { opacity: 0; visibility: visible; }
        100% { opacity: 0; visibility: hidden; display: none; }
    }
</style>
""", unsafe_allow_html=True)

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
                
                # Display a full-screen overlay with a decryption animation
                st.markdown("""
                    <div style="
                        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                        background: radial-gradient(circle, #1a2a6c, #b21f1f, #fdbb2d); z-index: 999999;
                        display: flex; flex-direction: column; justify-content: center; align-items: center;
                        color: white; font-family: sans-serif;">
                        <div style="font-size: 50px; margin-bottom: 20px; animation: pulse 1.5s infinite;">🔒</div>
                        <h2>Decrypting & Accessing Secure Database...</h2>
                    </div>
                    <style>
                        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
                    </style>
                """, unsafe_allow_html=True)
                time.sleep(1.5)
                
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

# ── Font download helper ──────────────────────────────────────────────────────
@st.cache_data
def get_fonts():
    """Download Noto Sans fonts once per session, cache to /tmp."""
    regular_path = '/tmp/NotoSans-Regular.ttf'
    bold_path    = '/tmp/NotoSans-Bold.ttf'
    if not os.path.exists(regular_path):
        urllib.request.urlretrieve(
            'https://github.com/googlefonts/noto-fonts/raw/main/'
            'hinted/ttf/NotoSans/NotoSans-Regular.ttf',
            regular_path
        )
    if not os.path.exists(bold_path):
        urllib.request.urlretrieve(
            'https://github.com/googlefonts/noto-fonts/raw/main/'
            'hinted/ttf/NotoSans/NotoSans-Bold.ttf',
            bold_path
        )
    return regular_path, bold_path

# ── PDF builder ───────────────────────────────────────────────────────────────
def build_pdf(title, chart_fig, tables: dict) -> bytes:
    """
    Renders a Plotly figure to PNG then builds a PDF containing
    the chart followed by each table in `tables`.
    tables = {'Table title': dataframe, ...}
    Returns PDF as bytes.
    """
    font_regular, font_bold = get_fonts()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.add_font('Noto', '',  font_regular, uni=True)
    pdf.add_font('Noto', 'B', font_bold,    uni=True)

    # Title
    pdf.set_font('Noto', 'B', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(4)

    # Chart image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    pio.write_image(chart_fig, tmp_path, format='png', width=1100, height=450)
    pdf.image(tmp_path, x=10, w=190)
    os.unlink(tmp_path)
    pdf.ln(6)

    # Tables
    for table_title, df in tables.items():
        pdf.set_font('Noto', 'B', 12)
        pdf.cell(0, 8, table_title, ln=True)
        pdf.ln(2)

        col_count = len(df.columns)
        col_width = 190 / col_count

        # Header row
        pdf.set_font('Noto', 'B', 9)
        pdf.set_fill_color(220, 230, 241)
        for col in df.columns:
            pdf.cell(col_width, 7, str(col), border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font('Noto', '', 9)
        for _, row in df.iterrows():
            for val in row:
                pdf.cell(col_width, 6, str(val), border=1)
            pdf.ln()

        pdf.ln(6)

    return bytes(pdf.output())

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title('♨️ Specialty Tea Buyer Forecast')
st.write('Select a buyer, year, and grade to see their monthly forecast.')

# ── Sidebar: Buyer | Year | Grade ────────────────────────────────────────────
with st.sidebar:
    st.header('🔍 Filter Options')

    buyer_list     = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)
    if 'previous_buyer' not in st.session_state:
        st.session_state['previous_buyer'] = selected_buyer

    if st.session_state['previous_buyer'] != selected_buyer:
        st.markdown(f"""
            <div style="
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(255, 255, 255, 0.95); z-index: 99999;
                display: flex; flex-direction: column; justify-content: center; align-items: center;
                font-family: Arial, sans-serif;">
                <div style="width: 60px; height: 60px; border: 5px solid #ccc; border-bottom-color: #ff7f50; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
                <h2 style="color: #333; margin-top: 20px;">Fetching metrics for <b>{selected_buyer}</b>...</h2>
                <p style="color: #777;">Recalculating forecast models and charting records</p>
            </div>
            <style>
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
        """, unsafe_allow_html=True)
        st.session_state['previous_buyer'] = selected_buyer
        time.sleep(1.2) # Yields execution to let browser show CSS before layout update
        st.rerun()

    selected_year  = st.selectbox('Select year', list(range(2023, 2031)))

    # Determine which grades have data for this buyer + year
    if selected_year <= 2025:
        source = historical[
            (historical['Buyer_Name'] == selected_buyer) &
            (historical['year']       == selected_year)  &
            (historical['purchased']  == 1)
        ]
    else:
        source = forecast[
            (forecast['Buyer_Name'] == selected_buyer) &
            (forecast['year']       == selected_year)
        ]

    grades_with_data = source['Grade'].unique().tolist()

    # Preserve selected grade across year changes using session state
    if 'selected_grade' not in st.session_state:
        st.session_state['selected_grade'] = ALL_GRADES[0]

    # Append "- no data" marker to inactive grades so user can tell at a glance
    grade_display_list = [
        g if g in grades_with_data else f'{g}  - no data'
        for g in ALL_GRADES
    ]

    # Find the index of the currently stored grade in the display list
    # Match by checking if the stored grade is contained in the display string
    current_index = 0
    for i, display_str in enumerate(grade_display_list):
        if st.session_state['selected_grade'] in display_str:
            current_index = i
            break

    selected_grade_display = st.selectbox(
        'Select grade',
        grade_display_list,
        index=current_index
    )

    # Strip marker to get the clean grade name used in all filters
    selected_grade = selected_grade_display.replace('  - no data', '').strip()

    # Save back to session state so it persists when year changes
    st.session_state['selected_grade'] = selected_grade

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

    # ── Title row with PDF button placeholder ─────────────────────────────────
    report_title = (
        f'Monthly Sales — {selected_buyer} · {selected_grade} · {selected_year}'
    )
    title_col, pdf_btn_col = st.columns([5, 1])
    with title_col:
        st.subheader(f'🗓️ {report_title}')
    # pdf_btn_col is filled after chart and table are built below

    # ── Dual bar chart ────────────────────────────────────────────────────────
    fig_hist = go.Figure()

    fig_hist.add_trace(go.Bar(
        name='Quantity Sold (bags)',
        x=hist_plot['month_label'],
        y=hist_plot['Qty'],
        marker_color='steelblue',
        yaxis='y1',
        offsetgroup=1,
        hovertemplate='<b>%{x}</b><br>Qty sold: %{y:,.0f} bags<extra></extra>'
    ))

    fig_hist.add_trace(go.Bar(
        name='Average Price',
        x=hist_plot['month_label'],
        y=hist_plot['Average'],
        marker_color='coral',
        yaxis='y2',
        offsetgroup=2,
        hovertemplate='<b>%{x}</b><br>Avg price: %{y:,.2f}<extra></extra>'
    ))

    fig_hist.update_layout(
        barmode='group',
        height=450,
        xaxis=dict(
            title='Month',
            categoryorder='array',
            categoryarray=MONTH_ORDER
        ),
        yaxis=dict(
            title_text='Qty sold (bags)',
            title_font_color='steelblue',
            tickfont_color='steelblue',
            showgrid=False,
            rangemode='tozero'
        ),
        yaxis2=dict(
            title_text='Avg price',
            title_font_color='coral',
            tickfont_color='coral',
            overlaying='y',
            side='right',
            showgrid=False,
            rangemode='tozero'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(t=80, b=40, l=60, r=60)
    )

    st.plotly_chart(fig_hist, use_container_width=True)

    # ── Sales table ───────────────────────────────────────────────────────────
    st.subheader('✍️ Monthly sales table')

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
        label='⬇️ Download table as CSV',
        data=sales_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_sales.csv',
        mime='text/csv',
        key='download_sales'
    )

    # ── PDF report — placed in the title row column ───────────────────────────
    with st.spinner('Preparing PDF report...'):
        pdf_bytes_hist = build_pdf(
            title=report_title,
            chart_fig=fig_hist,
            tables={'Monthly Sales Table': sales_table}
        )
    with pdf_btn_col:
        st.markdown('<div style="margin-top:28px;"></div>',
                    unsafe_allow_html=True)
        st.download_button(
            label='⬇️ Download Full report',
            data=pdf_bytes_hist,
            file_name=(
                f'{selected_buyer}_{selected_grade}'
                f'_{selected_year}_report.pdf'
            ),
            mime='application/pdf',
            key='download_pdf_hist'
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

    # ── Title row with PDF button placeholder ─────────────────────────────────
    report_title = (
        f'Monthly Forecast — {selected_buyer} · {selected_grade} · {selected_year}'
    )
    title_col, pdf_btn_col = st.columns([5, 1])
    with title_col:
        st.subheader(f'🗓️ {report_title}')
    # pdf_btn_col is filled after all data is built below

    # ── Triple bar chart ──────────────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Probability of Purchase',
        x=fcst_plot['month_label'],
        y=fcst_plot['avg_buy_probability'],
        marker_color='steelblue',
        yaxis='y1',
        offsetgroup=1,
        hovertemplate='<b>%{x}</b><br>Buy probability: %{y:.1%}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Predicted Quantity (bags)',
        x=fcst_plot['month_label'],
        y=fcst_plot['expected_qty'],
        marker_color='coral',
        yaxis='y2',
        offsetgroup=2,
        customdata=fcst_plot['probability_wtd_qty'],
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Predicted qty: %{y:,.1f} bags<br>'
            'Weighted qty: %{customdata:,.1f} bags'
            '<extra></extra>'
        )
    ))

    fig.add_trace(go.Bar(
        name='Weighted Quantity (bags)',
        x=fcst_plot['month_label'],
        y=fcst_plot['probability_wtd_qty'],
        marker_color='seagreen',
        yaxis='y2',
        offsetgroup=3,
        customdata=fcst_plot['expected_qty'],
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Predicted qty: %{customdata:,.1f} bags<br>'
            'Weighted qty: %{y:,.1f} bags'
            '<extra></extra>'
        )
    ))

    fig.update_layout(
        barmode='group',
        height=450,
        xaxis=dict(
            title='Month',
            categoryorder='array',
            categoryarray=MONTH_ORDER
        ),
        yaxis=dict(
            title_text='Buy probability',
            title_font_color='steelblue',
            tickfont_color='steelblue',
            tickformat='.0%',
            showgrid=True,
            rangemode='tozero'
        ),
        yaxis2=dict(
            title_text='Quantity (bags)',
            title_font_color='coral',
            tickfont_color='coral',
            overlaying='y',
            side='right',
            showgrid=False,
            rangemode='tozero'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(t=80, b=40, l=60, r=60)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Likelihood helpers ────────────────────────────────────────────────────
    def likelihood_emoji(p):
        if p >= 0.5:   return '🟢 High'
        elif p >= 0.3: return '🟡 Medium'
        else:          return '🔴 Low'

    def likelihood_clean(p):
        if p >= 0.5:   return 'High'
        elif p >= 0.3: return 'Medium'
        else:          return 'Low'

    # ── Build forecast tables ─────────────────────────────────────────────────
    base = fcst_plot[[
        'month_label', 'avg_buy_probability',
        'expected_qty', 'probability_wtd_qty'
    ]].copy()
    base['expected_qty']        = base['expected_qty'].round(1)
    base['probability_wtd_qty'] = base['probability_wtd_qty'].round(1)

    # Display version — emojis for app
    forecast_display = base.copy()
    forecast_display['Likelihood'] = (
        forecast_display['avg_buy_probability'].apply(likelihood_emoji)
    )
    forecast_display['avg_buy_probability'] = (
        forecast_display['avg_buy_probability'] * 100
    ).round(1).astype(str) + '%'
    forecast_display = forecast_display.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Probability of Purchase',
        'expected_qty':         'Predicted Quantity (bags)',
        'probability_wtd_qty':  'Weighted Quantity (bags)',
    })[['Month', 'Probability of Purchase', 'Likelihood',
        'Predicted Quantity (bags)', 'Weighted Quantity (bags)']]

    # Download version — no emojis for CSV and PDF
    forecast_download = base.copy()
    forecast_download['Likelihood'] = (
        forecast_download['avg_buy_probability'].apply(likelihood_clean)
    )
    forecast_download['avg_buy_probability'] = (
        forecast_download['avg_buy_probability'] * 100
    ).round(1).astype(str) + '%'
    forecast_download = forecast_download.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Probability of Purchase',
        'expected_qty':         'Predicted Quantity (bags)',
        'probability_wtd_qty':  'Weighted Quantity (bags)',
    })[['Month', 'Probability of Purchase', 'Likelihood',
        'Predicted Quantity (bags)', 'Weighted Quantity (bags)']]

    # ── Filter toggle — affects forecast table only ───────────────────────────
    show_above_50 = st.toggle(
        'Show only months with 🟢 High probability (≥ 50%)',
        value=False
    )

    display_table  = forecast_display.copy()
    download_table = forecast_download.copy()

    if show_above_50:
        mask           = fcst_plot['avg_buy_probability'] >= 0.5
        display_table  = forecast_display[mask.values].reset_index(drop=True)
        download_table = forecast_download[mask.values].reset_index(drop=True)

        if display_table.empty:
            st.info(
                f'No months in {selected_year} where **{selected_buyer}** '
                f'has a predicted buy probability ≥ 50% for **{selected_grade}**.'
            )
            st.stop()

    # ── Forecast table ────────────────────────────────────────────────────────
    st.subheader('📋 Forecast table')
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    st.download_button(
        label='⬇️ Download forecast as CSV',
        data=download_table.to_csv(index=False),
        file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_forecast.csv',
        mime='text/csv',
        key='download_forecast'
    )

    # ── Historical reference table — not affected by toggle ───────────────────
    st.subheader('🕰️ Historical purchase data')
    st.write('Actual purchase records used to train the model for this buyer and grade.')

    hist_all = (
        historical[
            (historical['Buyer_Name'] == selected_buyer) &
            (historical['Grade']      == selected_grade)
        ]
        .sort_values(['year', 'month'])
        .reset_index(drop=True)
    )

    hist_download = None

    if hist_all.empty:
        st.info(
            f'No historical purchase data found for '
            f'**{selected_buyer}** · **{selected_grade}**.'
        )
    else:
        hist_base          = hist_all[['year','month','Qty','Average','purchased']].copy()
        hist_base['Month'] = pd.to_datetime(
            hist_base[['year','month']].assign(day=1)
        ).dt.strftime('%b %Y')
        hist_base['purchased'] = hist_base['purchased'].fillna(0).astype(int)
        hist_base['Qty']       = hist_base['Qty'].astype(int)
        hist_base['Average']   = hist_base['Average'].round(2)

        # Display version — emojis
        hist_display = hist_base.copy()
        hist_display['Purchased'] = hist_base['purchased'].map(
            {1: '✅ Yes', 0: '❌ No'}
        )
        hist_display = hist_display[
            ['Month', 'Purchased', 'Qty', 'Average']
        ].rename(columns={
            'Qty':     'Quantity Purchased (bags)',
            'Average': 'Average Price'
        })

        # Download version — no emojis
        hist_download = hist_base.copy()
        hist_download['Purchased'] = hist_base['purchased'].map(
            {1: 'Yes', 0: 'No'}
        )
        hist_download = hist_download[
            ['Month', 'Purchased', 'Qty', 'Average']
        ].rename(columns={
            'Qty':     'Quantity Purchased (bags)',
            'Average': 'Average Price'
        })

        st.dataframe(hist_display, use_container_width=True, hide_index=True)

        st.download_button(
            label='⬇️ Download historical data as CSV',
            data=hist_download.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_history.csv',
            mime='text/csv',
            key='download_history'
        )

    # ── PDF report — placed in the title row column ───────────────────────────
    tables_for_pdf = {'Forecast Table': download_table}
    if hist_download is not None:
        tables_for_pdf['Historical Purchase Data'] = hist_download

    with st.spinner('Preparing PDF report...'):
        pdf_bytes_fcst = build_pdf(
            title=report_title,
            chart_fig=fig,
            tables=tables_for_pdf
        )
    with pdf_btn_col:
        st.markdown('<div style="margin-top:28px;"></div>',
                    unsafe_allow_html=True)
        st.download_button(
            label='⬇️ Download Full Report',
            data=pdf_bytes_fcst,
            file_name=(
                f'{selected_buyer}_{selected_grade}'
                f'_{selected_year}_report.pdf'
            ),
            mime='application/pdf',
            key='download_pdf_fcst'
        )