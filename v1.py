import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD

st.set_page_config(layout="wide")

st.title("TSLA Institutional Short-Term Prediction System")

# ---------------------------
# 获取数据
# ---------------------------
@st.cache_data
def load_data():
    df = yf.download("TSLA", period="5d", interval="5m")
    return df

df = load_data()

# ---------------------------
# 技术指标
# ---------------------------
df["RSI"] = RSIIndicator(df["Close"], window=14).rsi()

macd = MACD(df["Close"])
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()

# ---------------------------
# 成交密集区 (Volume Profile)
# ---------------------------
def volume_profile(data, bins=30):
    
    price = data["Close"]
    volume = data["Volume"]
    
    hist, edges = np.histogram(price, bins=bins, weights=volume)
    
    vp = pd.DataFrame({
        "price": edges[:-1],
        "volume": hist
    })
    
    return vp

vp = volume_profile(df)

poc = vp.loc[vp["volume"].idxmax(), "price"]

# ---------------------------
# 市场环境
# ---------------------------
spy = yf.download("SPY", period="2d", interval="5m")
vix = yf.download("^VIX", period="2d", interval="5m")

spy_change = (spy["Close"].iloc[-1] - spy["Close"].iloc[-10]) / spy["Close"].iloc[-10]
vix_level = vix["Close"].iloc[-1]

# ---------------------------
# 情绪评分
# ---------------------------
sentiment = 0

if spy_change > 0:
    sentiment += 1
else:
    sentiment -= 1

if vix_level < 18:
    sentiment += 1
else:
    sentiment -= 1

rsi = df["RSI"].iloc[-1]

if rsi < 35:
    sentiment += 1

# ---------------------------
# 预测模型
# ---------------------------
price = df["Close"].iloc[-1]

expected_move = price * 0.025

low = price - expected_move
high = price + expected_move

# ---------------------------
# 图表
# ---------------------------
fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )
)

fig.add_hline(y=poc, line_dash="dash")

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# 输出
# ---------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Current Price", round(price,2))
col2.metric("POC (筹码中心)", round(poc,2))
col3.metric("RSI", round(rsi,2))

st.subheader("Predicted Range")

st.write(f"Low: {round(low,2)}")
st.write(f"High: {round(high,2)}")

st.subheader("Market Sentiment Score")

st.write(sentiment)
