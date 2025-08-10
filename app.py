import streamlit as st
from polygon import RESTClient
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta

st.title("Polygon.io Candlestick Chart with Supertrend and Jump to Date")

# Input fields
API_KEY = st.text_input("Enter Polygon API Key", type="password")
ticker = st.text_input("Enter Stock Symbol", "AAPL")
from_date = st.date_input("From Date", value=datetime(2023, 1, 1))
to_date = st.date_input("To Date", value=datetime(2023, 1, 7))
jump_date = st.date_input("Jump to Date", value=from_date, min_value=from_date, max_value=to_date)
window_days = st.slider("Days to Display Around Jump Date", 1, 5, 2)

# Supertrend calculation function
def calculate_supertrend(df, period=10, multiplier=3):
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        )
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['upper_band'] = (df['high'] + df['low']) / 2 + multiplier * df['atr']
    df['lower_band'] = (df['high'] + df['low']) / 2 - multiplier * df['atr']
    df['supertrend'] = np.nan
    df['trend'] = 0
    for i in range(period, len(df)):
        prev_supertrend = df['supertrend'].iloc[i-1] if i > 0 else df['close'].iloc[i]
        if df['close'].iloc[i] > prev_supertrend:
            df.loc[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
            df.loc[df.index[i], 'trend'] = 1
        else:
            df.loc[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
            df.loc[df.index[i], 'trend'] = -1
        if df['trend'].iloc[i] == 1 and df['lower_band'].iloc[i] < df['supertrend'].iloc[i-1]:
            df.loc[df.index[i], 'supertrend'] = df['supertrend'].iloc[i-1]
        elif df['trend'].iloc[i] == -1 and df['upper_band'].iloc[i] > df['supertrend'].iloc[i-1]:
            df.loc[df.index[i], 'supertrend'] = df['supertrend'].iloc[i-1]
    return df

# Fetch data button
if st.button("Fetch Data and Plot"):
    if not API_KEY or not ticker:
        st.error("Please provide API key and stock symbol.")
    else:
        client = RESTClient(api_key=API_KEY)
        try:
            aggs = client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="minute",
                from_=from_date.strftime("%Y-%m-%d"),
                to=to_date.strftime("%Y-%m-%d"),
                limit=50000
            )
            df = pd.DataFrame(aggs)
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df[["date", "open", "high", "low", "close", "volume"]]
            df = calculate_supertrend(df)
            jump_datetime = pd.to_datetime(jump_date)
            window = timedelta(days=window_days)
            df_filtered = df[(df['date'] >= jump_datetime - window) & (df['date'] <= jump_datetime + window)]
            if df_filtered.empty:
                st.error("No data available for the selected date range.")
            else:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, subplot_titles=(f"{ticker} Candlestick", "Volume"),
                                    row_heights=[0.7, 0.3])
                fig.add_trace(
                    go.Candlestick(x=df_filtered['date'], open=df_filtered['open'], 
                                  high=df_filtered['high'], low=df_filtered['low'], 
                                  close=df_filtered['close'], name="OHLC"),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=df_filtered['date'], y=df_filtered['supertrend'], 
                              mode='lines', name='Supertrend', line=dict(color='purple', width=2)),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Bar(x=df_filtered['date'], y=df_filtered['volume'], 
                          name='Volume', marker_color='rgba(0, 150, 255, 0.5)'),
                    row=2, col=1
                )
                fig.update_layout(
                    title=f"{ticker} 1-Minute Candlestick Chart (Centered on {jump_date})",
                    xaxis_title="Date",
                    yaxis_title="Price",
                    xaxis_rangeslider_visible=False,
                    showlegend=True,
                    height=800
                )
                fig.update_xaxes(range=[jump_datetime - window, jump_datetime + window])
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
