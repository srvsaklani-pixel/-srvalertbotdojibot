import os
import requests
import yfinance as yf
import pandas as pd
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

SYMBOLS = ["^NSEI"]

# USE ONLY YFINANCE SUPPORTED INTERVALS

TIMEFRAMES = {
    "5m": "5MIN",
    "15m": "15MIN",
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

def is_valid_doji(open_price, close_price, high_price, low_price):

    body = abs(close_price - open_price)

    candle_range = high_price - low_price

    if candle_range == 0:
        return False

    body_percent = (body / candle_range) * 100

    # ORIGINAL STRATEGY RULES

    if body <= 2:
        return True

    if body_percent <= 12:
        return True

    return False

# ============================================================
# STRATEGY
# ============================================================

def check_strategy(df, tf_name):

    # --------------------------------------------------------
    # FIX MULTI INDEX COLUMNS
    # --------------------------------------------------------

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # --------------------------------------------------------
    # EMA200
    # --------------------------------------------------------

    df['EMA200'] = df['Close'].ewm(span=EMA_PERIOD).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)

    df.dropna(inplace=True)

    if len(df) < 5:
        return

    # --------------------------------------------------------
    # CANDLES
    # --------------------------------------------------------

    doji = df.iloc[-3]

    current = df.iloc[-1]

    # --------------------------------------------------------
    # VALUES
    # --------------------------------------------------------

    doji_open = float(doji['Open'])

    doji_close = float(doji['Close'])

    doji_high = float(doji['High'])

    doji_low = float(doji['Low'])

    doji_ema = float(doji['EMA200'])

    doji_rsi = float(doji['RSI'])

    current_close = float(current['Close'])

    # ========================================================
    # VALID DOJI ?
    # ========================================================

    valid_doji = is_valid_doji(
        doji_open,
        doji_close,
        doji_high,
        doji_low
    )

    if not valid_doji:

        send_telegram_message(
f"""✅ Scan Completed

Timeframe: {tf_name}

No valid strategy doji found.

Time: {datetime.now().strftime('%H:%M:%S')}
"""
        )

        return

    # ========================================================
    # LONG SETUP
    # ========================================================

    if doji_close > doji_ema and doji_rsi > 60:

        send_telegram_message(
f"""⚠️ VALID LONG DOJI FORMED

Timeframe: {tf_name}

Doji High: {round(doji_high,2)}

Doji Low: {round(doji_low,2)}

RSI: {round(doji_rsi,2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
        )

        # ENTRY

        if current_close > doji_high:

            send_telegram_message(
f"""🚨 LONG ENTRY CONFIRMED

Timeframe: {tf_name}

Breakout Above: {round(doji_high,2)}

Current Price: {round(current_close,2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
            )

        return

    # ========================================================
    # SHORT SETUP
    # ========================================================

    if doji_close < doji_ema and doji_rsi < 40:

        send_telegram_message(
f"""⚠️ VALID SHORT DOJI FORMED

Timeframe: {tf_name}

Doji High: {round(doji_high,2)}

Doji Low: {round(doji_low,2)}

RSI: {round(doji_rsi,2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
        )

        # ENTRY

        if current_close < doji_low:

            send_telegram_message(
f"""🚨 SHORT ENTRY CONFIRMED

Timeframe: {tf_name}

Breakdown Below: {round(doji_low,2)}

Current Price: {round(current_close,2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
            )

        return

    # ========================================================
    # DOJI FOUND BUT FILTER FAILED
    # ========================================================

    send_telegram_message(
f"""✅ Doji Found But EMA/RSI Conditions Failed

Timeframe: {tf_name}

RSI: {round(doji_rsi,2)}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
    )

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
f"""❌ No data received

Timeframe: {label}
"""
                )

                continue

            check_strategy(df, label)

        except Exception as e:

            send_telegram_message(
f"""❌ ERROR FOUND

Timeframe: {label}

Error:
{str(e)}
"""
            )

            print(e)

print("BOT FINISHED")
