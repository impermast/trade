import joblib
from xgboost import XGBRegressor
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from CORE.log_manager import Logger

# Setup logger
logger = Logger(name="BDT", tag="[BDT]", logfile="LOGS/bdt.log", console=True).get_logger()

model = joblib.load('xgb_model_multi.joblib')
features = joblib.load('xgb_model_features.joblib')

# df['rsi']         = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
# df['ema']         = ta.trend.EMAIndicator(df['close'], window=10).ema_indicator()
# df['macd']        = ta.trend.MACD(df['close']).macd()
# df['boll_upper']  = ta.volatility.BollingerBands(df['close']).bollinger_hband()
# df['boll_lower']  = ta.volatility.BollingerBands(df['close']).bollinger_lband()
# df['atr']         = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
# df['obv']         = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
# df['return_1h']   = df['close'].pct_change(1)
# df['return_3h']   = df['close'].pct_change(3)
# df['return_6h']   = df['close'].pct_change(6)
# df['hour']        = df['timestamp'].dt.hour

for i in range(len(df) - 2):  # -2 для проскальзывания
    row = df.iloc[i]
    price_exec = df.iloc[i + 1]['open'] * (1 + slippage_percent)  # цена сделки с проскальзыванием
    time = row['timestamp']

    X = row[features].values.reshape(1, -1)
    y_pred = model.predict(X)[0]
    action = round(y_pred[0])
    amount = max(min_trade_amt, float(y_pred[1]))

    # Ограничение на покупку: не больше половины доступного USDT
    if action == 1:
        amount = min(amount/10, usdt * 0.5)

    usdt_before = usdt
    btc_before = btc

    if action == 1 and usdt >= min_trade_amt and amount >= min_trade_amt:
        trade_amt = min(usdt, amount)
        btc_gained = (trade_amt * (1 - fee_rate)) / price_exec
        btc += btc_gained
        usdt -= trade_amt
        act = "buy"
        logger.info(f"[{time}] BUY:  ${trade_amt:>6.2f} → {btc_gained:.6f} BTC @ {price_exec:.2f} USD | Fee: {fee_rate*100:.2f}% | USDT: {usdt_before:.2f}→{usdt:.2f} | BTC: {btc_before:.6f}→{btc:.6f}")

    elif action == 2 and btc > 0:
        max_sell_usdt = btc * price_exec
        sell_amt = min(max_sell_usdt, amount)
        btc_to_sell = sell_amt / price_exec
        usdt_gained = btc_to_sell * price_exec * (1 - fee_rate)
        btc -= btc_to_sell
        usdt += usdt_gained
        act = "sell"
        logger.info(f"[{time}] SELL: {btc_to_sell:.6f} BTC → ${usdt_gained:>6.2f} @ {price_exec:.2f} USD | Fee: {fee_rate*100:.2f}% | BTC: {btc_before:.6f}→{btc:.6f} | USDT: {usdt_before:.2f}→{usdt:.2f}")

    else:
        act = "hold"

    if usdt < -1e-6 or btc < -1e-6:
        raise ValueError("❌ Отрицательный баланс! Проверь расчёты.")

    history.append({
        'time': time,
        'price': row['close'],
        'usdt': usdt,
        'btc': btc,
        'action': act,
        'predicted_amount': amount,
        'btc_value': btc * price_exec,
        'total_value': usdt + btc * price_exec
    })