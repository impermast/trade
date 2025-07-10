# strategy/analbot.py
import os, sys

sys.path.append(os.path.abspath("."))
from BOTS.loggerbot import Logger
from STRATEGY.rsi import RSIonly_Strategy

from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

class Analytic:
    def __init__(self, df, source_file):
        self.df = df
        self.source_file = source_file
        self.logger = Logger(name="Analitic", tag="[ANAL]", logfile="logs/analitic.log", console=True).get_logger()
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


    def save_to_file(self):
        if self.source_file:
            try:
                self.df.to_csv(self.source_file, index=False)
                self.logger.info(f"Данные успешно сохранены в файл: {self.source_file}")
            except Exception as e:
                self.logger.error(f"Ошибка при сохранении файла: {e}")
        else:
            self.logger.warning("Файл не указан — сохранение невозможно.")


    def make_strategy(self, strategy_cls, **params):
        strategy = strategy_cls(**params)
        self.logger.info(f"Начинаю расчет для стратегии {strategy.name}")
        indicators, stratparams = strategy.check_indicators()
        self.make_calc(indicators, stratparams)
        self.save_to_file()
        result = strategy.get_signals(self.df)
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
    anal = Analytic(df,csv_path)
    r = anal.make_strategy(RSIonly_Strategy,rsi={"period": 20, "lower": 20})
    print(r)