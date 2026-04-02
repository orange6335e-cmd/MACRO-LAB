import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fredapi import Fred

st.set_page_config(page_title="全球總經與市場數據儀表板", layout="wide")

# 讀取藏在 Streamlit Secrets 裡的 API Key
try:
    fred = Fred(api_key=st.secrets["FRED_API_KEY"])
except Exception as e:
    st.error("找不到 FRED API Key！請確認是否已在 Streamlit Secrets 中設定。")

# ==========================================
# ⚙️ 側邊欄：全域時間範圍控制
# ==========================================
st.sidebar.header("⚙️ 儀表板設定")
years = st.sidebar.slider("選擇歷史資料範圍 (年)", min_value=1, max_value=30, value=5, step=1)

end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365 * years)

st.title("📈 總經與市場研究室")

# === 準備標的字典 ===
market_tickers = {
    "S&P 500 ETF (SPY)": "SPY",
    "台灣 0050 ETF": "0050.TW",
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

# === 建立三個分頁 ===
tab1, tab2, tab3 = st.tabs(["📊 金融市場動態", "🏛️ 總體經濟指標", "⚖️ 雙指標對照分析 (雙Y軸)"])

# --- 頁籤 1: 市場動態 ---
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_asset = st.selectbox("選擇市場標的：", list(market_tickers.keys()))
        ticker_symbol = market_tickers[selected_asset]
    with col2:
        show_ma = st.checkbox("顯示 20MA & 60MA", value=True)
    with col3:
        show_bb = st.checkbox("顯示布林通道", value=False)
    with col4:
        show_vol = st.checkbox("顯示成交量", value=True)
    
    @st.cache_data
    def get_market_data(ticker, start, end):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(start=start, end=end) 
            data = data.dropna() 
            return data
        except:
            return pd.DataFrame()

    market_data = get_market_data(ticker_symbol, start_date, end_date)

    if not market_data.empty:
        st.metric(label=f"{selected_asset} 最新收盤價", value=f"{market_data['Close'].iloc[-1]:.2f}")
        
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
            x=market_data.index, open=market_data['Open'], high=market_data['High'],
            low=market_data['Low'], close=market_data['Close'],
            name='K線', increasing_line_color='red', decreasing_line_color='green'
        )
        fig.add_trace(candlestick, row=1, col=1) if show_vol else fig.add_trace(candlestick)

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

        fig.update_layout(title=f"{selected_asset} (過去 {years} 年)", template="plotly_dark", xaxis_rangeslider_visible=False, height=700 if show_vol else 500, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("無法取得該資產數據。")

# --- 頁籤 2: 總經指標 ---
with tab2:
    selected_macro = st.selectbox("選擇經濟指標：", list(macro_tickers.keys()))
    macro_symbol = macro_tickers[selected_macro]

    @st.cache_data
    def get_macro_data_api(ticker, start, end):
        try:
            data = fred.get_series(ticker)
            df = pd.DataFrame(data, columns=[ticker])
            df = df[(df.index >= pd.to_datetime(start)) & (df.index <= pd.to_datetime(end))]
            df = df.dropna()
            return df
        except Exception as e:
            st.error(f"透過 API 抓取 {ticker} 時發生錯誤: {e}")
            return pd.DataFrame()
    
    macro_data = get_macro_data_api(macro_symbol, start_date, end_date)
    
    if not macro_data.empty:
        fig_macro = go.Figure(data=[go.Scatter(x=macro_data.index, y=macro_data[macro_symbol], mode='lines', line=dict(color='orange'))])
        fig_macro.update_layout(title=f"{selected_macro} (過去 {years} 年)", template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_macro, use_container_width=True)
    else:
        st.warning("目前沒有該總經數據。")

# --- 頁籤 3: 雙指標對照分析 ---
with tab3:
    st.markdown("將任何「市場數據」與「總經指標」疊加，觀察兩者的連動關係。系統已自動啟用**雙 Y 軸**。")
    
    all_metrics = {**market_tickers, **macro_tickers}
    
    colA, colB = st.columns(2)
    with colA:
        metric1_name = st.selectbox("🔴 選擇指標 1 (對應左側 Y 軸)：", list(all_metrics.keys()), index=0)
    with colB:
        metric2_name = st.selectbox("🔵 選擇指標 2 (對應右側 Y 軸)：", list(all_metrics.keys()), index=list(all_metrics.keys()).index("聯邦基金利率"))

    @st.cache_data
    def get_unified_data(name, start, end):
        if name in market_tickers:
            try:
                df = yf.Ticker(market_tickers[name]).history(start=start, end=end)
                df = df[['Close']].rename(columns={'Close': name})
                # 拔除時區資訊，避免合併衝突
                df.index = df.index.tz_localize(None)
                return df
            except: return pd.DataFrame()
        else:
            try:
                data = fred.get_series(macro_tickers[name])
                df = pd.DataFrame(data, columns=[name])
                df = df[(df.index >= pd.to_datetime(start)) & (df.index <= pd.to_datetime(end))]
                # 確保 FRED 數據也沒有時區資訊
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                return df
            except: return pd.DataFrame()

    df1 = get_unified_data(metric1_name, start_date, end_date)
    df2 = get_unified_data(metric2_name, start_date, end_date)

    if not df1.empty and not df2.empty:
        merged_df = df1.join(df2, how='outer').ffill().dropna()

        fig_compare = make_subplots(specs=[[{"secondary_y": True}]])

        fig_compare.add_trace(
            go.Scatter(x=merged_df.index, y=merged_df[metric1_name], name=metric1_name, line=dict(color='tomato')),
            secondary_y=False,
        )
        fig_compare.add_trace(
            go.Scatter(x=merged_df.index, y=merged_df[metric2_name], name=metric2_name, line=dict(color='dodgerblue')),
            secondary_y=True,
        )

        fig_compare.update_layout(
            title_text=f"對照分析：{metric1_name} vs {metric2_name} (過去 {years} 年)",
            template="plotly_dark", hovermode="x unified"
        )
        fig_compare.update_yaxes(title_text=metric1_name, secondary_y=False, color='tomato')
        fig_compare.update_yaxes(title_text=metric2_name, secondary_y=True, color='dodgerblue')

        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.warning("無法取得部分資料，請檢查選擇的指標。")
