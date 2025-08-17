import streamlit as st
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from streamlit_lottie import st_lottie
import requests
import os

def to_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def decimal_round(value, places=2):
    quantize_str = '1.' + '0'*places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def get_domain_from_ticker(ticker):
    domain_map = {
        "TCS.NS": "tcs.com",
        "INFY.NS": "infosys.com",
        "HDFCBANK.NS": "hdfcbank.com",
    }
    domain = domain_map.get(ticker, None)
    if domain:
        # Replace YOUR_API_TOKEN with your actual Logo.dev API token
        return f"https://img.logo.dev/{domain}?token=pk_Wnzoy1txRV67sh51JcuY3A"
    return None

def read_portfolio_from_excel(file_path):
    if not os.path.exists(file_path):
        st.error(f"Excel file not found at {file_path}")
        return []

    df = pd.read_excel(file_path)

    expected_cols = ['Symbol', 'Quantity Available', 'Average Price', 'Previous Closing Price']
    for col in expected_cols:
        if col not in df.columns:
            st.error(f"Required column '{col}' missing in Excel sheet.")
            return []

    portfolio = []
    for _, row in df.iterrows():
        ticker_raw = str(row.get('Symbol', '')).strip()
        if not ticker_raw:
            continue

        ticker = ticker_raw if ticker_raw.endswith('.NS') else f"{ticker_raw}.NS"
        company = ticker_raw

        shares = to_decimal(row.get('Quantity Available', 0))
        buy_price = to_decimal(row.get('Average Price', 0))
        prev_close = to_decimal(row.get('Previous Closing Price', 0))
        invested_amount = decimal_round(shares * buy_price)
        current_value = decimal_round(shares * prev_close)
        gain_loss = decimal_round(current_value - invested_amount)

        logo_url = get_domain_from_ticker(ticker)

        portfolio.append({
            "Ticker": ticker,
            "Company": company,
            "Shares": shares,
            "Buy Price": buy_price,
            "Previous Close Price": prev_close,
            "Invested Amount": invested_amount,
            "Current Value": current_value,
            "Gain/Loss": gain_loss,
            "Logo": logo_url,
        })
    return portfolio

# Premium dark theme CSS and Google Fonts
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<style>
body, [class*="css"]  {
    background: linear-gradient(120deg, #181d2f 0%, #213663 100%) !important;
    color: #fff !important;
    font-family: 'Montserrat', 'Playfair Display', sans-serif !important;
}
h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    color: #D5C67A;
    letter-spacing: 2px;
}
.metric-card {
    background: rgba(45,49,88,0.82);
    border-radius: 20px;
    box-shadow: 0 8px 24px rgba(60,70,150,0.33);
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(10px);
    text-align: center;
}
.metric-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #FFD700;
    margin: 0.5em 0;
    text-shadow: 0 2px 14px rgba(255,215,0,.25);
}
.metric-title {
    font-size: 1.1rem;
    color: #f4f4f4;
    margin-bottom: 0.7em;
    font-weight: 500;
}
.table_img {
    width: 35px;
    height: 35px;
    border-radius: 50%;
    object-fit: contain;
    border: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)

def format_currency(val):
    return f"₹{val:,.2f}"

def main():
    st.title("🪄 Elegant Premium Portfolio Tracker")

    excel_file_path = r"C:\Users\Dell\Downloads\holdings-GNU044.xlsx"  # update path accordingly
    portfolio = read_portfolio_from_excel(excel_file_path)
    if not portfolio:
        st.warning("No portfolio data found or Excel file missing.")
        return

    total_invested = sum(item["Invested Amount"] for item in portfolio)
    total_current = sum(item["Current Value"] for item in portfolio)
    total_gain = sum(item["Gain/Loss"] for item in portfolio)

    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-title">Total Invested</div>
      <div class="metric-value">{format_currency(total_invested)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Current Value</div>
      <div class="metric-value">{format_currency(total_current)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Net Gain/Loss</div>
      <div class="metric-value" style="color:#43aa8b;">{format_currency(total_gain)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("💎 Portfolio Holdings")

    df = pd.DataFrame(portfolio)

    def path_to_image_html(path):
        if path:
            return f'<img src="{path}" class="table_img">'
        else:
            return ""

    df['LogoImg'] = df['Logo'].apply(path_to_image_html)

    df['Shares'] = df['Shares'].apply(lambda x: f"{x:.4f}" if isinstance(x, Decimal) else x)
    df['Buy Price'] = df['Buy Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Previous Close Price'] = df['Previous Close Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Invested Amount'] = df['Invested Amount'].apply(format_currency)
    df['Current Value'] = df['Current Value'].apply(format_currency)
    df['Gain/Loss'] = df['Gain/Loss'].apply(format_currency)

    display_cols = ['LogoImg', 'Ticker', 'Company', 'Shares', 'Buy Price', 'Previous Close Price',
                    'Invested Amount', 'Current Value', 'Gain/Loss']

    df_display = df[display_cols].rename(columns={
        'LogoImg': '',
        'Buy Price': 'Buy Price (₹)',
        'Previous Close Price': 'Prev Close (₹)',
        'Invested Amount': 'Invested (₹)',
        'Current Value': 'Current Value (₹)',
        'Gain/Loss': 'Gain/Loss (₹)'
    })

    st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Use a tested public Lottie animation URL
    public_lottie_url = "https://assets5.lottiefiles.com/packages/lf20_V9t630.json"
    animation_json = load_lottie_url(public_lottie_url)
    if animation_json:
        st_lottie(animation_json, speed=1.2, height=200)
    else:
        st.warning("Animation failed to load.")

if __name__ == "__main__":
    main()
