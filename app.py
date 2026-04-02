import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fredapi import Fred # 導入 FRED 官方 API 套件

st.set_page_config(page_title="全球總經與市場數據儀表板", layout="wide")
st.title("📈 總經與市場研究室")

# 讀取藏在 Streamlit Secrets 裡的 API Key
# 這樣就算程式碼公開在 GitHub，別人也偷不走你的密碼
try:
    fred = Fred(api_key=st.secrets["FRED_API_KEY"])
except Exception as e:
    st.error("找不到 FRED API Key！請確認是否已在 Streamlit Secrets 中設定。")

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
tab1, tab2 = st.tabs([" 金融市場動態 ", " 總體經濟指標"])

# --- 頁籤 1: 市場動態 (這部分與上次相同) ---
with tab1:
    st.header("選擇市場資產與技術指標")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_asset = st.selectbox("選擇標的：", list(market_tickers.keys()))
        ticker_symbol = market_tickers[selected_asset]
    with col2:
        show_ma = st.checkbox("顯示 20MA & 60MA", value=True)
    with col3:
        show_bb = st.checkbox("顯示布林通道 (BBands)", value=False)
    with col4:
        show_vol = st.checkbox("顯示成交量 (Volume)", value=True)
    
    @st.cache_data
    def get_market_data(ticker):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y") 
            data = data.dropna() 
            return data
        except:
            return pd.DataFrame()

    market_data = get_market_data(ticker_symbol)

    if not market_data.empty:
        latest_price = market_data['Close'].iloc[-1]
        st.metric(label=f"{selected_asset} ({ticker_symbol}) 最新收盤價", value=f"{latest_price:.2f}")
        
        market_data['MA20'] = market_data['Close'].rolling(window=20).mean()
        market_data['MA60'] = market_data['Close'].rolling(window=60).mean()
        market_data['BB_mid'] = market_data['Close'].rolling(window=20).mean()
        market_data['BB_std'] = market_data['Close'].rolling(window=20).std()
        market_data['BB_upper'] = market_data['BB_mid'] + 2 * market_data['BB_std']
        market_data['BB_lower'] = market_data['BB_mid'] - 2 * market_data['BB_std']

        if show_vol:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        else:
            fig = go.Figure()

        candlestick = go.Candlestick(
            x=market_data.index,
            open=market_data['Open'], high=market_data['High'],
            low=market_data['Low'], close=market_data['Close'],
            name='K線', increasing_line_color='red', decreasing_line_color='green'
        )
        if show_vol:
            fig.add_trace(candlestick, row=1, col=1)
        else:
            fig.add_trace(candlestick)

        if show_ma:
            ma20 = go.Scatter(x=market_data.index, y=market_data['MA20'], line=dict(color='orange', width=1.5), name='20MA (月線)')
            ma60 = go.Scatter(x=market_data.index, y=market_data['MA60'], line=dict(color='dodgerblue', width=1.5), name='60MA (季線)')
            if show_vol:
                fig.add_trace(ma20, row=1, col=1)
                fig.add_trace(ma60, row=1, col=1)
            else:
                fig.add_trace(ma20)
                fig.add_trace(ma60)

        if show_bb:
            bb_upper = go.Scatter(x=market_data.index, y=market_data['BB_upper'], line=dict(color='gray', dash='dash'), name='BB 上軌')
            bb_lower = go.Scatter(x=market_data.index, y=market_data['BB_lower'], line=dict(color='gray', dash='dash'), name='BB 下軌', fill='tonexty', fillcolor='rgba(128,128,128,0.1)')
            if show_vol:
                fig.add_trace(bb_upper, row=1, col=1)
                fig.add_trace(bb_lower, row=1, col=1)
            else:
                fig.add_trace(bb_upper)
                fig.add_trace(bb_lower)

        if show_vol:
            colors = ['red' if row['Close'] >= row['Open'] else 'green' for index, row in market_data.iterrows()]
            volume_bar = go.Bar(x=market_data.index, y=market_data['Volume'], marker_color=colors, name='成交量')
            fig.add_trace(volume_bar, row=2, col=1)

        fig.update_layout(title=f"{selected_asset} 歷史走勢與技術分析", template="plotly_dark", xaxis_rangeslider_visible=False, height=700 if show_vol else 500, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("無法取得該資產數據。")

# --- 頁籤 2: 總經指標 (改用官方 API) ---
with tab2:
    st.header("選擇總經指標")
    selected_macro = st.selectbox("請選擇要查看的經濟指標：", list(macro_tickers.keys()))
    macro_symbol = macro_tickers[selected_macro]

    @st.cache_data
    def get_macro_data_api(ticker):
        try:
            # 使用官方 API 抓取資料，語法變得超級簡單！
            data = fred.get_series(ticker)
            
            # 轉換成 DataFrame 方便畫圖
            df = pd.DataFrame(data, columns=[ticker])
            
            # 抓取過去 10 年
            start_macro = end_date - datetime.timedelta(days=365*10)
            df = df[df.index >= pd.to_datetime(start_macro)]
            df = df.dropna()
            return df
        except Exception as e:
            st.error(f"透過 API 抓取 {ticker} 時發生錯誤: {e}")
            return pd.DataFrame()
    
    macro_data = get_macro_data_api(macro_symbol)
    
    if not macro_data.empty:
        fig_macro = go.Figure(data=[go.Scatter(x=macro_data.index, y=macro_data[macro_symbol], mode='lines', line=dict(color='orange'))])
        fig_macro.update_layout(title=f"{selected_macro} 過去十年走勢", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_macro, use_container_width=True)
    else:
        st.warning("目前沒有該總經數據。")
