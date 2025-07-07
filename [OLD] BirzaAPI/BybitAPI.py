
import pandas as pd
from pybit.unified_trading import HTTP
import BirzaAPI


class BybitAPI(BirzaAPI):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.session = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )
        self.logger = local_logging("[OLD] BirzaAPI")
    def check_connection(self):
        logger = self.logger    
        try:
            logger.info("🔌 Инициализация подключения к Bybit API...")
            
            # Тест баланса
            balance = self.session.get_wallet_balance(accountType="UNIFIED")
            usdt = balance["result"]["list"][0]["coin"][0]
            logger.info(f"💰 Баланс USDT: {usdt['availableToWithdraw']}")

            # Тест свечей
            candles = self.session.get_kline(
                category="linear",
                symbol="BTCUSDT",
                interval="1m",
                limit=3
            )
            if not candles.get("result") or not candles["result"]["list"]:
                raise RuntimeError("Свечи не загружены — возможно, API недоступен.")

            logger.info(f"📈 Получены {len(candles['result']['list'])} свечи по BTCUSDT.")
            logger.info("✅ Bybit API успешно инициализирован.")

        except Exception as e:
            logger.exception(f"❌ Ошибка инициализации BybitAPI: {e}")
            raise

    # Пример метода с логами
    def get_ohlcv(self, symbol, timeframe="1m", limit=200):
        logger = self.logger
        try:
            logger.info(f"📊 Загрузка {limit} свечей {symbol} с таймфреймом {timeframe}")
            res = self.session.get_kline(
                category="linear",
                symbol=symbol.replace("/", ""),
                interval=timeframe,
                limit=limit
            )
            df = pd.DataFrame(res["result"]["list"], columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            df = df.astype(float)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.rename(columns={"timestamp": "time"}, inplace=True)
            return df[["time", "open", "high", "low", "close", "volume"]]
        except Exception as e:
            logger.error(f"Ошибка при загрузке OHLCV: {e}")
            return pd.DataFrame()


def local_logging(logname):
    import logging

    logger = logging.getLogger(logname)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

if "__name__" ==  __main__:
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    check_bot = BybitAPI(api_key=api_key, api_secret=api_secret, testnet=True)
    check_bot.check_connection()