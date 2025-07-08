import time

import ccxt
import joblib
import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler



# === 1. Скачать данные с биржи через ccxt ===
def fetch_ohlcv_to_df(exchange, symbol, timeframe='5m', limit=10000):
    print(f"Загружаем {symbol} ({timeframe}) с биржи {exchange.id}...")

    all_data = []
    since = exchange.parse8601('2024-01-01T00:00:00Z')  # старт с января 2023
    now = exchange.milliseconds()

    while since < now:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=10000)
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

exchange = ccxt.bybit({
    'enableRateLimit': True
})
symbol = 'BTC/USDT'
timeframe = '5m'
df = fetch_ohlcv_to_df(exchange, symbol, timeframe)

# === 2. Добавить технические индикаторы ===
df.ta.rsi(length=14, append=True)
df.ta.ema(length=21, append=True)
df.ta.macd(append=True)
df.ta.bbands(append=True)

# Удалим строки с NaN
df.dropna(inplace=True)

print(df.columns.to_list())
# === 3. Создание фичей и таргета ===
feature_cols = [
    'close', 'RSI_14', 'EMA_21',
    'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
    'BBL_5_2.0', 'BBM_5_2.0', 'BBU_5_2.0', 'BBB_5_2.0', 'BBP_5_2.0'
]
target_shift = 3  # Предсказание close через 3 шага

df['target'] = df['close'].shift(-target_shift)
df.dropna(inplace=True)

X = df[feature_cols].values
y = df['target'].values.reshape(-1, 1)

# === 4. Нормализация ===
scaler_x = StandardScaler()
scaler_y = StandardScaler()
X_scaled = scaler_x.fit_transform(X)
y_scaled = scaler_y.fit_transform(y)

X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
y_tensor = torch.tensor(y_scaled, dtype=torch.float32)

class PricePredictor(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.net(x)

model = PricePredictor(X_tensor.shape[1])
loss_fn = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# === Обучение ===
for epoch in range(100):
    model.train()
    pred = model(X_tensor)
    loss = loss_fn(pred, y_tensor)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    if epoch % 10 == 0:
        print(f"Epoch {epoch}: loss = {loss.item():.4f}")

# Сохраняем модель
torch.save(model.state_dict(), "price_predictor.pth")

# Также желательно сохранить скейлеры
joblib.dump(scaler_x, "scaler_x.pkl")
joblib.dump(scaler_y, "scaler_y.pkl")

# Предсказание модели
model.eval()
with torch.no_grad():
    y_pred_scaled = model(X_tensor)
    y_pred = scaler_y.inverse_transform(y_pred_scaled.numpy())
    y_true = scaler_y.inverse_transform(y_tensor.numpy())

# Строим график
plt.figure(figsize=(18, 6))
plt.plot(y_true, label="Real price", linewidth=2)
plt.plot(y_pred, label="Predicted price", linestyle="--")
plt.title("BTC/USDT: true vs predicted price")
plt.xlabel("Time step (5min intervals)")
plt.ylabel("Price, USDT")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("try.png")
# plt.show()
