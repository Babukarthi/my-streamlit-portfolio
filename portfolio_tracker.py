import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
import yfinance as yf

# ---------------- Utility Functions ----------------
def to_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def decimal_round(value, places=2):
    quantize_str = '1.' + '0' * places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def fetch_dividends(ticker):
    stock = yf.Ticker(ticker)
    try:
        return stock.dividends
    except Exception:
        return pd.Series(dtype='float64')

# ---------------- Portfolio Functions ----------------
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

# ---------------- Formatting & Styling ----------------
st.markdown("""
<style>
body, [class*="css"]  {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364) !important;
    color: #f8f9fa !important;
    font-family: 'Montserrat', 'Playfair Display', sans-serif !important;
}
h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    color: #FFCF56;
    letter-spacing: 1.5px;
}
.metric-card {
    background: rgba(21, 25, 45, 0.8);
    border-radius: 16px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.4);
    padding: 1.4rem 2rem;
    margin-bottom: 1.4rem;
    backdrop-filter: blur(12px);
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    border: 1px solid rgba(255,255,255,0.08);
}
.metric-card:hover {
    transform: translateY(-5px) scale(1.01);
    box-shadow: 0 10px 28px rgba(0,0,0,0.55);
}
.metric-value {
    font-size: 2.4rem;
    font-weight: 700;
    margin: 0.6em 0;
}
.metric-title {
    font-size: 1.05rem;
    color: #e0e0e0;
    margin-bottom: 0.5em;
    font-weight: 500;
    letter-spacing: 1px;
}
[data-testid="stDataFrame"] table {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.1);
    font-size: 0.95rem;
    background: rgba(20, 25, 45, 0.65);
    backdrop-filter: blur(10px);
}
[data-testid="stDataFrame"] th {
    background: rgba(30, 35, 60, 0.95) !important;
    color: #FFD700 !important;
    font-weight: 700 !important;
    text-transform: uppercase;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background: rgba(255,255,255,0.02);
}
[data-testid="stDataFrame"] tbody tr:hover {
    background: rgba(255,215,0,0.08);
    transition: background 0.3s ease;
}
</style>
""", unsafe_allow_html=True)

def format_currency(val):
    return f"₹{val:,.2f}"

def color_gain(val):
    try:
        val_num = Decimal(str(val).replace("₹", "").replace(",", ""))
        color = "green" if val_num >= 0 else "red"
        return f"color: {color}; font-weight:600;"
    except:
        return ""

def color_current_value(row):
    try:
        curr_val = Decimal(str(row["Current Value"]).replace("₹", "").replace(",", ""))
        inv_val = Decimal(str(row["Invested Amount"]).replace("₹", "").replace(",", ""))
        color = "green" if curr_val >= inv_val else "red"
        return [f"color:{color}; font-weight:600;" if col == "Current Value" else "" for col in row.index]
    except:
        return ["" for _ in row.index]

# ---------------- Dividend Tracker Functions ----------------
def get_dividend_portfolio():
    st.info("Enter stock tickers and quantities owned for dividend tracking.")
    tickers_str = st.text_area("Tickers (comma separated, e.g. TCS.NS, INFY.NS):")
    quantities_str = st.text_area("Quantities (comma separated, e.g. 10, 20):")
    
    tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
    quantities = [to_decimal(q.strip()) for q in quantities_str.split(",") if q.strip()]
    
    if len(tickers) != len(quantities):
        st.error("Ticker count and quantity count must be equal.")
        return []
    
    portfolio = []
    for t, q in zip(tickers, quantities):
        portfolio.append({"Ticker": t, "Shares": q})
    return portfolio

def dividend_tracker():
    st.title("📈 Dividend Income Tracker")

    portfolio = get_dividend_portfolio()
    if not portfolio:
        st.warning("Enter your portfolio holdings above.")
        return

    year = st.selectbox("Select Year", options=[str(y) for y in range(2000, 2100)], index=25)

    monthly_dividends = {month: Decimal("0") for month in range(1, 13)}

    for item in portfolio:
        ticker = item["Ticker"]
        shares = item["Shares"]
        dividends = fetch_dividends(ticker)
        if dividends.empty:
            continue
        
        # Filter dividends by year
        div_selected_year = dividends[dividends.index.year == int(year)]
        
        # Sum dividends by month
        monthly_sum = div_selected_year.groupby(div_selected_year.index.month).sum()
        
        # Add weighted by shares
        for month, div_value in monthly_sum.items():
            monthly_dividends[month] += shares * Decimal(div_value)

    df_dividends = pd.DataFrame([
        {"Month": pd.Timestamp(year=int(year), month=m, day=1).strftime("%B"), 
         "Dividend Received (₹)": float(monthly_dividends[m])}
        for m in range(1, 13)
    ])

    total_div = sum(monthly_dividends.values())

    st.subheader(f"Dividend Income - {year}")
    st.dataframe(df_dividends)
    st.markdown(f"### Total Dividend Received in {year}: ₹{total_div:.2f}")


# ---------------- Main App ----------------
def portfolio_tracker():
    st.title("🪄 Elegant Premium Portfolio Tracker")

    github_excel_url = "https://raw.githubusercontent.com/Babukarthi/my-streamlit-portfolio/main/holdings-GNU044.xlsx"
    portfolio = read_portfolio_from_excel(github_excel_url)

    if not portfolio:
        st.warning("No portfolio data found or Excel file missing.")
        return

    total_invested = sum(item["Invested Amount"] for item in portfolio)
    total_current = sum(item["Current Value"] for item in portfolio)
    total_gain = sum(item["Gain/Loss"] for item in portfolio)

    gain_color = "#43aa8b" if total_gain >= 0 else "#d1495b"

    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-title">Total Invested</div>
      <div class="metric-value" style="color:#FFD700;">{format_currency(total_invested)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Current Value</div>
      <div class="metric-value" style="color:#00BFFF;">{format_currency(total_current)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-title">Net Gain/Loss</div>
      <div class="metric-value" style="color:{gain_color};">
        {format_currency(total_gain)}
      </div>
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(portfolio)

    # Remove Ticker
    df = df.drop(columns=["Ticker"])

    # Shares integer
    df['Shares'] = df['Shares'].apply(lambda x: f"{int(x)}" if isinstance(x, Decimal) else x)

    # Format currencies
    df['Buy Price'] = df['Buy Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Previous Close Price'] = df['Previous Close Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Invested Amount'] = df['Invested Amount'].apply(format_currency)
    df['Current Value'] = df['Current Value'].apply(format_currency)
    df['Gain/Loss'] = df['Gain/Loss'].apply(format_currency)

    # Style DataFrame
    df_styled = (
        df.style
          .applymap(color_gain, subset=['Gain/Loss'])
          .apply(color_current_value, axis=1)
    )
    st.dataframe(df_styled, height=600)

def main():
    st.sidebar.title("Dashboard Menu")
    selection = st.sidebar.radio("Select Feature", ["Portfolio Tracker", "Dividend Tracker"])

    if selection == "Portfolio Tracker":
        portfolio_tracker()
    elif selection == "Dividend Tracker":
        dividend_tracker()

if __name__ == "__main__":
    main()
    
