import pandas as pd
import ta
import joblib
import numpy as np
from xgboost import XGBRegressor

model = joblib.load('xgb_model_multi.joblib')
features = joblib.load('xgb_model_features.joblib')

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
        print(f"[{time}] BUY:  ${trade_amt:>6.2f} → {btc_gained:.6f} BTC @ {price_exec:.2f} USD | Fee: {fee_rate*100:.2f}% | USDT: {usdt_before:.2f}→{usdt:.2f} | BTC: {btc_before:.6f}→{btc:.6f}")

    elif action == 2 and btc > 0:
        max_sell_usdt = btc * price_exec
        sell_amt = min(max_sell_usdt, amount)
        btc_to_sell = sell_amt / price_exec
        usdt_gained = btc_to_sell * price_exec * (1 - fee_rate)
        btc -= btc_to_sell
        usdt += usdt_gained
        act = "sell"
        print(f"[{time}] SELL: {btc_to_sell:.6f} BTC → ${usdt_gained:>6.2f} @ {price_exec:.2f} USD | Fee: {fee_rate*100:.2f}% | BTC: {btc_before:.6f}→{btc:.6f} | USDT: {usdt_before:.2f}→{usdt:.2f}")

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