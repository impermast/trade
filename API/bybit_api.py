# api/bybit_api.py

import ccxt
import pandas as pd
from API.birza_api import BirzaAPI
from BOTS.loggerbot import Logger

class BybitAPI(BirzaAPI):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.logger = Logger(name="bybitAPI", logfile="logs/bybitAPI.log").get_logger()

        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

        try:
            self.logger.info("Инициализация подключения к Bybit через ccxt...")
            assets = self.get_balance()
            self.logger.info(f"Подключение установлено. Активы: {list(assets.keys())}")
        except Exception as e:
            self.logger.exception(f"Ошибка инициализации BybitAPI: {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = "1m", limit: int = 100) -> pd.DataFrame:
        try:
            self.logger.info(f"Получение OHLCV: символ={symbol}, таймфрейм={timeframe}, лимит={limit}")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.rename(columns={"timestamp": "time"}, inplace=True)
            return df
        except Exception as e:
            self.logger.error(f"Ошибка при получении OHLCV: {e}")
            return pd.DataFrame()

    def place_order(self, symbol, side, qty, order_type="market", price=None):
        try:
            self.logger.info(f"Создание ордера: {side.upper()} {qty} {symbol}, тип={order_type.upper()}, цена={price}")
            params = {}

            if order_type == "market":
                return self.exchange.create_market_order(symbol, side.lower(), qty, params)
            elif order_type == "limit":
                return self.exchange.create_limit_order(symbol, side.lower(), qty, price, params)
            else:
                raise ValueError("Недопустимый тип ордера")
        except Exception as e:
            self.logger.error(f"Ошибка при создании ордера: {e}")
            return {}

    def get_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            return balance['total']
        except Exception as e:
            self.logger.error(f"Ошибка при получении баланса: {e}")
            return {}

    def get_positions(self, symbol: str):
        self.logger.warning("Метод get_positions не поддерживается ccxt для Bybit. Возвращён пустой словарь.")
        return {}

    def get_order_status(self, order_id: str):
        try:
            return self.exchange.fetch_order(order_id)
        except Exception as e:
            self.logger.error(f"Ошибка при проверке статуса ордера {order_id}: {e}")
            return {}
