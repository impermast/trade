import ccxt
import pandas as pd
from datetime import datetime
import time
import os


def fetch_historical_data(exchange, symbol, start_date='2023-01-01T00:00:00Z', timeframe='1h', save_path=None):
    """
    Загрузка исторических OHLCV-данных.
    """
    print(f"Загружаем исторические данные {symbol} с {start_date} ({timeframe}) через {exchange.id}...")
    all_data = []
    since = exchange.parse8601(start_date)
    now = exchange.milliseconds()

    while since < now:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_data += ohlcv
        since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000.0)

        print(f"Загружено {len(all_data)} записей...")

    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path, index=False)
        print(f"Данные сохранены в {save_path}")

    return df


def fetch_live_data(exchange, symbol, timeframe='1m', limit=100):
    """
    Получение последних свечей в реальном времени.
    """
    print(f"Получаем последние {limit} свечей {symbol} ({timeframe}) через {exchange.id}...")
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df



if __name__ == "__main__":
    exchange = ccxt.bybit({'enableRateLimit': True})
    symbol = 'BTC/USDT'

    # Исторические данные
    df_hist = fetch_historical_data(exchange, symbol, start_date='2023-01-01T00:00:00Z',
                                     timeframe='15m', save_path='DATA/BTCUSDT_15m_historical.csv')

    # Актуальные данные (например, для стратегии в реальном времени)
    df_live = fetch_live_data(exchange, symbol, timeframe='1m', limit=50)
    print(df_live.tail())
