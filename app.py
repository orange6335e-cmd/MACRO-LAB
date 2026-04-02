import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

# 設定網頁標題
st.set_page_config(page_title="全球總經與市場數據儀表板", layout="wide")
st.title("📈 全球總經與市場數據儀表板")

# 設定抓取資料的時間範圍 (過去一年)
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# --- 1. 抓取 Yahoo Finance 數據 ---
st.header("市場即時報價與歷史走勢")
col1, col2, col3 = st.columns(3)

@st.cache_data
def get_market_data(ticker):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data

gold_data = get_market_data("GC=F")
oil_data = get_market_data("CL=F")
bond_data = get_market_data("^TNX") # 10年期公債殖利率

with col1:
    st.metric(label="黃金期貨 (GC=F)", value=f"{gold_data['Close'].iloc[-1].item():.2f}")
with col2:
    st.metric(label="WTI 原油期貨 (CL=F)", value=f"{oil_data['Close'].iloc[-1].item():.2f}")
with col3:
    st.metric(label="美10年期公債殖利率 (^TNX)", value=f"{bond_data['Close'].iloc[-1].item():.2f}%")

st.subheader("黃金期貨走勢圖")
fig_gold = go.Figure(data=[go.Scatter(x=gold_data.index, y=gold_data['Close'].squeeze(), mode='lines')])
st.plotly_chart(fig_gold, use_container_width=True)


# --- 2. 抓取 FRED 總經數據 (直接讀取源頭 CSV) ---
st.header("總體經濟指標")

@st.cache_data
def get_macro_data(ticker):
    # 直接組合 FRED 的 CSV 下載網址
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={ticker}"
    # 讓 pandas 直接去讀取這個網址
    data = pd.read_csv(url, index_col='DATE', parse_dates=True)
    
    # 篩選過去五年的資料
    start_macro = end_date - datetime.timedelta(days=365*5)
    data = data[data.index >= pd.to_datetime(start_macro)]
    
    # 確保資料格式是數字 (避免 FRED 偶爾有 '.' 代表缺失值)
    data[ticker] = pd.to_numeric(data[ticker], errors='coerce')
    return data

cpi_data = get_macro_data('CPIAUCSL')

st.subheader("美國消費者物價指數 (CPI) - 過去五年")
fig_cpi = go.Figure(data=[go.Scatter(x=cpi_data.index, y=cpi_data['CPIAUCSL'], mode='lines', line=dict(color='orange'))])
st.plotly_chart(fig_cpi, use_container_width=True)
