import asyncio
import pandas as pd

from API.bybit_api import BybitAPI
from API.mock_api import MockAPI
from BOTS.analbot import Analytic
from STRATEGY.rsi import RSIonly_Strategy
from BOTS.loggerbot import Logger
from BOTS.PLOTBOTS.plotbot import PlotBot

UPDATE_INTERVAL = 60  # секунд
SYMBOL = "BTC/USDT"
TF = "1m"


SYMBOL_NAME = SYMBOL.replace("/", "")
CSV_PATH = f"DATA/{SYMBOL_NAME}_{TF}_anal.csv"
logger = Logger(
    name="MainBot", 
    tag="[MAIN]", 
    logfile="LOGS/mainbot.log", 
    console=True).get_logger()
stop_event = asyncio.Event()

async def plot_loop():
    logger.info("Запущен графический цикл")
    def start_plotbot():
        plotbot = PlotBot(csv_file=CSV_PATH, refresh_interval=UPDATE_INTERVAL)
        plotbot.start()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, start_plotbot)

async def trading_loop(botapi):
    logger.info(f"Запущен торговый цикл {type(botapi).__name__}")
    try:
        while not stop_event.is_set():
            df = await botapi.get_ohlcv_async(SYMBOL, timeframe=TF, limit=100)
            analytic = Analytic(df, data_name=f"{SYMBOL_NAME}_{TF}")
            signal = analytic.make_strategy(RSIonly_Strategy, rsi={"period": 14, "lower": 30, "upper": 70})

            if signal == 1:
                logger.info("Сигнал: ПОКУПКА")
                await botapi.place_order_async(SYMBOL, "buy", qty=0.001)
            elif signal == -1:
                logger.info("Сигнал: ПРОДАЖА")
                await botapi.place_order_async(SYMBOL, "sell", qty=0.001)
            # Save CSV for plotbot
            df.to_csv(CSV_PATH, index=False)
            await asyncio.sleep(UPDATE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Торговый цикл был отменён")
        raise
    finally:
        if hasattr(botapi, "close_async"):
            await botapi.close_async()
        logger.info("Торговый цикл завершён")

async def main():
    botapi = MockAPI()
    try:
        await asyncio.gather(
            trading_loop(botapi)
        )
    except KeyboardInterrupt:
        logger.warning("Получен KeyboardInterrupt. Завершаем...")
        stop_event.set()
        # Дождёмся завершения тасков
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Ошибка в главной функции: {e}", exc_info=True)
        stop_event.set()
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt вне asyncio.run — выходим")
