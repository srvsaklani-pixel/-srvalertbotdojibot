import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np

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

TIMEFRAMES = {
    "3m": "3MIN",
    "5m": "5MIN",
    "10m": "10MIN",
    "30m": "30MIN"
}

EMA_PERIOD = 200
RSI_PERIOD = 14

# ============================================================
# RSI
# ============================================================

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# ============================================================
# DOJI CHECK
# ============================================================

def is_valid_doji(candle):

    body = abs(candle['Close'] - candle['Open'])

    candle_range = candle['High'] - candle['Low']

    if candle_range == 0:
        return False

    body_percent = (body / candle_range) * 100

    # EXACT STRATEGY LOGIC
    if body <= 2:
        return True

    if body_percent <= 12:
        return True

    return False

# ============================================================
# STRATEGY CHECK
# ============================================================

def check_strategy(df):

    df['EMA200'] = df['Close'].ewm(span=EMA_PERIOD).mean()

    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)

    if len(df) < 5:
        return

    doji = df.iloc[-3]

    confirm = df.iloc[-2]

    current = df.iloc[-1]

    # ========================================================
    # VALID DOJI ?
    # ========================================================

    if not is_valid_doji(doji):
        return

    # ========================================================
    # LONG DOJI ALERT
    # ========================================================

    if doji['Close'] > doji['EMA200'] and doji['RSI'] > 60:

        msg = f"""
⚠️ VALID LONG DOJI FORMED

Symbol: NIFTY

Timeframe: ACTIVE

Doji High: {round(doji['High'],2)}

Doji Low: {round(doji['Low'],2)}

RSI: {round(doji['RSI'],2)}
"""

        send_telegram_message(msg)

        # ENTRY CONFIRMATION

        if current['Close'] > doji['High']:

            entry_msg = f"""
🚨 LONG ENTRY CONFIRMED

Symbol: NIFTY

Breakout Above: {round(doji['High'],2)}

Current Price: {round(current['Close'],2)}
"""

            send_telegram_message(entry_msg)

    # ========================================================
    # SHORT DOJI ALERT
    # ========================================================

    if doji['Close'] < doji['EMA200'] and doji['RSI'] < 40:

        msg = f"""
⚠️ VALID SHORT DOJI FORMED

Symbol: NIFTY

Timeframe: ACTIVE

Doji High: {round(doji['High'],2)}

Doji Low: {round(doji['Low'],2)}

RSI: {round(doji['RSI'],2)}
"""

        send_telegram_message(msg)

        # ENTRY CONFIRMATION

        if current['Close'] < doji['Low']:

            entry_msg = f"""
🚨 SHORT ENTRY CONFIRMED

Symbol: NIFTY

Breakdown Below: {round(doji['Low'],2)}

Current Price: {round(current['Close'],2)}
"""

            send_telegram_message(entry_msg)

# ============================================================
# MAIN
# ============================================================

for symbol in SYMBOLS:

    for interval, label in TIMEFRAMES.items():

        try:

            print(f"Checking {symbol} {label}")

            df = yf.download(

                symbol,
                period="10d",
                interval=interval,
                progress=False

            )

            if df.empty:

                continue

            check_strategy(df)

        except Exception as e:

            print("ERROR:", e)
