import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="全球總經與市場數據儀表板", layout="wide")
st.title("📈 總經與市場研究室")

end_date = datetime.date.today()

# === 準備標的字典 ===
market_tickers = {
    "S&P 500 指數": "^GSPC",
    "台灣加權指數": "^TWII",
    "VIX 恐慌指數": "^VIX",
    "美元指數": "DX-Y.NYB",
    "黃金期貨": "GC=F",
    "WTI 原油期貨": "CL=F",
    "美10年期公債殖利率": "^TNX"
}

macro_tickers = {
    "消費者物價指數 (CPI)": "CPIAUCSL",
    "核心 PCE 通膨率": "PCEPILFE",
    "失業率": "UNRATE",
    "聯邦基金利率": "FEDFUNDS",
    "10年-2年公債利差 (衰退指標)": "T10Y2Y"
}

# === 建立分頁 ===
tab1, tab2 = st.tabs(["📊 金融市場動態", "🏛️ 總體經濟指標"])

# --- 頁籤 1: 市場動態 ---
with tab1:
    st.header("選擇市場資產")
    # 下拉式選單
    selected_asset = st.selectbox("請選擇要查看的標的：", list(market_tickers.keys()))
    ticker_symbol = market_tickers[selected_asset]
    
    @st.cache_data
    def get_market_data(ticker):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y") # 抓取過去兩年
            data = data.dropna() # 資料清洗：移除空值，確保數據正確性
            return data
        except:
            return pd.DataFrame()

    market_data = get_market_data(ticker_symbol)

    if not market_data.empty:
        # 顯示最新報價
        latest_price = market_data['Close'].iloc[-1]
        st.metric(label=f"{selected_asset} ({ticker_symbol}) 最新報價", value=f"{latest_price:.2f}")
        
        # 畫圖
        fig = go.Figure(data=[go.Scatter(x=market_data.index, y=market_data['Close'], mode='lines', name='收盤價')])
        fig.update_layout(title=f"{selected_asset} 過去兩年走勢", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("無法取得該資產數據。")

# --- 頁籤 2: 總經指標 ---
with tab2:
    st.header("選擇總經指標")
    selected_macro = st.selectbox("請選擇要查看的經濟指標：", list(macro_tickers.keys()))
    macro_symbol = macro_tickers[selected_macro]

    @st.cache_data
    def get_macro_data(ticker):
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={ticker}"
            data = pd.read_csv(url, index_col='DATE', parse_dates=True)
            # 抓取過去 10 年，看長趨勢
            start_macro = end_date - datetime.timedelta(days=365*10)
            data = data[data.index >= pd.to_datetime(start_macro)]
            data[ticker] = pd.to_numeric(data[ticker], errors='coerce')
            data = data.dropna() # 資料清洗
            return data
        except:
            return pd.DataFrame()

    macro_data = get_macro_data(macro_symbol)
    
    if not macro_data.empty:
        fig_macro = go.Figure(data=[go.Scatter(x=macro_data.index, y=macro_data[macro_symbol], mode='lines', line=dict(color='orange'))])
        fig_macro.update_layout(title=f"{selected_macro} 過去十年走勢", template="plotly_dark")
        st.plotly_chart(fig_macro, use_container_width=True)
    else:
        st.warning("無法取得該總經數據。")
