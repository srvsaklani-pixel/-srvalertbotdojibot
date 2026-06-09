import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os

from datetime import datetime
import pytz

# ============================================================

# TELEGRAM CONFIG

# ============================================================

BOT_TOKEN = os.getenv("8873557784:AAH6gkeAYada9hR6JELYAplZvieelYO1aC0")
CHAT_ID = os.getenv("5067510130")

# ============================================================

# SETTINGS

# ============================================================

SYMBOLS = [
"^NSEI",
"^NSEBANK"
]

TIMEFRAMES = {
"3min": "3m",
"5min": "5m",
"10min": "10m",
"30min": "30m"
}

EMA_PERIOD = 200
RSI_PERIOD = 14

RR_LIST = [2, 3, 4, 5]

# ============================================================

# TELEGRAM MESSAGE

# ============================================================

def send_telegram(message):

```
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.get(
    url,
    params={
        "chat_id": CHAT_ID,
        "text": message
    }
)
```

# ============================================================

# RSI

# ============================================================

def calculate_rsi(close, period=14):

```
delta = close.diff()

gain = np.where(delta > 0, delta, 0)
loss = np.where(delta < 0, -delta, 0)

gain = pd.Series(gain).rolling(period).mean()
loss = pd.Series(loss).rolling(period).mean()

rs = gain / loss

rsi = 100 - (100 / (1 + rs))

return rsi.values
```

# ============================================================

# HEIKIN ASHI

# ============================================================

def heikin_ashi(df):

```
ha = pd.DataFrame(index=df.index)

ha['ha_close'] = (
    df['Open'] +
    df['High'] +
    df['Low'] +
    df['Close']
) / 4

ha_open = []

for i in range(len(df)):

    if i == 0:

        first_open = (
            df['Open'].iloc[0] +
            df['Close'].iloc[0]
        ) / 2

        ha_open.append(first_open)

    else:

        value = (
            ha_open[i - 1] +
            ha['ha_close'].iloc[i - 1]
        ) / 2

        ha_open.append(value)

ha['ha_open'] = ha_open

ha['ha_high'] = pd.concat([
    df['High'],
    ha['ha_open'],
    ha['ha_close']
], axis=1).max(axis=1)

ha['ha_low'] = pd.concat([
    df['Low'],
    ha['ha_open'],
    ha['ha_close']
], axis=1).min(axis=1)

return ha
```

# ============================================================

# DOJI CHECK

# ============================================================

def is_doji(row):

```
body = abs(
    row['ha_close'] -
    row['ha_open']
)

full_range = (
    row['ha_high'] -
    row['ha_low']
)

if full_range == 0:
    return False

body_percent = body / full_range

return body_percent <= 0.12
```

# ============================================================

# DATA DOWNLOAD

# ============================================================

def fetch_data(symbol, interval):

```
df = yf.download(
    symbol,
    period="10d",
    interval=interval,
    progress=False,
    auto_adjust=False
)

if df.empty:
    return None

return df
```

# ============================================================

# MAIN STRATEGY

# ============================================================

def check_setup(symbol, timeframe_name, interval):

```
print(f"Checking {symbol} {timeframe_name}")

df = fetch_data(symbol, interval)

if df is None:
    return

# ========================================================
# INDICATORS
# ========================================================

df['EMA200'] = df['Close'].ewm(
    span=EMA_PERIOD,
    adjust=False
).mean()

df['RSI'] = calculate_rsi(
    df['Close'],
    RSI_PERIOD
)

# ========================================================
# HEIKIN ASHI
# ========================================================

ha = heikin_ashi(df)

df = pd.concat([df, ha], axis=1)

if len(df) < 5:
    return

# ========================================================
# LAST 3 CANDLES
# ========================================================

doji = df.iloc[-3]

confirm = df.iloc[-2]

trigger = df.iloc[-1]

# ========================================================
# DOJI CHECK
# ========================================================

if not is_doji(doji):
    return

# ========================================================
# LONG CONDITIONS
# ========================================================

long_condition = (

    confirm['ha_close'] >
    confirm['ha_open']

    and

    trigger['High'] >
    confirm['ha_high']

    and

    trigger['Close'] >
    trigger['EMA200']

    and

    trigger['RSI'] > 60
)

# ========================================================
# SHORT CONDITIONS
# ========================================================

short_condition = (

    confirm['ha_close'] <
    confirm['ha_open']

    and

    trigger['Low'] <
    confirm['ha_low']

    and

    trigger['Close'] <
    trigger['EMA200']

    and

    trigger['RSI'] < 40
)

# ========================================================
# LONG SIGNAL
# ========================================================

if long_condition:

    entry = round(
        confirm['ha_high'],
        2
    )

    sl = round(
        doji['ha_low'],
        2
    )

    risk = entry - sl

    if risk <= 0:
        return

    targets = []

    for rr in RR_LIST:

        tp = round(
            entry + (risk * rr),
            2
        )

        targets.append(
            f"1:{rr} = {tp}"
        )

    message = f"""
```

🚨 LONG SIGNAL

Symbol: {symbol}

Timeframe:
{timeframe_name}

Entry:
{entry}

SL:
{sl}

Targets:
{chr(10).join(targets)}

EMA200:
PASS

RSI:
{round(trigger['RSI'], 2)}

Time:
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

```
    print(message)

    send_telegram(message)

# ========================================================
# SHORT SIGNAL
# ========================================================

if short_condition:

    entry = round(
        confirm['ha_low'],
        2
    )

    sl = round(
        doji['ha_high'],
        2
    )

    risk = sl - entry

    if risk <= 0:
        return

    targets = []

    for rr in RR_LIST:

        tp = round(
            entry - (risk * rr),
            2
        )

        targets.append(
            f"1:{rr} = {tp}"
        )

    message = f"""
```

🚨 SHORT SIGNAL

Symbol: {symbol}

Timeframe:
{timeframe_name}

Entry:
{entry}

SL:
{sl}

Targets:
{chr(10).join(targets)}

EMA200:
PASS

RSI:
{round(trigger['RSI'], 2)}

Time:
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

```
    print(message)

    send_telegram(message)
```

# ============================================================

# MAIN

# ============================================================

print("🚀 BOT STARTED")

india = pytz.timezone("Asia/Kolkata")

now = datetime.now(india)

heartbeat = f"""
✅ BOT RUNNING

Time:
{now.strftime('%Y-%m-%d %H:%M:%S IST')}
"""

send_telegram(heartbeat)

for symbol in SYMBOLS:

```
for timeframe_name, interval in TIMEFRAMES.items():

    try:

        check_setup(
            symbol,
            timeframe_name,
            interval
        )

    except Exception as e:

        print(
            "ERROR:",
            symbol,
            timeframe_name,
            e
        )
```
