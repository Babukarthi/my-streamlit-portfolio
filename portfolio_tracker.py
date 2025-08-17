import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

API_KEY = "YOUR_ALPHA_VANTAGE_API_KEY"  # Replace with your key

# ----------- Utility Functions -----------
def to_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def decimal_round(value, places=2):
    quantize_str = '1.' + '0' * places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

# ----------- Read portfolio from Excel -----------
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
        shares = to_decimal(row.get('Quantity Available', 0))
        buy_price = to_decimal(row.get('Average Price', 0))
        prev_close = to_decimal(row.get('Previous Closing Price', 0))
        invested_amount = decimal_round(shares * buy_price)
        current_value = decimal_round(shares * prev_close)
        gain_loss = decimal_round(current_value - invested_amount)

        portfolio.append({
            "Ticker": ticker,
            "Company": ticker_raw,
            "Shares": shares,
            "Buy Price": buy_price,
            "Previous Close Price": prev_close,
            "Invested Amount": invested_amount,
            "Current Value": current_value,
            "Gain/Loss": gain_loss,
        })
    return portfolio

# ----------- Fetch Dividends from Alpha Vantage -----------
def fetch_dividends_alpha_vantage(ticker, year):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "apikey": API_KEY,
        "outputsize": "full",
        "datatype": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        time_series = data.get("Time Series (Daily)", {})
        dividends = defaultdict(float)
        for date_str, daily_data in time_series.items():
            date = pd.to_datetime(date_str)
            if date.year == int(year):
                div = float(daily_data.get("7. dividend amount", 0))
                if div > 0:
                    dividends[date.month] += div
        return dividends
    except Exception as e:
        st.error(f"Error fetching dividend data for {ticker}: {e}")
        return defaultdict(float)

# ----------- Formatting Helpers -----------
def format_currency(val):
    return f"₹{val:,.2f}"

# ----------- Dividend Tracker Module -----------
def dividend_tracker_module(portfolio):
    st.title("📈 Dividend Income Tracker")

    year = st.selectbox("Select Year", options=[str(y) for y in range(2000, 2100)], index=25)

    monthly_dividends = defaultdict(Decimal)
    for item in portfolio:
        ticker = item["Ticker"]
        shares = item["Shares"]
        dividends = fetch_dividends_alpha_vantage(ticker, year)
        for month, div_amount in dividends.items():
            monthly_dividends[month] += shares * Decimal(str(div_amount))

    if not monthly_dividends:
        st.info(f"No dividend data found for year {year}.")
        return

    df_dividends = pd.DataFrame([
        {
            "Month": pd.Timestamp(year=int(year), month=m, day=1).strftime("%B"),
            "Dividend Received (₹)": float(monthly_dividends[m]) 
        }
        for m in range(1, 13)
    ])

    total_div = sum(monthly_dividends.values())

    st.subheader(f"Dividend Income for {year}")
    st.dataframe(df_dividends)
    st.markdown(f"### Total Dividend Received in {year}: {format_currency(total_div)}")

# ----------- Portfolio Tracker Module -----------
def portfolio_tracker_module():
    st.title("🪄 Elegant Premium Portfolio Tracker")

    github_excel_url = "https://raw.githubusercontent.com/Babukarthi/my-streamlit-portfolio/main/holdings-GNU044.xlsx"
    portfolio = read_portfolio_from_excel(github_excel_url)

    if not portfolio:
        st.warning("No portfolio data found or Excel file missing.")
        return None

    total_invested = sum(item["Invested Amount"] for item in portfolio)
    total_current = sum(item["Current Value"] for item in portfolio)
    total_gain = sum(item["Gain/Loss"] for item in portfolio)

    gain_color = "#43aa8b" if total_gain >= 0 else "#d1495b"

    st.markdown(f"""
    <div style="background: rgba(21, 25, 45, 0.8); border-radius: 16px; box-shadow: 0 6px 22px rgba(0,0,0,0.4); padding: 1.4rem 2rem; margin-bottom: 1.4rem; backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255,255,255,0.08);">
      <div style="font-size: 1.05rem; color: #e0e0e0; margin-bottom: 0.5em; font-weight: 500; letter-spacing: 1px;">Total Invested</div>
      <div style="font-size: 2.4rem; font-weight: 700; margin: 0.6em 0; color: #FFD700;">{format_currency(total_invested)}</div>
    </div>
    <div style="background: rgba(21, 25, 45, 0.8); border-radius: 16px; box-shadow: 0 6px 22px rgba(0,0,0,0.4); padding: 1.4rem 2rem; margin-bottom: 1.4rem; backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255,255,255,0.08);">
      <div style="font-size: 1.05rem; color: #e0e0e0; margin-bottom: 0.5em; font-weight: 500; letter-spacing: 1px;">Current Value</div>
      <div style="font-size: 2.4rem; font-weight: 700; margin: 0.6em 0; color: #00BFFF;">{format_currency(total_current)}</div>
    </div>
    <div style="background: rgba(21, 25, 45, 0.8); border-radius: 16px; box-shadow: 0 6px 22px rgba(0,0,0,0.4); padding: 1.4rem 2rem; margin-bottom: 1.4rem; backdrop-filter: blur(12px); text-align: center; border: 1px solid rgba(255,255,255,0.08);">
      <div style="font-size: 1.05rem; color: #e0e0e0; margin-bottom: 0.5em; font-weight: 500; letter-spacing: 1px;">Net Gain/Loss</div>
      <div style="font-size: 2.4rem; font-weight: 700; margin: 0.6em 0; color: {gain_color};">{format_currency(total_gain)}</div>
    </div>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(portfolio)

    df = df.drop(columns=["Ticker"])
    df['Shares'] = df['Shares'].apply(lambda x: f"{int(x)}" if isinstance(x, Decimal) else x)
    df['Buy Price'] = df['Buy Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Previous Close Price'] = df['Previous Close Price'].apply(lambda x: format_currency(x) if isinstance(x, Decimal) else x)
    df['Invested Amount'] = df['Invested Amount'].apply(format_currency)
    df['Current Value'] = df['Current Value'].apply(format_currency)
    df['Gain/Loss'] = df['Gain/Loss'].apply(format_currency)

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

    df_styled = (
        df.style
          .applymap(color_gain, subset=['Gain/Loss'])
          .apply(color_current_value, axis=1)
    )
    st.dataframe(df_styled, height=600)

    return portfolio  # returning portfolio for dividend module

# ----------- Main app with sidebar -----------
def main():
    st.sidebar.title("Dashboard Menu")
    menu = st.sidebar.radio("Select Module", ["Portfolio Tracker", "Dividend Tracker"])

    if menu == "Portfolio Tracker":
        portfolio = portfolio_tracker_module()
        st.session_state["portfolio"] = portfolio if portfolio else []
    elif menu == "Dividend Tracker":
        # Use portfolio from session state for dividend module
        portfolio = st.session_state.get("portfolio", [])
        if not portfolio:
            st.warning("Please run Portfolio Tracker first to load holdings.")
            return
        dividend_tracker_module(portfolio)

if __name__ == "__main__":
    main()
    
