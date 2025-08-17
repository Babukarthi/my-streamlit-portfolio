import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

# Utility functions
def to_decimal(value):
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')

def decimal_round(value, places=2):
    quantize_str = '1.' + '0' * places
    return value.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

def format_currency(val):
    try:
        val = float(val)
        return f"₹{val:,.2f}"
    except:
        return val

# Load portfolio from Excel on GitHub
def load_portfolio_from_excel(url):
    df = pd.read_excel(url)
    required_cols = ['Symbol', 'Quantity Available', 'Average Price']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing column '{col}' in portfolio Excel")
            return None
    
    portfolio = []
    for _, row in df.iterrows():
        symbol_raw = str(row['Symbol']).strip()
        symbol = symbol_raw if symbol_raw.endswith('.NS') else symbol_raw + '.NS'
        shares = to_decimal(row['Quantity Available'])
        avg_price = to_decimal(row['Average Price'])

        # Fetch previous close price live from yfinance
        try:
            ticker = yf.Ticker(symbol)
            prev_close = to_decimal(ticker.info.get('previousClose', 0))
        except Exception as e:
            prev_close = Decimal('0')

        invested = decimal_round(shares * avg_price)
        current_val = decimal_round(shares * prev_close)
        gain_loss = decimal_round(current_val - invested)

        portfolio.append({
            'Ticker': symbol,
            'Company': symbol_raw,
            'Shares': shares,
            'Avg Price': avg_price,
            'Prev Close': prev_close,
            'Invested': invested,
            'Current Value': current_val,
            'Gain/Loss': gain_loss,
        })
    return portfolio

# Fetch dividends using yfinance for a ticker
def fetch_dividends(ticker):
    try:
        t = yf.Ticker(ticker)
        div = t.dividends
        if div.empty:
            return pd.DataFrame()
        df_div = div.reset_index()
        df_div['Ticker'] = ticker
        df_div.rename(columns={'Date': 'Dividend Date', 'Dividends':'Dividend Amount'}, inplace=True)
        df_div['Year'] = df_div['Dividend Date'].dt.year
        df_div['Month'] = df_div['Dividend Date'].dt.month
        return df_div
    except:
        return pd.DataFrame()

# Main: Portfolio tracker UI
def portfolio_tracker(github_excel_url):
    st.title("🪄 Elegant Portfolio Tracker")

    portfolio = load_portfolio_from_excel(github_excel_url)
    if not portfolio:
        st.warning("No portfolio data or missing columns.")
        return None

    df_portfolio = pd.DataFrame(portfolio)
    total_invested = df_portfolio['Invested'].sum()
    total_current = df_portfolio['Current Value'].sum()
    total_gain = df_portfolio['Gain/Loss'].sum()

    gain_color = "#43aa8b" if total_gain >= 0 else "#d1495b"

    st.markdown(f"""
    <div style="text-align: center; padding: 10px;">
      <h3>Total Invested: <span style="color: #FFD700;">{format_currency(total_invested)}</span></h3>
      <h3>Current Value: <span style="color: #00BFFF;">{format_currency(total_current)}</span></h3>
      <h3>Net Gain/Loss: <span style="color: {gain_color};">{format_currency(total_gain)}</span></h3>
    </div>
    """, unsafe_allow_html=True)

    # Format columns for display
    display_df = df_portfolio.copy()
    for col in ['Shares']:
        display_df[col] = display_df[col].apply(lambda x: f"{int(x)}")
    for col in ['Avg Price','Prev Close','Invested','Current Value','Gain/Loss']:
        display_df[col] = display_df[col].apply(format_currency)

    st.dataframe(display_df[['Company', 'Shares', 'Avg Price', 'Prev Close', 'Invested', 'Current Value', 'Gain/Loss']], height=600)
    return df_portfolio

# Dividend tracker UI
def dividend_tracker(portfolio_df):
    st.title("📈 Dividend Income Tracker")

    if portfolio_df is None or portfolio_df.empty:
        st.warning("Please load portfolio data first.")
        return

    years = sorted(set(portfolio_df.index.year if hasattr(portfolio_df.index, 'year') else [datetime.now().year]))
    years = list(range(2019, datetime.now().year + 1))  # last 5 years default

    selected_year = st.selectbox("Select Year", years, index=len(years)-1)

    # Fetch dividends for all tickers
    all_dividends = []
    for ticker in portfolio_df['Ticker']:
        st.text(f"Fetching dividends for {ticker}...")
        df_div = fetch_dividends(ticker)
        if not df_div.empty:
            df_div_year = df_div[df_div['Year'] == selected_year]
            # Multiply dividends by shares for income
            shares = portfolio_df.loc[portfolio_df['Ticker'] == ticker, 'Shares'].values[0]
            df_div_year['Dividend Received'] = df_div_year['Dividend Amount'] * shares
            all_dividends.append(df_div_year)

    if not all_dividends:
        st.info(f"No dividend data found for year {selected_year}.")
        return

    dividends_df = pd.concat(all_dividends)
    dividends_df = dividends_df[['Ticker','Dividend Date','Dividend Amount', 'Dividend Received']].sort_values('Dividend Date')
    dividends_df['Dividend Amount'] = dividends_df['Dividend Amount'].apply(format_currency)
    dividends_df['Dividend Received'] = dividends_df['Dividend Received'].apply(format_currency)

    st.subheader(f"Dividend Details for {selected_year}")
    st.dataframe(dividends_df)

    # Monthly summary
    monthly_summary = dividends_df.groupby(dividends_df['Dividend Date'].dt.month)['Dividend Received'].apply(
        lambda x: sum(float(s.replace('₹','').replace(',','')) for s in x)).reset_index()
    monthly_summary.columns = ['Month', 'Dividend Received (₹)']
    monthly_summary['Month'] = monthly_summary['Month'].apply(lambda x: datetime(2000, x, 1).strftime('%B'))

    st.subheader(f"Monthly Dividend Income Summary for {selected_year}")
    st.dataframe(monthly_summary)

    total_dividends = monthly_summary['Dividend Received (₹)'].sum()
    st.markdown(f"### Total Dividend Received in {selected_year}: ₹{total_dividends:,.2f}")

# Main function
def main():
    st.sidebar.title("Dashboard Menu")
    choice = st.sidebar.radio("Select Module", ["Portfolio Tracker", "Dividend Tracker"])
    
    github_excel_url = "https://raw.githubusercontent.com/Babukarthi/my-streamlit-portfolio/main/holdings-GNU044.xlsx"
    portfolio_df = None
    
    if choice == "Portfolio Tracker":
        portfolio_df = portfolio_tracker(github_excel_url)
        st.session_state['portfolio_df'] = portfolio_df
    elif choice == "Dividend Tracker":
        portfolio_df = st.session_state.get('portfolio_df')
        if portfolio_df is None:
            st.warning("Please load portfolio first from Portfolio Tracker.")
        else:
            dividend_tracker(portfolio_df)

if __name__ == "__main__":
    main()
    
