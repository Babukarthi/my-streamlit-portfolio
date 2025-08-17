import streamlit as st
import pandas as pd
import yfinance as yf
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


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


def load_portfolio(github_excel_url):
    df = pd.read_excel(github_excel_url)
    required_cols = ['Symbol', 'Quantity Available', 'Average Price']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Missing columns in portfolio Excel: {missing_cols}")
        return None

    portfolio = []
    for _, row in df.iterrows():
        symbol_raw = str(row['Symbol']).strip()
        symbol = symbol_raw if symbol_raw.endswith('.NS') else f"{symbol_raw}.NS"

        shares = pd.to_numeric(row['Quantity Available'], errors='coerce')
        if pd.isna(shares):
            shares = 0
        avg_price = pd.to_numeric(row['Average Price'], errors='coerce')
        if pd.isna(avg_price):
            avg_price = 0

        try:
            ticker = yf.Ticker(symbol)
            prev_close = ticker.info.get('previousClose', 0)
            if prev_close is None:
                prev_close = 0
            prev_close = float(prev_close)
        except:
            prev_close = 0

        invested = decimal_round(Decimal(shares) * Decimal(avg_price))
        current_val = decimal_round(Decimal(shares) * Decimal(prev_close))
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

    return pd.DataFrame(portfolio)


def fetch_dividends(ticker):
    try:
        t = yf.Ticker(ticker)
        divs = t.dividends
        if divs.empty:
            return pd.DataFrame()
        df_divs = divs.reset_index()
        df_divs['Dividend Amount'] = pd.to_numeric(df_divs['Dividends'], errors='coerce').fillna(0)
        df_divs['Dividend Date'] = pd.to_datetime(df_divs['Date'])
        df_divs['Year'] = df_divs['Dividend Date'].dt.year
        df_divs['Month'] = df_divs['Dividend Date'].dt.month
        df_divs['Ticker'] = ticker
        df_divs = df_divs.rename(columns={'Dividends': 'Dividend Amount', 'Date': 'Dividend Date'})
        return df_divs[['Ticker', 'Dividend Date', 'Year', 'Month', 'Dividend Amount']]
    except Exception as e:
        st.warning(f"Error fetching dividends for {ticker}: {e}")
        return pd.DataFrame()


def portfolio_tracker(github_excel_url):
    st.title("🪄 Elegant Portfolio Tracker")
    df_portfolio = load_portfolio(github_excel_url)
    if df_portfolio is None or df_portfolio.empty:
        st.warning("Portfolio data not found or empty.")
        return None

    total_invested = df_portfolio['Invested'].sum()
    total_current = df_portfolio['Current Value'].sum()
    total_gain = df_portfolio['Gain/Loss'].sum()

    gain_color = "#43aa8b" if total_gain >= 0 else "#d1495b"

    st.markdown(f"""
    <div style="text-align:center;">
        <h3>Total Invested: <span style="color: #FFD700;">{format_currency(total_invested)}</span></h3>
        <h3>Current Value: <span style="color: #00BFFF;">{format_currency(total_current)}</span></h3>
        <h3>Net Gain/Loss: <span style="color: {gain_color};">{format_currency(total_gain)}</span></h3>
    </div>
    """, unsafe_allow_html=True)

    display_df = df_portfolio.copy()
    display_df['Shares'] = display_df['Shares'].apply(lambda x: f"{int(x)}")
    for col in ['Avg Price', 'Prev Close', 'Invested', 'Current Value', 'Gain/Loss']:
        display_df[col] = display_df[col].apply(format_currency)

    st.dataframe(display_df[['Company', 'Shares', 'Avg Price', 'Prev Close', 'Invested', 'Current Value', 'Gain/Loss']], height=600)

    return df_portfolio


def dividend_tracker(portfolio_df):
    st.title("📈 Dividend Income Tracker")

    if portfolio_df is None or portfolio_df.empty:
        st.warning("Load portfolio first to view dividend data.")
        return

    years = list(range(2019, datetime.now().year + 1))
    selected_year = st.selectbox("Select Year", years, index=len(years) - 1)

    all_dividends = []
    for ticker in portfolio_df['Ticker']:
        df_div = fetch_dividends(ticker)
        if df_div.empty:
            continue
        df_year = df_div[df_div['Year'] == selected_year].copy()
        if df_year.empty:
            continue

        df_year['Dividend Amount'] = pd.to_numeric(df_year['Dividend Amount'], errors='coerce').fillna(0)
        shares = portfolio_df.loc[portfolio_df['Ticker'] == ticker, 'Shares'].values[0]
        shares = float(shares)

        df_year['Dividend Received'] = df_year['Dividend Amount'] * shares
        all_dividends.append(df_year)

    if not all_dividends:
        st.info(f"No dividend data found for year {selected_year}.")
        return

    dividends_df = pd.concat(all_dividends)
    dividends_df['Dividend Amount'] = dividends_df['Dividend Amount'].apply(format_currency)
    dividends_df['Dividend Received'] = dividends_df['Dividend Received'].apply(format_currency)

    st.subheader(f"Dividend Details for {selected_year}")
    st.dataframe(dividends_df[['Ticker', 'Dividend Date', 'Dividend Amount', 'Dividend Received']])

    monthly_summary = dividends_df.groupby('Month')['Dividend Received'].apply(
        lambda vals: sum(float(s.replace('₹', '').replace(',', '')) for s in vals)).reset_index()
    monthly_summary['Month'] = monthly_summary['Month'].apply(lambda m: datetime(2000, m, 1).strftime('%B'))

    st.subheader(f"Monthly Dividend Income Summary for {selected_year}")
    st.dataframe(monthly_summary)

    total_div = monthly_summary['Dividend Received'].sum()
    st.markdown(f"### Total Dividends Received in {selected_year}: {format_currency(total_div)}")


def main():
    st.sidebar.title("Dashboard Menu")
    choice = st.sidebar.radio("Select Module", ["Portfolio Tracker", "Dividend Tracker"])

    github_excel_url = "https://raw.githubusercontent.com/Babukarthi/my-streamlit-portfolio/main/holdings-GNU044.xlsx"

    if choice == "Portfolio Tracker":
        portfolio_df = portfolio_tracker(github_excel_url)
        st.session_state['portfolio_df'] = portfolio_df
    elif choice == "Dividend Tracker":
        portfolio_df = st.session_state.get('portfolio_df')
        if portfolio_df is None:
            st.warning("Please load your portfolio first in Portfolio Tracker.")
        else:
            dividend_tracker(portfolio_df)


if __name__ == "__main__":
    main()
        
