import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 設定網頁標題
st.set_page_config(page_title="全球總經與市場數據儀表板", layout="wide")
st.title("📈 全球總經與市場數據儀表板")

end_date = datetime.date.today()

# --- 1. 抓取 Yahoo Finance 數據 ---
st.header("市場即時報價與歷史走勢")
col1, col2, col3 = st.columns(3)

@st.cache_data
def get_market_data(ticker):
    # 改用 Ticker().history()，在雲端環境比 download() 穩定很多
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1y") # 直接抓過去一年的資料
        return data
    except:
        return pd.DataFrame() # 如果抓不到，回傳空表格避免當機

gold_data = get_market_data("GC=F")
oil_data = get_market_data("CL=F")
bond_data = get_market_data("^TNX") # 10年期公債殖利率

# 建立一個安全讀取最新價格的函數 (防呆機制)
def get_latest_price(data):
    if not data.empty and 'Close' in data.columns:
        return f"{data['Close'].iloc[-1]:.2f}"
    return "N/A"

with col1:
    st.metric(label="黃金期貨 (GC=F)", value=get_latest_price(gold_data))
with col2:
    st.metric(label="WTI 原油期貨 (CL=F)", value=get_latest_price(oil_data))
with col3:
    bond_yield = get_latest_price(bond_data)
    st.metric(label="美10年期公債殖利率 (^TNX)", value=f"{bond_yield}%" if bond_yield != "N/A" else "N/A")

st.subheader("黃金期貨走勢圖")
# 只有在資料不是空的時候才畫圖
if not gold_data.empty:
    fig_gold = go.Figure(data=[go.Scatter(x=gold_data.index, y=gold_data['Close'], mode='lines')])
    st.plotly_chart(fig_gold, use_container_width=True)
else:
    st.warning("⚠️ 目前無法從 Yahoo Finance 取得黃金歷史資料，請稍後再試。")


# --- 2. 抓取 FRED 總經數據 ---
st.header("總體經濟指標")

@st.cache_data
def get_macro_data(ticker):
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={ticker}"
        data = pd.read_csv(url, index_col='DATE', parse_dates=True)
        start_macro = end_date - datetime.timedelta(days=365*5)
        data = data[data.index >= pd.to_datetime(start_macro)]
        data[ticker] = pd.to_numeric(data[ticker], errors='coerce')
        return data
    except:
        return pd.DataFrame()

cpi_data = get_macro_data('CPIAUCSL')

st.subheader("美國消費者物價指數 (CPI) - 過去五年")
if not cpi_data.empty:
    fig_cpi = go.Figure(data=[go.Scatter(x=cpi_data.index, y=cpi_data['CPIAUCSL'], mode='lines', line=dict(color='orange'))])
    st.plotly_chart(fig_cpi, use_container_width=True)
else:
    st.warning("⚠️ 無法取得 CPI 資料。")
