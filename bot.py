import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

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
# VALID DOJI
# ============================================================

def is_valid_doji(candle):

    body = abs(candle['Close'] - candle['Open'])

    candle_range = candle['High'] - candle['Low']

    if candle_range == 0:
        return False

    body_percent = (body / candle_range) * 100

    # ORIGINAL STRATEGY LOGIC

    if body <= 2:
        return True

    if body_percent <= 12:
        return True

    return False

# ============================================================
# STRATEGY CHECK
# ============================================================

def check_strategy(df, tf_name):

    df['EMA200'] = df['Close'].ewm(span=EMA_PERIOD).mean()

    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)

    if len(df) < 5:
        return

    doji = df.iloc[-3]

    current = df.iloc[-1]

    doji_found = False

    # ========================================================
    # VALID DOJI ?
    # ========================================================

    if is_valid_doji(doji):

        # ====================================================
        # LONG DOJI
        # ====================================================

        if doji['Close'] > doji['EMA200'] and doji['RSI'] > 60:

            doji_found = True

            msg = f"""
⚠️ VALID LONG DOJI FORMED

Symbol: NIFTY

Timeframe: {tf_name}

Doji High: {round(doji['High'],2)}

Doji Low: {round(doji['Low'],2)}

RSI: {round(doji['RSI'],2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

            send_telegram_message(msg)

            # ENTRY CONFIRMATION

            if current['Close'] > doji['High']:

                entry_msg = f"""
🚨 LONG ENTRY CONFIRMED

Symbol: NIFTY

Timeframe: {tf_name}

Breakout Above: {round(doji['High'],2)}

Current Price: {round(current['Close'],2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

                send_telegram_message(entry_msg)

        # ====================================================
        # SHORT DOJI
        # ====================================================

        elif doji['Close'] < doji['EMA200'] and doji['RSI'] < 40:

            doji_found = True

            msg = f"""
⚠️ VALID SHORT DOJI FORMED

Symbol: NIFTY

Timeframe: {tf_name}

Doji High: {round(doji['High'],2)}

Doji Low: {round(doji['Low'],2)}

RSI: {round(doji['RSI'],2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

            send_telegram_message(msg)

            # ENTRY CONFIRMATION

            if current['Close'] < doji['Low']:

                entry_msg = f"""
🚨 SHORT ENTRY CONFIRMED

Symbol: NIFTY

Timeframe: {tf_name}

Breakdown Below: {round(doji['Low'],2)}

Current Price: {round(current['Close'],2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

                send_telegram_message(entry_msg)

    # ========================================================
    # NO DOJI FOUND
    # ========================================================

    if not doji_found:

        no_msg = f"""
✅ Scan Completed

Timeframe: {tf_name}

No valid strategy doji found.

Time: {datetime.now().strftime('%H:%M:%S')}
"""

        send_telegram_message(no_msg)

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

            check_strategy(df, label)

        except Exception as e:

            error_msg = f"""
ERROR FOUND

Timeframe: {label}

Error:
{e}
"""

            send_telegram_message(error_msg)

            print(e)
