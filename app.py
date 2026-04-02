import streamlit as st
import yfinance as yf
import pandas_datareader.data as web
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

# 抓取資料函數
@st.cache_data # 使用 cache 加快網頁載入速度
def get_market_data(ticker):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data

gold_data = get_market_data("GC=F")
oil_data = get_market_data("CL=F")
bond_data = get_market_data("^TNX") # 10年期公債殖利率

# 顯示最新價格
with col1:
    st.metric(label="黃金期貨 (GC=F)", value=f"{gold_data['Close'].iloc[-1].item():.2f}")
with col2:
    st.metric(label="WTI 原油期貨 (CL=F)", value=f"{oil_data['Close'].iloc[-1].item():.2f}")
with col3:
    st.metric(label="美10年期公債殖利率 (^TNX)", value=f"{bond_data['Close'].iloc[-1].item():.2f}%")

# 畫圖示範 (黃金)
st.subheader("黃金期貨走勢圖")
fig_gold = go.Figure(data=[go.Scatter(x=gold_data.index, y=gold_data['Close'].squeeze(), mode='lines')])
st.plotly_chart(fig_gold, use_container_width=True)


# --- 2. 抓取 FRED 總經數據 ---
st.header("總體經濟指標")

@st.cache_data
def get_macro_data(ticker):
    # 抓取過去五年的數據來觀察趨勢
    start_macro = end_date - datetime.timedelta(days=365*5)
    data = web.DataReader(ticker, 'fred', start_macro, end_date)
    return data

cpi_data = get_macro_data('CPIAUCSL')

st.subheader("美國消費者物價指數 (CPI) - 過去五年")
fig_cpi = go.Figure(data=[go.Scatter(x=cpi_data.index, y=cpi_data['CPIAUCSL'], mode='lines', line=dict(color='orange'))])
st.plotly_chart(fig_cpi, use_container_width=True)