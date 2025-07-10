# strategy/xgb_strategy.py

import pandas as pd
import numpy as np
import joblib
from xgboost import XGBRegressor

sys.path.append(os.path.abspath("."))
from STRATEGY.base import BaseStrategy

#НУЖНО БУДЕТ ЧТОТО СДЕЛАТЬ С РЕТЕРНАМИ
class XGBStrategy(BaseStrategy):
    def __init__(self, model_path="xgb_model_multi.joblib", features_path="xgb_model_features.joblib", slippage=0.0005, **params):
        super().__init__(name="XGBStrategy", indicators=['rsi','ema','macd','boll_upper','boll_lower','atr','ovb','return_1','return_3','return_6'], **params)
        self.model = joblib.load(model_path)
        self.features = joblib.load(features_path)
        self.slippage = slippage

    def default_params(self):
        return {
            "rsi": {"period": 14},
            'ema': {"period": 10}
        }

    def get_signals(self, df: pd.DataFrame) -> int:
        if df.shape[0] < 2:
            return 0

        row = df.iloc[-2] 
        next_open = df.iloc[-1]['open'] 
        X = row[self.features].values.reshape(1, -1)
        y_pred = self.model.predict(X)[0]  # предположим [signal, amount]
        signal = int(round(y_pred[0]))
        amount = float(y_pred[1])
        price_exec = next_open * (1 + self.slippage)

        
        df.at[df.index[-1], "xgb_signal"] = (signal,amount)

        return signal

if __name__ == "__main__":
    strat = XGBStrategy(rsi={"period": 10})
    # Должен выводить название стратегии и измененные параметры rsi
    print(strat)