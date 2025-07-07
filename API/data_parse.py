# download_data.py
import ccxt
import pandas as pd
from datetime import datetime
import time

def fetch_ohlcv_to_df(exchange, symbol, timeframe='1h', limit=1000):
    print(f"Загружаем {symbol} ({timeframe}) с биржи {exchange.id}...")

    all_data = []
    since = exchange.parse8601('2025-01-01T00:00:00Z')  # старт с января 2023
    now = exchange.milliseconds()

    while since < now:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_data += ohlcv
        since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000.0)  # пауза, чтобы не получить бан

        print(f"Загружено {len(all_data)} записей...")

        # if len(ohlcv) < 1000:
        #     break

    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# === Настройки биржи и инструмента ===
exchange = ccxt.bybit({
    'enableRateLimit': True
})
symbol = 'BTC/USDT'
timeframe = '15m'

# === Получение и сохранение данных ===
df = fetch_ohlcv_to_df(exchange, symbol, timeframe)
df.to_csv("DATA/BTCUSDT_1h.csv", index=False)

