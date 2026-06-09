import os
import requests
import yfinance as yf
import pandas as pd

# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(url, data=payload)

# ============================================================
# SETTINGS
# ============================================================

SYMBOLS = [
    "^NSEI"
]

TIMEFRAMES = [
    ("5m", "5MIN"),
    ("15m", "15MIN"),
    ("30m", "30MIN")
]

EMA_PERIOD = 200
RSI_PERIOD = 14

# ============================================================
# RSI FUNCTION
# ============================================================

def calculate_rsi(data, period=14):

    delta = data['Close'].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# ============================================================
# CHECK STRATEGY
# ============================================================

def check_strategy(df):

    df['EMA200'] = df['Close'].ewm(span=EMA_PERIOD).mean()

    df['RSI'] = calculate_rsi(df, RSI_PERIOD)

    last = df.iloc[-1]

    close_price = last['Close']
    ema200 = last['EMA200']
    rsi = last['RSI']

    # LONG CONDITION
    if close_price > ema200 and rsi > 60:

        return "LONG"

    # SHORT CONDITION
    elif close_price < ema200 and rsi < 40:

        return "SHORT"

    return None

# ============================================================
# MAIN
# ============================================================

for symbol in SYMBOLS:

    for interval, label in TIMEFRAMES:

        try:

            df = yf.download(
                symbol,
                period="7d",
                interval=interval,
                progress=False
            )

            if df.empty:
                continue

            signal = check_strategy(df)

            if signal:

                last_close = round(df['Close'].iloc[-1], 2)

                msg = f"""
🚨 EMA200 RSI ALERT

Symbol: {symbol}

Timeframe: {label}

Signal: {signal}

Price: {last_close}
"""

                send_telegram_message(msg)

                print(msg)

            else:

                print(f"No signal for {symbol} {label}")

        except Exception as e:

            print("ERROR:", e)
