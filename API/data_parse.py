import ccxt
import pandas as pd
import time



def fetch_data(exchange, symbol, timeframe='1h', start_date='2025-01-01T00:00:00Z', limit=1000):

    exchange_class = getattr(ccxt, exchange)
    exchange = exchange_class({'enableRateLimit': True})

    if not start_date:
        raise ValueError("Необходимо указать start_date.")
    all_data = []
    since = exchange.parse8601(start_date)
    now = exchange.milliseconds()

    while since < now:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not ohlcv:
            break
        all_data += ohlcv
        since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000.0)

    data = all_data
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    return df


if __name__ == "__main__":
    a = fetch_data("bybit", "BTC/USDT", timeframe="15m", start_date="2025-05-05T00:00:00Z")
    print(a)