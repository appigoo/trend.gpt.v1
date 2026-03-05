import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(layout="wide")

st.title("TSLA Quant Trading Dashboard")

# -----------------------------
# 下载 TSLA 数据
# -----------------------------
@st.cache_data(ttl=300)
def load_tsla():

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


df = load_tsla()

if df is None:
    st.error("TSLA market data unavailable")
    st.stop()


# -----------------------------
# 确保 Series 结构
# -----------------------------
close = df["Close"].squeeze()
volume = df["Volume"].squeeze()


# -----------------------------
# 技术指标
# -----------------------------
try:

    df["RSI"] = RSIIndicator(close, window=14).rsi()

    macd = MACD(close)

    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

except:

    df["RSI"] = np.nan
    df["MACD"] = np.nan
    df["MACD_signal"] = np.nan


# -----------------------------
# Volume Profile
# -----------------------------
def volume_profile(data, bins=40):

    price = data["Close"].squeeze()
    vol = data["Volume"].squeeze()

    if len(price) == 0:
        return pd.DataFrame({"price": [], "volume": []})

    hist, edges = np.histogram(
        price,
        bins=bins,
        weights=vol
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

    poc = float(close.iloc[-1])


# -----------------------------
# 宏观环境
# -----------------------------
@st.cache_data(ttl=300)
def market_context():

    spy = yf.download(
        "SPY",
        period="2d",
        interval="30m",
        progress=False
    )

    vix = yf.download(
        "^VIX",
        period="2d",
        interval="30m",
        progress=False
    )

    if spy is None or spy.empty or vix is None or vix.empty:

        return 0.0, 20.0


    spy_close = spy["Close"].squeeze()
    vix_close = vix["Close"].squeeze()

    spy_change = float(
        (spy_close.iloc[-1] - spy_close.iloc[-5])
        / spy_close.iloc[-5]
    )

    vix_level = float(vix_close.iloc[-1])

    return spy_change, vix_level


spy_change, vix_level = market_context()


# -----------------------------
# 市场情绪评分
# -----------------------------
sentiment = 0

if float(spy_change) > 0:
    sentiment += 1
else:
    sentiment -= 1

if float(vix_level) < 18:
    sentiment += 1
else:
    sentiment -= 1

rsi_value = df["RSI"].iloc[-1]

if pd.notna(rsi_value):

    if rsi_value < 35:
        sentiment += 1

    if rsi_value > 70:
        sentiment -= 1


# -----------------------------
# 预测模型
# -----------------------------
price_now = float(close.iloc[-1])

expected_move = price_now * 0.025

pred_low = price_now - expected_move
pred_high = price_now + expected_move


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
c1, c2, c3, c4 = st.columns(4)

c1.metric("Price", round(price_now,2))
c2.metric("POC", round(poc,2))

if pd.notna(rsi_value):
    c3.metric("RSI", round(rsi_value,2))
else:
    c3.metric("RSI","NA")

c4.metric("VIX", round(vix_level,2))


# -----------------------------
# 预测区间
# -----------------------------
st.subheader("Predicted Daily Range")

l1, l2 = st.columns(2)

l1.metric("Predicted Low", round(pred_low,2))
l2.metric("Predicted High", round(pred_high,2))


# -----------------------------
# 市场情绪
# -----------------------------
st.subheader("Market Sentiment")

if sentiment >= 2:

    st.success(f"Bullish  ({sentiment})")

elif sentiment == 1:

    st.info("Slightly Bullish")

elif sentiment == 0:

    st.warning("Neutral")

else:

    st.error(f"Bearish ({sentiment})")


# -----------------------------
# Volume Profile
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
