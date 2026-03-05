import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(layout="wide")
st.title("TSLA Daily Report")

# -----------------------------
# 1️⃣ 下载 TSLA 数据
# -----------------------------
@st.cache_data(ttl=300)
def load_tsla():
    df = yf.download("TSLA", period="5d", interval="15m", progress=False)
    if df is None or df.empty:
        return None
    return df.dropna()

df = load_tsla()
if df is None:
    st.error("TSLA market data unavailable")
    st.stop()

close = df["Close"].squeeze()
volume = df["Volume"].squeeze()

# -----------------------------
# 2️⃣ 技术指标
# -----------------------------
df["RSI"] = RSIIndicator(close, window=14).rsi()
macd = MACD(close)
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()
ema50 = df["Close"].ewm(span=50).mean().iloc[-1]

# -----------------------------
# 3️⃣ 机构筹码 - Volume Profile
# -----------------------------
def volume_profile(data, bins=40):
    price = data["Close"].squeeze()
    vol = data["Volume"].squeeze()
    if len(price) == 0:
        return pd.DataFrame({"price": [], "volume": []})
    hist, edges = np.histogram(price, bins=bins, weights=vol)
    return pd.DataFrame({"price": edges[:-1], "volume": hist})

vp = volume_profile(df)
poc = vp.loc[vp["volume"].idxmax(), "price"] if not vp.empty else float(close.iloc[-1])

# -----------------------------
# 4️⃣ 宏观环境 / 市场情绪
# -----------------------------
@st.cache_data(ttl=300)
def market_context():
    spy = yf.download("SPY", period="2d", interval="30m", progress=False)
    vix = yf.download("^VIX", period="2d", interval="30m", progress=False)
    if spy.empty or vix.empty:
        return 0.0, 20.0
    spy_close = spy["Close"].squeeze()
    vix_close = vix["Close"].squeeze()
    spy_change = float((spy_close.iloc[-1]-spy_close.iloc[-5])/spy_close.iloc[-5])
    vix_level = float(vix_close.iloc[-1])
    return spy_change, vix_level

spy_change, vix_level = market_context()

# 情绪评分
sentiment = 0
if spy_change > 0: sentiment +=1
else: sentiment -=1
if vix_level < 18: sentiment +=1
else: sentiment -=1
rsi_val = df["RSI"].iloc[-1]
if pd.notna(rsi_val):
    if rsi_val < 35: sentiment +=1
    if rsi_val > 70: sentiment -=1

# -----------------------------
# 5️⃣ Gamma Level (示例)
# -----------------------------
# 真实数据需要调用 Option API，此处用示例值
gamma_call_wall = 438
gamma_put_wall = 410
gamma_flip = 420

# -----------------------------
# 6️⃣ 技术支撑结构图
# -----------------------------
levels = {
    "强阻力": 450,
    "50EMA阻力": round(ema50,2),
    "次阻力": 425,
    "关键支撑": 420,
    "心理支撑": 400,
    "强支撑": 375,
    "长期底": 350
}

# -----------------------------
# 7️⃣ 预测区间
# -----------------------------
price_now = float(close.iloc[-1])
pred_low = price_now * 0.975
pred_high = price_now * 1.025

# -----------------------------
# 8️⃣ K线图 + POC
# -----------------------------
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="TSLA"
))
fig.add_hline(y=poc, line_dash="dash", annotation_text="POC")
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 9️⃣ 指标面板
# -----------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("Price", round(price_now,2))
c2.metric("POC", round(poc,2))
c3.metric("RSI", round(rsi_val,2))
c4.metric("VIX", round(vix_level,2))

st.subheader("Predicted Daily Range")
l1,l2 = st.columns(2)
l1.metric("Low", round(pred_low,2))
l2.metric("High", round(pred_high,2))

st.subheader("Market Sentiment")
if sentiment >= 2: st.success(f"Bullish ({sentiment})")
elif sentiment == 1: st.info(f"Slightly Bullish ({sentiment})")
elif sentiment == 0: st.warning("Neutral")
else: st.error(f"Bearish ({sentiment})")

st.subheader("Gamma Level")
st.write(f"Call Wall: {gamma_call_wall}, Put Wall: {gamma_put_wall}, Gamma Flip: {gamma_flip}")

st.subheader("TSLA 技术结构 (2026 Mar)")
for k,v in levels.items():
    bar = "█" * int((v/50))
    st.write(f"{v} ┤{bar} {k}")

st.subheader("Volume Profile")
if not vp.empty:
    vp_fig = go.Figure()
    vp_fig.add_bar(x=vp["volume"], y=vp["price"], orientation="h")
    st.plotly_chart(vp_fig,use_container_width=True)
else:
    st.write("Volume profile unavailable")
