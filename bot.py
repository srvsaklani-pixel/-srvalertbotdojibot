import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

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
# INDIAN TIME
# ============================================================

IST = pytz.timezone('Asia/Kolkata')

def indian_time():

    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')

# ============================================================
# SETTINGS
# ============================================================

SYMBOLS = ["^NSEI"]

TIMEFRAMES = {
    "3min": "3MIN",
    "5min": "5MIN",
    "10min": "10MIN",
    "30min": "30MIN"
}

EMA_PERIOD = 200
RSI_PERIOD = 14

DOJI_ABS = 2
DOJI_BODY_PCT = 12

EQ_TOLERANCE = 0.5

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
# HEIKIN ASHI
# ============================================================

def heikin_ashi(df):

    ha = pd.DataFrame(index=df.index)

    ha['Open'] = df['Open']
    ha['High'] = df['High']
    ha['Low'] = df['Low']
    ha['Close'] = df['Close']

    # --------------------------------------------------------
    # HA CLOSE
    # --------------------------------------------------------

    ha['ha_close'] = (
        df['Open'] +
        df['High'] +
        df['Low'] +
        df['Close']
    ) / 4

    # --------------------------------------------------------
    # HA OPEN
    # --------------------------------------------------------

    ha_open = []

    first_ha_open = (
        df['Open'].iloc[0] +
        df['Close'].iloc[0]
    ) / 2

    ha_open.append(first_ha_open)

    for i in range(1, len(df)):

        value = (
            ha_open[i - 1] +
            ha['ha_close'].iloc[i - 1]
        ) / 2

        ha_open.append(value)

    ha['ha_open'] = ha_open

    # --------------------------------------------------------
    # HA HIGH / LOW
    # --------------------------------------------------------

    ha['ha_high'] = ha[
        ['High', 'ha_open', 'ha_close']
    ].max(axis=1)

    ha['ha_low'] = ha[
        ['Low', 'ha_open', 'ha_close']
    ].min(axis=1)

    # --------------------------------------------------------
    # BODY
    # --------------------------------------------------------

    ha['ha_body'] = abs(
        ha['ha_close'] - ha['ha_open']
    )

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    ha['ha_color'] = np.where(
        ha['ha_close'] >= ha['ha_open'],
        'green',
        'red'
    )

    return ha

# ============================================================
# VALID DOJI
# ============================================================

def is_valid_doji(candle):

    body = candle['ha_body']

    candle_range = (
        candle['ha_high'] - candle['ha_low']
    )

    if candle_range == 0:
        return False

    body_percent = (
        body / candle_range
    ) * 100

    # ORIGINAL STRATEGY RULES

    if body <= DOJI_ABS:
        return True

    if body_percent <= DOJI_BODY_PCT:
        return True

    return False

# ============================================================
# STRATEGY CHECK
# ============================================================

def check_strategy(df, tf_name):

    # --------------------------------------------------------
    # EMA200
    # --------------------------------------------------------

    df['EMA200'] = df['Close'].ewm(
        span=EMA_PERIOD
    ).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    df['RSI'] = calculate_rsi(
        df['Close'],
        RSI_PERIOD
    )

    df.dropna(inplace=True)

    # --------------------------------------------------------
    # HEIKIN ASHI
    # --------------------------------------------------------

    ha = heikin_ashi(df)

    ha['EMA200'] = df['EMA200']

    ha['RSI'] = df['RSI']

    if len(ha) < 5:
        return

    # --------------------------------------------------------
    # CANDLES
    # --------------------------------------------------------

    doji = ha.iloc[-3]

    confirm = ha.iloc[-2]

    current = ha.iloc[-1]

    # ========================================================
    # VALID DOJI ?
    # ========================================================

    if not is_valid_doji(doji):

        send_telegram_message(
f"""✅ Scan Completed

Timeframe: {tf_name}

No valid strategy doji found.

Alert Time:
{indian_time()}
"""
        )

        return

    # ========================================================
    # LONG CONDITIONS
    # ========================================================

    long_confirm = (

        confirm['ha_color'] == 'green'

        and

        abs(
            confirm['ha_open'] -
            confirm['ha_low']
        ) <= EQ_TOLERANCE

        and

        doji['Close'] > doji['EMA200']

        and

        doji['RSI'] > 60

    )

    # ========================================================
    # SHORT CONDITIONS
    # ========================================================

    short_confirm = (

        confirm['ha_color'] == 'red'

        and

        abs(
            confirm['ha_open'] -
            confirm['ha_high']
        ) <= EQ_TOLERANCE

        and

        doji['Close'] < doji['EMA200']

        and

        doji['RSI'] < 40

    )

    # ========================================================
    # LONG ALERT
    # ========================================================

    if long_confirm:

        send_telegram_message(
f"""⚠️ VALID LONG DOJI FORMED

Timeframe: {tf_name}

🕯️ Doji Candle Time:
{doji.name.strftime('%Y-%m-%d %H:%M IST')}

Doji High:
{round(doji['ha_high'],2)}

Doji Low:
{round(doji['ha_low'],2)}

RSI:
{round(doji['RSI'],2)}

Alert Time:
{indian_time()}
"""
        )

        # ----------------------------------------------------
        # ENTRY CONFIRMATION
        # ----------------------------------------------------

        if current['High'] > confirm['ha_high']:

            send_telegram_message(
f"""🚨 LONG ENTRY CONFIRMED

Timeframe: {tf_name}

🕯️ Doji Candle Time:
{doji.name.strftime('%Y-%m-%d %H:%M IST')}

Breakout Above:
{round(confirm['ha_high'],2)}

Current Price:
{round(current['Close'],2)}

Alert Time:
{indian_time()}
"""
            )

        return

    # ========================================================
    # SHORT ALERT
    # ========================================================

    if short_confirm:

        send_telegram_message(
f"""⚠️ VALID SHORT DOJI FORMED

Timeframe: {tf_name}

🕯️ Doji Candle Time:
{doji.name.strftime('%Y-%m-%d %H:%M IST')}

Doji High:
{round(doji['ha_high'],2)}

Doji Low:
{round(doji['ha_low'],2)}

RSI:
{round(doji['RSI'],2)}

Alert Time:
{indian_time()}
"""
        )

        # ----------------------------------------------------
        # ENTRY CONFIRMATION
        # ----------------------------------------------------

        if current['Low'] < confirm['ha_low']:

            send_telegram_message(
f"""🚨 SHORT ENTRY CONFIRMED

Timeframe: {tf_name}

🕯️ Doji Candle Time:
{doji.name.strftime('%Y-%m-%d %H:%M IST')}

Breakdown Below:
{round(confirm['ha_low'],2)}

Current Price:
{round(current['Close'],2)}

Alert Time:
{indian_time()}
"""
            )

        return

    # ========================================================
    # DOJI FOUND BUT CONFIRM FAILED
    # ========================================================

    send_telegram_message(
f"""✅ Doji Found But Confirmation Failed

Timeframe: {tf_name}

🕯️ Doji Candle Time:
{doji.name.strftime('%Y-%m-%d %H:%M IST')}

RSI:
{round(doji['RSI'],2)}

Alert Time:
{indian_time()}
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

            # ------------------------------------------------
            # DOWNLOAD LIVE 1M DATA
            # ------------------------------------------------

            base_df = yf.download(
                symbol,
                period="7d",
                interval="1m",
                progress=False
            )

            # ------------------------------------------------
            # FIX MULTI INDEX
            # ------------------------------------------------

            if isinstance(
                base_df.columns,
                pd.MultiIndex
            ):
                base_df.columns = (
                    base_df.columns
                    .get_level_values(0)
                )

            if base_df.empty:

                send_telegram_message(
f"""❌ No data received

Timeframe: {label}

Alert Time:
{indian_time()}
"""
                )

                continue

            # ------------------------------------------------
            # RESAMPLE
            # ------------------------------------------------

            df = base_df.resample(interval).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

            # ------------------------------------------------
            # STRATEGY CHECK
            # ------------------------------------------------

            check_strategy(df, label)

        except Exception as e:

            send_telegram_message(
f"""❌ ERROR FOUND

Timeframe: {label}

Error:
{str(e)}

Alert Time:
{indian_time()}
"""
            )

            print(e)

print("BOT FINISHED")
