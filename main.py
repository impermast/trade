from BOTS.analbot import Analytic
from STRATEGY.rsi import RSIonly_Strategy
import os
import pandas as pd

# Получаем путь к текущему файлу (аналог __file__)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Путь на уровень выше → в папку DATA
csv_path = os.path.join(current_dir, "DATA", "BTCUSDT_1h.csv")
csv_path = os.path.abspath(csv_path)  # абсолютный путь (на всякий случай)
df = pd.read_csv(csv_path)
if 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
anal = Analytic(df)
r = anal.make_strategy(RSIonly_Strategy,rsi={"period": 20, "lower": 20})
print(r)