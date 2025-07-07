import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class Analytic:
    def __init__(self, df, logger):
        self.df = df
        self.logger = logger
        self.indicators = self.Indicators(self)

    class Indicators:
        def __init__(self, parent):
            self.parent = parent

        def sma(self, period=10, inplace=True):
            self.parent.logger.info("Вычисление SMA.")
            df = self.parent.df
            df['sma'] = SMAIndicator(df['close'], window=period).sma_indicator()
            if inplace: self.parent.df["sma"] = df["sma"]
            else: return df.copy()

        def ema(self, period=10, inplace=True):
            self.parent.logger.info("Вычисление EMA.")
            df = self.parent.df
            df['ema']= EMAIndicator(df['close'], window=period).ema_indicator()
            if inplace: self.parent.df["ema"] = df["ema"]
            else: return df.copy()

        def rsi(self, period=14, inplace=True):
            self.parent.logger.info("Вычисление RSI.")
            df = self.parent.df
            df['rsi'] = RSIIndicator(df['close'], window=period).rsi()
            if inplace: self.parent.df["rsi"] = df["rsi"]
            else: return df.copy()

        def macd(self, window_slow=12, window_fast=26, window_sign=9, inplace=True):
            self.parent.logger.info("Вычисление MACD.")
            df = self.parent.df
            df['macd'] = MACD(df['close'], window_slow=window_slow, window_fast=window_fast, window_sign=window_sign).macd_diff()
            if inplace: self.parent.df["macd"] = df["macd"]
            else: return df.copy()

        def bollinger_bands(self, period=20, window_dev=2, inplace=True):
            self.parent.logger.info("Вычи Bollinger Bands.")
            df = self.parent.df
            bb = BollingerBands(df['close'], window=period, window_dev=window_dev)
            df['bb_h'] = bb.bollinger_hband()
            df['bb_m'] = bb.bollinger_mavg()
            df['bb_l'] = bb.bollinger_lband()
            if inplace:
                self.parent.df["bb_h"] = df["bb_h"]
                self.parent.df["bb_m"] = df["bb_m"]
                self.parent.df["bb_l"] = df["bb_l"]
            else: return df.copy()