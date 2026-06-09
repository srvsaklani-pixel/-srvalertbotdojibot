import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# TELEGRAM SETTINGS
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
# RSI FUNCTION
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
# STRATEGY CHECK
# ============================================================

def check_strategy(df, tf_name):

    # --------------------------------------------------------
    # EMA200
    # --------------------------------------------------------

    df['EMA200'] = df['Close'].ewm(span=EMA_PERIOD).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)

    df = df.dropna().copy()

    if len(df) < 5:
        return

    # --------------------------------------------------------
    # CANDLES
    # --------------------------------------------------------

    doji = df.iloc[-3]

    current = df.iloc[-1]

    # --------------------------------------------------------
    # SAFE FLOAT CONVERSION
    # --------------------------------------------------------

    doji_open = float(doji['Open'])

    doji_close = float(doji['Close'])

    doji_high = float(doji['High'])

    doji_low = float(doji['Low'])

    doji_ema = float(doji['EMA200'])

    doji_rsi = float(doji['RSI'])

    current_close = float(current['Close'])

    # --------------------------------------------------------
    # DOJI LOGIC
    # --------------------------------------------------------

    body = abs(doji_close - doji_open)

    candle_range = doji_high - doji_low

    if candle_range == 0:
        return

    body_percent = (body / candle_range) * 100

    valid_doji = False

    # ORIGINAL STRATEGY RULES

    if body <= 2:
        valid_doji = True

    if body_percent <= 12:
        valid_doji = True

    # --------------------------------------------------------
    # NO DOJI FOUND
    # --------------------------------------------------------

    if not valid_doji:

        no_msg = f"""
✅ Scan Completed

Timeframe: {tf_name}

No valid strategy doji found.

Time: {datetime.now().strftime('%H:%M:%S')}
"""

        send_telegram_message(no_msg)

        return

    # ========================================================
    # LONG SETUP
    # ========================================================

    if doji_close > doji_ema and doji_rsi > 60:

        msg = f"""
⚠️ VALID LONG DOJI FORMED

Symbol: NIFTY

Timeframe: {tf_name}

Doji High: {round(doji_high, 2)}

Doji Low: {round(doji_low, 2)}

RSI: {round(doji_rsi, 2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

        send_telegram_message(msg)

        # ----------------------------------------------------
        # ENTRY CONFIRMATION
        # ----------------------------------------------------

        if current_close > doji_high:

            entry_msg = f"""
🚨 LONG ENTRY CONFIRMED

Symbol: NIFTY

Timeframe: {tf_name}

Breakout Above: {round(doji_high, 2)}

Current Price: {round(current_close, 2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

            send_telegram_message(entry_msg)

        return

    # ========================================================
    # SHORT SETUP
    # ========================================================

    if doji_close < doji_ema and doji_rsi < 40:

        msg = f"""
⚠️ VALID SHORT DOJI FORMED

Symbol: NIFTY

Timeframe: {tf_name}

Doji High: {round(doji_high, 2)}

Doji Low: {round(doji_low, 2)}

RSI: {round(doji_rsi, 2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

        send_telegram_message(msg)

        # ----------------------------------------------------
        # ENTRY CONFIRMATION
        # ----------------------------------------------------

        if current_close < doji_low:

            entry_msg = f"""
🚨 SHORT ENTRY CONFIRMED

Symbol: NIFTY

Timeframe: {tf_name}

Breakdown Below: {round(doji_low, 2)}

Current Price: {round(current_close, 2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

            send_telegram_message(entry_msg)

        return

    # ========================================================
    # DOJI FOUND BUT EMA/RSI FAILED
    # ========================================================

    no_filter_msg = f"""
✅ Doji Found But EMA/RSI Conditions Failed

Timeframe: {tf_name}

RSI: {round(doji_rsi, 2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""

    send_telegram_message(no_filter_msg)

# ============================================================
# MAIN
# ============================================================

print("BOT STARTED")

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

                send_telegram_message(
                    f"❌ No data received for {label}"
                )

                continue

            check_strategy(df, label)

        except Exception as e:

            error_msg = f"""
❌ ERROR FOUND

Timeframe: {label}

Error:
{str(e)}
"""

            send_telegram_message(error_msg)

            print(e)

print("BOT FINISHED")
