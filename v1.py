import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(layout="wide")

st.title("TSLA Institutional Prediction System")

# -----------------------------
# 数据下载
# -----------------------------
@st.cache_data(ttl=300)
def load_data():

    df = yf.download(
        "TSLA",
        period="5d",
        interval="15m",
        progress=False
    )

    if df is None or df.empty:
        return None

    df = df.dropna()

    return df


df = load_data()

if df is None:
    st.error("Market data unavailable. Please refresh later.")
    st.stop()

# -----------------------------
# 修复 dataframe 结构
# -----------------------------
df["Close"] = df["Close"].astype(float)
df["Volume"] = df["Volume"].astype(float)

price_series = df["Close"].squeeze()
volume_series = df["Volume"].squeeze()

# -----------------------------
# 技术指标
# -----------------------------
try:
    df["RSI"] = RSIIndicator(price_series, window=14).rsi()

    macd = MACD(price_series)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

except:
    df["RSI"] = np.nan
    df["MACD"] = np.nan
    df["MACD_signal"] = np.nan


# -----------------------------
# Volume Profile
# -----------------------------
def volume_profile(data, bins=30):

    price = data["Close"].squeeze()
    volume = data["Volume"].squeeze()

    if len(price) == 0:
        return pd.DataFrame({"price": [], "volume": []})

    hist, edges = np.histogram(
        price,
        bins=bins,
        weights=volume
    )

    vp = pd.DataFrame({
        "price": edges[:-1],
        "volume": hist
    })

    return vp


vp = volume_profile(df)

if not vp.empty:
    poc = vp.loc[vp["volume"].idxmax(), "price"]
else:
    poc = price_series.iloc[-1]


# -----------------------------
# 市场环境
# -----------------------------
@st.cache_data(ttl=300)
def market_context():

    spy = yf.download("SPY", period="2d", interval="30m", progress=False)
    vix = yf.download("^VIX", period="2d", interval="30m", progress=False)

    if spy.empty or vix.empty:
        return 0, 20

    spy_change = (
        spy["Close"].iloc[-1] - spy["Close"].iloc[-5]
    ) / spy["Close"].iloc[-5]

    vix_level = vix["Close"].iloc[-1]

    return spy_change, vix_level


spy_change, vix_level = market_context()

# -----------------------------
# 情绪评分
# -----------------------------
sentiment = 0

if spy_change > 0:
    sentiment += 1
else:
    sentiment -= 1

if vix_level < 18:
    sentiment += 1
else:
    sentiment -= 1

rsi_value = df["RSI"].iloc[-1]

if pd.notna(rsi_value) and rsi_value < 35:
    sentiment += 1

# -----------------------------
# 预测模型
# -----------------------------
current_price = price_series.iloc[-1]

expected_move = current_price * 0.025

pred_low = current_price - expected_move
pred_high = current_price + expected_move

# -----------------------------
# K线图
# -----------------------------
fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="TSLA"
    )
)

fig.add_hline(
    y=poc,
    line_dash="dash",
    annotation_text="POC"
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 指标面板
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Price",
    round(current_price, 2)
)

col2.metric(
    "POC",
    round(poc, 2)
)

col3.metric(
    "RSI",
    round(rsi_value, 2) if pd.notna(rsi_value) else "NA"
)

col4.metric(
    "VIX",
    round(vix_level, 2)
)

# -----------------------------
# 预测区间
# -----------------------------
st.subheader("Predicted Daily Range")

c1, c2 = st.columns(2)

c1.metric(
    "Predicted Low",
    round(pred_low, 2)
)

c2.metric(
    "Predicted High",
    round(pred_high, 2)
)

# -----------------------------
# 市场情绪
# -----------------------------
st.subheader("Market Sentiment Score")

if sentiment > 1:
    st.success(f"Bullish ({sentiment})")

elif sentiment == 1:
    st.info(f"Slightly Bullish ({sentiment})")

elif sentiment == 0:
    st.warning("Neutral")

else:
    st.error(f"Bearish ({sentiment})")

# -----------------------------
# Volume Profile 图
# -----------------------------
st.subheader("Volume Profile")

if not vp.empty:

    vp_fig = go.Figure()

    vp_fig.add_bar(
        x=vp["volume"],
        y=vp["price"],
        orientation="h"
    )

    st.plotly_chart(vp_fig, use_container_width=True)

else:
    st.write("Volume profile unavailable")
