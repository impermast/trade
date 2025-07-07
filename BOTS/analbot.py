# strategy/analbot.py

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

        def sma(self, period:int=10, inplace=True):
            self.parent.logger.info("Вычисление SMA.")
            df = self.parent.df
            df['sma'] = SMAIndicator(df['close'], window=period).sma_indicator()
            if inplace:
                self.parent.df["sma"] = df["sma"]
                return None
            else: return df.copy()

        def ema(self, period:int=10, inplace=True):
            self.parent.logger.info("Вычисление EMA.")
            df = self.parent.df
            df['ema']= EMAIndicator(df['close'], window=period).ema_indicator()
            if inplace:
                self.parent.df["ema"] = df["ema"]
                return None
            else: return df.copy()

        def rsi(self, period:int=14, inplace=True):
            self.parent.logger.info("Вычисление RSI.")
            df = self.parent.df
            df['rsi'] = RSIIndicator(df['close'], window=period).rsi()
            if inplace:
                self.parent.df["rsi"] = df["rsi"]
                return None
            else: return df.copy()

        def macd(self, window_slow:int=12, window_fast:int=26, window_sign:int=9, inplace=True):
            self.parent.logger.info("Вычисление MACD.")
            df = self.parent.df
            df['macd'] = MACD(df['close'], window_slow=window_slow, window_fast=window_fast, window_sign=window_sign).macd_diff()
            if inplace:
                self.parent.df["macd"] = df["macd"]
                return None
            else: return df.copy()

        def bollinger_bands(self, period:int=20, window_dev=2, inplace=True):
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
                return None
            else: return df.copy()

    @staticmethod
    def _get_expected_columns(name, params):
        if name == "sma":
            return [f"sma_{params['period']}"]
        elif name == "ema":
            return [f"ema_{params['period']}"]
        elif name == "rsi":
            return [f"rsi_{params['period']}"]
        elif name == "macd":
            return [f"macd_{params['window_fast']}_{params['window_slow']}"]
        elif name == "bollinger_bands":
            p = params['period']
            return [f"bb_h_{p}", f"bb_m_{p}", f"bb_l_{p}"]
        else:
            return []

    def make_calc(self, indicators):
        """
        indicators: список элементов:
            - либо кортежи вида: ("sma", {"period": 20})
            - либо строки: "sma" (используются параметры по умолчанию)
        """
        default_params = {
            "sma": {"period": 10},
            "ema": {"period": 10},
            "rsi": {"period": 14},
            "macd": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
            "bollinger_bands": {"period": 20, "window_dev": 2},
        }

        for item in indicators:
            if isinstance(item, str):
                name = item
                params = default_params.get(name, {})
            elif isinstance(item, tuple) and len(item) == 2:
                name, params = item
            else:
                self.logger.warning(f"Неверный формат индикатора: {item}")
                continue

            method = getattr(self.indicators, name, None)
            if method is None:
                self.logger.warning(f"Индикатор {name} не найден.")
                continue

            expected_columns = self._get_expected_columns(name, params)
            missing = [col for col in expected_columns if col not in self.df.columns]
            if not missing:
                self.logger.info(f"Пропускаем {name} — уже рассчитан.")
                continue

            try:
                method(inplace=True, **params)
                self.logger.info(f"Индикатор {name} рассчитан.")
            except Exception as e:
                self.logger.error(f"Ошибка при расчёте {name}: {e}")

    def make_strategy(self, strategy_cls):
        strategy = strategy_cls(self.df, **params)
        indicators = strategy.check_indicators()
        self.make_calc(indicators)
        result = strategy.get_signals(self.df)
        return result

