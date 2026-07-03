import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from fpdf import FPDF
import tempfile
import os
import io

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Tea Buyer Forecast',
    page_icon='☕',
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

# ── PDF generation helper ─────────────────────────────────────────────────────
def build_pdf(title, chart_fig, tables: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Use DejaVu — bundled with fpdf2, supports full Unicode
    # This handles all special characters in buyer names
    pdf.add_font('DejaVu', '',
                 '/home/adminuser/venv/lib/python3.14/site-packages/fpdf/fonts/DejaVuSans.ttf',
                 uni=True)
    pdf.add_font('DejaVu', 'B',
                 '/home/adminuser/venv/lib/python3.14/site-packages/fpdf/fonts/DejaVuSans-Bold.ttf',
                 uni=True)

    # Title
    pdf.set_font('DejaVu', 'B', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(4)

    # Export chart to temporary PNG
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name

    pio.write_image(chart_fig, tmp_path, format='png', width=1100, height=450)
    pdf.image(tmp_path, x=10, w=190)
    os.unlink(tmp_path)
    pdf.ln(6)

    # Tables
    for table_title, df in tables.items():
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 8, table_title, ln=True)
        pdf.ln(2)

        col_count = len(df.columns)
        col_width = 190 / col_count

        # Header row
        pdf.set_font('DejaVu', 'B', 9)
        pdf.set_fill_color(220, 230, 241)
        for col in df.columns:
            pdf.cell(col_width, 7, str(col), border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font('DejaVu', '', 9)
        for _, row in df.iterrows():
            for val in row:
                pdf.cell(col_width, 6, str(val), border=1)
            pdf.ln()

        pdf.ln(6)

    return bytes(pdf.output())

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title('☕ Specialty Tea Buyer Forecast')
st.write('Select a buyer, year, and grade to see their monthly forecast.')

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('🔍 Filter Options')

    buyer_list     = sorted(forecast['Buyer_Name'].unique().tolist())
    selected_buyer = st.selectbox('Select buyer', buyer_list)
    selected_year  = st.selectbox('Select year', list(range(2023, 2031)))

    # ── Grade dropdown with inactive markers ──────────────────────────────────
    # Check which grades have data for this buyer + year combination
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

    # Build display list — append " (no data)" to inactive grades
    grade_display_list = [
        g if g in grades_with_data else f'{g}  - no data'
        for g in ALL_GRADES
    ]

    selected_grade_display = st.selectbox('Select grade', grade_display_list)

    # Strip the marker to get the clean grade name for filtering
    selected_grade = selected_grade_display.replace('  - no data', '').strip()

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
    hist_plot['Average']   = np.where(
        hist_plot['purchased'] == 1,
        hist_plot['Average'].fillna(0),
        0.0
    )

    # ── Chart ─────────────────────────────────────────────────────────────────
    report_title = (
        f'Monthly Sales — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    title_col, btn_col = st.columns([6, 1])
    with title_col:
        st.subheader(f'🗓️ {report_title}')

    fig_hist = go.Figure()

    fig_hist.add_trace(go.Bar(
        name='Qty sold (bags)',
        x=hist_plot['month_label'],
        y=hist_plot['Qty'],
        marker_color='steelblue',
        yaxis='y1',
        offsetgroup=1,
        hovertemplate='<b>%{x}</b><br>Qty sold: %{y:,.0f} bags<extra></extra>'
    ))

    fig_hist.add_trace(go.Bar(
        name='Avg price',
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
            orientation='h', yanchor='bottom',
            y=1.02, xanchor='right', x=1
        ),
        margin=dict(t=80, b=40, l=60, r=60)
    )

    st.plotly_chart(fig_hist, use_container_width=True)

    # ── Table ─────────────────────────────────────────────────────────────────
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

    dl_csv, dl_pdf = st.columns([1, 1])

    with dl_csv:
        st.download_button(
            label='⬇️ Download table as CSV',
            data=sales_table.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_sales.csv',
            mime='text/csv',
            key='download_sales'
        )

    with dl_pdf:
        with st.spinner('Preparing PDF report...'):
            pdf_bytes = build_pdf(
                title=report_title,
                chart_fig=fig_hist,
                tables={'Monthly Sales Table': sales_table}
            )
        st.download_button(
            label='⬇️ Download full report (PDF)',
            data=pdf_bytes,
            file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_report.pdf',
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

    # ── Chart ─────────────────────────────────────────────────────────────────
    report_title = (
        f'Monthly Forecast — {selected_buyer} · {selected_grade} · {selected_year}'
    )

    st.subheader(f'🗓️ {report_title}')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Buy probability',
        x=fcst_plot['month_label'],
        y=fcst_plot['avg_buy_probability'],
        marker_color='steelblue',
        yaxis='y1',
        offsetgroup=1,
        hovertemplate='<b>%{x}</b><br>Buy probability: %{y:.1%}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        name='Predicted qty (bags)',
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
        name='Weighted qty (bags)',
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
            orientation='h', yanchor='bottom',
            y=1.02, xanchor='right', x=1
        ),
        margin=dict(t=80, b=40, l=60, r=60)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Build tables ──────────────────────────────────────────────────────────
    def likelihood_emoji(p):
        if p >= 0.5:   return '🟢 High'
        elif p >= 0.3: return '🟡 Medium'
        else:          return '🔴 Low'

    def likelihood_clean(p):
        if p >= 0.5:   return 'High'
        elif p >= 0.3: return 'Medium'
        else:          return 'Low'

    base = fcst_plot[[
        'month_label', 'avg_buy_probability',
        'expected_qty', 'probability_wtd_qty'
    ]].copy()
    base['expected_qty']        = base['expected_qty'].round(1)
    base['probability_wtd_qty'] = base['probability_wtd_qty'].round(1)

    # Display version (with emojis)
    forecast_display = base.copy()
    forecast_display['Likelihood'] = (
        forecast_display['avg_buy_probability'].apply(likelihood_emoji)
    )
    forecast_display['avg_buy_probability'] = (
        forecast_display['avg_buy_probability'] * 100
    ).round(1).astype(str) + '%'
    forecast_display = forecast_display.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Buy probability',
        'expected_qty':         'Predicted qty (bags)',
        'probability_wtd_qty':  'Weighted qty (bags)',
    })[['Month', 'Buy probability', 'Likelihood',
        'Predicted qty (bags)', 'Weighted qty (bags)']]

    # Download version (no emojis — for CSV and PDF)
    forecast_download = base.copy()
    forecast_download['Likelihood'] = (
        forecast_download['avg_buy_probability'].apply(likelihood_clean)
    )
    forecast_download['avg_buy_probability'] = (
        forecast_download['avg_buy_probability'] * 100
    ).round(1).astype(str) + '%'
    forecast_download = forecast_download.rename(columns={
        'month_label':          'Month',
        'avg_buy_probability':  'Buy probability',
        'expected_qty':         'Predicted qty (bags)',
        'probability_wtd_qty':  'Weighted qty (bags)',
    })[['Month', 'Buy probability', 'Likelihood',
        'Predicted qty (bags)', 'Weighted qty (bags)']]

    # ── Filter toggle ─────────────────────────────────────────────────────────
    st.divider()

    show_above_50 = st.toggle(
        'Show only months with 🟢 High probability (≥ 50%)',
        value=False
    )

    display_table   = forecast_display.copy()
    download_table  = forecast_download.copy()

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

    dl_csv_f, dl_pdf_f = st.columns([1, 1])

    with dl_csv_f:
        st.download_button(
            label='⬇️ Download forecast as CSV',
            data=download_table.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_forecast.csv',
            mime='text/csv',
            key='download_forecast'
        )

    # ── Historical reference table ────────────────────────────────────────────
    # Not affected by the toggle
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

    hist_display  = None
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

        hist_display = hist_base.copy()
        hist_display['Purchased'] = hist_base['purchased'].map(
            {1: '✅ Yes', 0: '❌ No'}
        )
        hist_display = hist_display[
            ['Month','Purchased','Qty','Average']
        ].rename(columns={'Qty':'Qty purchased (bags)','Average':'Avg price'})

        hist_download = hist_base.copy()
        hist_download['Purchased'] = hist_base['purchased'].map(
            {1: 'Yes', 0: 'No'}
        )
        hist_download = hist_download[
            ['Month','Purchased','Qty','Average']
        ].rename(columns={'Qty':'Qty purchased (bags)','Average':'Avg price'})

        st.dataframe(hist_display, use_container_width=True, hide_index=True)

        st.download_button(
            label='⬇️ Download historical data as CSV',
            data=hist_download.to_csv(index=False),
            file_name=f'{selected_buyer}_{selected_grade}_history.csv',
            mime='text/csv',
            key='download_history'
        )

    # ── PDF report button (placed after both tables are built) ────────────────
    with dl_pdf_f:
        tables_for_pdf = {'Forecast Table': download_table}
        if hist_download is not None:
            tables_for_pdf['Historical Purchase Data'] = hist_download

        with st.spinner('Preparing PDF report...'):
            pdf_bytes = build_pdf(
                title=report_title,
                chart_fig=fig,
                tables=tables_for_pdf
            )
        st.download_button(
            label='⬇️ Download full report (PDF)',
            data=pdf_bytes,
            file_name=f'{selected_buyer}_{selected_grade}_{selected_year}_report.pdf',
            mime='application/pdf',
            key='download_pdf_fcst'
        )