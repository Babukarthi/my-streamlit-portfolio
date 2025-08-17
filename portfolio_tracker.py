import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from streamlit_lottie import st_lottie

# ---------- Utility Functions ----------
def to_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def decimal_round(value, places=2):
    quantize_str = '1.' + '0' * places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def read_portfolio_from_excel(url):
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Failed to fetch Excel file from GitHub.")
        return []

    excel_data = BytesIO(response.content)
    df = pd.read_excel(excel_data)

    required_cols = ['Symbol', 'Quantity Available', 'Average Price', 'Previous Closing Price']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column '{col}' in Excel sheet.")
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

        portfolio.append({
            "Ticker": ticker,
            "Company": company,
            "Shares": shares,
            "Buy Price": buy_price,
            "Previous Close Price": prev_close,
            "Invested Amount": invested_amount,
            "Current Value": current_value,
            "Gain/Loss": gain_loss,
        })
    return portfolio

# ---------- CSS Styling ----------
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
    margin: 0.5em 0;
    text-shadow: 0 2px 14px rgba(255,215,0,.25);
}
.metric-title {
    font-size: 1.1rem;
    color: #f4f4f4;
    margin-bottom: 0.7em;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# ---------- Helper ----------
def format_currency(val):
    return f"₹{val:,.2f}"

# Custom style for Gain/Loss in DataFrame
def color_gain(val):
    try:
        val_num = Decimal(str(val).replace("₹", "").replace(",", ""))
        color = "green" if val_num >= 0 else "red"
        return f"color: {color}; font-weight:600;"
    except:
        return ""

# ---------- Main ----------
def main():
    st.title("🪄 Elegant Premium Portfolio Tracker")

    github_excel_url = "https://raw.githubusercontent.com/Babukarthi/my-streamlit-portfolio/main/holdings-GNU044.xlsx"
    portfolio = read_portfolio_from_excel(github_excel_url)
    if not portfolio:
        st.warning("No portfolio data found or Excel file missing.")
        return

    total_invested = sum(item["Invested Amount"] for item in portfolio)
    total_current = sum(item["Current Value"] for item in portfolio)
    total_gain = sum(item["Gain/Loss"] for item in portfolio)

    # Color for net gain/loss
    gain_color = "#43aa8b" if total_gain >= 0 else "#d1495b"

    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-title">Total Invested</div>
      <div class="metric-value" style="color:#FFD700;">{format_currency(total_invested)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Current Value</div>
      <div class="metric-value" style="color:#FFD700;">{format_currency(total_current)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Net Gain/Loss</div>
      <div class="metric-value" style="color:{gain_color};">
        {format_currency(total_gain)}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("💎 Portfolio Holdings")

    df = pd.DataFrame(portfolio)
    df['Shares'] = df['Shares'].apply(lambda x: f"{x:.4f}" if isinstance(x, Decimal) else x)
    df['Buy Price'] = df['Buy Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Previous Close Price'] = df['Previous Close Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Invested Amount'] = df['Invested Amount'].apply(format_currency)
    df['Current Value'] = df['Current Value'].apply(format_currency)
    df['Gain/Loss'] = df['Gain/Loss'].apply(format_currency)

    # Apply color styling
    df_styled = df.style.applymap(color_gain, subset=['Gain/Loss'])
    st.dataframe(df_styled, height=600)

    # Lottie Animation
    lottie_url = "https://assets5.lottiefiles.com/packages/lf20_V9t630.json"
    animation_json = load_lottie_url(lottie_url)
    if animation_json:
        st_lottie(animation_json, speed=1.2, height=200)
    else:
        st.warning("Animation failed to load.")

if __name__ == "__main__":
    main()
