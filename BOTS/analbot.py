# strategy/analbot.py
import os, sys
import pandas as pd

sys.path.append(os.path.abspath("."))
from BOTS.loggerbot import Logger
from STRATEGY.rsi import RSIonly_Strategy

from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class Analytic:
    def __init__(self, df, data_name:str ,output_file = "anal.csv"):
        self.df = df
        self.logger = Logger(name="Analitic", tag="[ANAL]", logfile="logs/analitic.log", console=True).get_logger()
        self.indicators = self.Indicators(self)
        self.output_file = output_file
        self.data_name = data_name
        self.output_path = f'DATA/{data_name}_{output_file}'

    class Indicators:
        def __init__(self, parent):
            self.parent = parent

        def sma(self, period: int = 10, inplace=True):
            self.parent.logger.info("Вычисление SMA.")
            df = self.parent.df
            col_name = f"sma_{period}" if period != 10 else "sma"
            df[col_name] = SMAIndicator(df['close'], window=period).sma_indicator()
            if inplace:
                self.parent.df[col_name] = df[col_name]
            else:
                return df[[col_name]].copy()

        def ema(self, period: int = 10, inplace=True):
            self.parent.logger.info("Вычисление EMA.")
            df = self.parent.df
            col_name = f"ema_{period}" if period != 10 else "ema"
            df[col_name] = EMAIndicator(df['close'], window=period).ema_indicator()
            if inplace:
                self.parent.df[col_name] = df[col_name]
            else:
                return df[[col_name]].copy()

        def rsi(self, period: int = 14, inplace=True):
            self.parent.logger.info("Вычисление RSI.")
            df = self.parent.df
            col_name = f"rsi_{period}" if period != 14 else "rsi"
            df[col_name] = RSIIndicator(df['close'], window=period).rsi()
            if inplace:
                self.parent.df[col_name] = df[col_name]
            else:
                return df[[col_name]].copy()

        def macd(self, window_slow: int = 12, window_fast: int = 26, window_sign: int = 9, inplace=True):
            self.parent.logger.info("Вычисление MACD.")
            df = self.parent.df
            is_default = (window_slow == 12 and window_fast == 26)
            col_name = f"macd_{window_fast}_{window_slow}" if not is_default else "macd"
            df[col_name] = MACD(
                df['close'],
                window_slow=window_slow,
                window_fast=window_fast,
                window_sign=window_sign
            ).macd_diff()
            if inplace:
                self.parent.df[col_name] = df[col_name]
            else:
                return df[[col_name]].copy()

        def bollinger_bands(self, period: int = 20, window_dev=2, inplace=True):
            self.parent.logger.info("Вычисление Bollinger Bands.")
            df = self.parent.df
            suffix = f"_{period}" if period != 20 else ""
            col_h = f"bb_h{suffix}"
            col_m = f"bb_m{suffix}"
            col_l = f"bb_l{suffix}"

            bb = BollingerBands(df['close'], window=period, window_dev=window_dev)
            df[col_h] = bb.bollinger_hband()
            df[col_m] = bb.bollinger_mavg()
            df[col_l] = bb.bollinger_lband()

            if inplace:
                self.parent.df[col_h] = df[col_h]
                self.parent.df[col_m] = df[col_m]
                self.parent.df[col_l] = df[col_l]
            else:
                return df[[col_h, col_m, col_l]].copy()

    @staticmethod
    def _get_expected_columns(name, params):
        defaults = {
            "sma": {"period": 10},
            "ema": {"period": 10},
            "rsi": {"period": 14},
            "macd": {"window_fast": 12, "window_slow": 26},
            "bollinger_bands": {"period": 20},
        }

        def is_default(param, value):
            return defaults.get(name, {}).get(param) == value

        if name == "sma":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"sma{suffix}"]

        elif name == "ema":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"ema{suffix}"]

        elif name == "rsi":
            suffix = f"_{params['period']}" if not is_default("period", params.get("period")) else ""
            return [f"rsi{suffix}"]

        elif name == "macd":
            fast = params.get("window_fast")
            slow = params.get("window_slow")
            is_def = is_default("window_fast", fast) and is_default("window_slow", slow)
            suffix = f"_{fast}_{slow}" if not is_def else ""
            return [f"macd{suffix}"]

        elif name == "bollinger_bands":
            p = params["period"]
            suffix = f"_{p}" if not is_default("period", p) else ""
            return [f"bb_h{suffix}", f"bb_m{suffix}", f"bb_l{suffix}"]

        return []

    def make_calc(self, indicators, stratparams):
        import inspect
        self.logger.info(f"Выполняю вычисления для индикаторов {stratparams}")

        for item in stratparams:
            indicator_name = item
            params = stratparams.get(indicator_name, {})

            self.logger.info(f"Вычисляю для индикатора {indicator_name} при параметрах {params}")

            method = getattr(self.indicators, indicator_name, None)
            if method is None:
                self.logger.warning(f"Индикатор {indicator_name} не найден.")
                continue

            expected_columns = self._get_expected_columns(indicator_name, params)
            missing = [col for col in expected_columns if col not in self.df.columns]
            if not missing:
                self.logger.info(f"Пропускаем {indicator_name} — уже рассчитан.")
                continue

            # 🔧 Фильтруем только допустимые параметры
            method_params = inspect.signature(method).parameters
            filtered_params = {k: v for k, v in params.items() if k in method_params}

            try:
                method(inplace=True, **filtered_params)
                self.logger.info(f"Индикатор {indicator_name} рассчитан.")
            except Exception as e:
                self.logger.error(f"Ошибка при расчёте {indicator_name}: {e}")


    def make_strategy(self, strategy_cls, inplace = True, **params):
        strategy = strategy_cls(**params)
        self.logger.info(f"Начинаю расчет для стратегии {strategy.name}")
        
        indicators, stratparams = strategy.check_indicators()
        self.make_calc(indicators, stratparams)
        result = strategy.get_signals(self.df)
        
        if inplace:
            try:
                df.to_csv(self.output_path, index=False)
                self.logger.info(f"Данные анализа сохранены в {self.output_path}")
            except Exception as e:
                self.logger.error(f"Ошибка сохранения {self.output_path}: {e}")
                
        return result

if __name__ == "__main__":
    import pandas as pd
    # Получаем путь к текущему файлу (аналог __file__)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Путь на уровень выше → в папку DATA
    csv_path = os.path.join(current_dir, "..", "DATA", "BTCUSDT_1h.csv")
    csv_path = os.path.abspath(csv_path)  # абсолютный путь (на всякий случай)
    df = pd.read_csv(csv_path)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    anal = Analytic(df,"BTCUSDT_1h")
    r = anal.make_strategy(RSIonly_Strategy,rsi={"period": 20, "lower": 20})
    print(r)