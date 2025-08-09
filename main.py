import asyncio
import os
import socket
import sys
from typing import Optional

import pandas as pd

from API.bybit_api import BybitAPI  # при желании замени на MockAPI
from API.mock_api import MockAPI
from BOTS.analbot import Analytic
from STRATEGY.rsi import RSIonly_Strategy
from BOTS.loggerbot import Logger
from BOTS.PLOTBOTS.plotbot import PlotBot
from API.dashboard_api import run_flask_in_new_terminal, stop_flask

# ------------ Конфиг ------------
UPDATE_INTERVAL = 60
SYMBOL = "BTC/USDT"
TF = "1m"
USE_FLASK = True
USE_PLOT = False

HOST = os.getenv("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.getenv("DASHBOARD_PORT", "5000"))

SYMBOL_NAME = SYMBOL.replace("/", "")
DATA_DIR = "DATA"
LOGS_DIR = "LOGS"
STATIC_DIR = os.path.join(DATA_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

CSV_RAW_PATH = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}.csv")
CSV_ANAL_PATH = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}_anal.csv")
STATE_PATH = os.path.join(STATIC_DIR, "state.json")

logger = Logger(
    name="MainBot",
    tag="[MAIN]",
    logfile=os.path.join(LOGS_DIR, "mainbot.log"),
    console=False
).get_logger()

stop_event = asyncio.Event()

# Включай реальную биржу, если у тебя есть ключи и нервная система
botapi = MockAPI()
# botapi = BybitAPI()  # если хочешь живые ключи и боль


# ------------ Утилиты ------------
def _is_port_open(host: str, port: int) -> bool:
    import socket as _s
    with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False

async def _wait_port(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if _is_port_open(host, port):
            return True
        await asyncio.sleep(0.2)
    return False


# ------------ Торговая логика ------------
async def plot_loop(use_plot: bool) -> None:
    if use_plot:
        logger.info("Запущен графический цикл PlotBot")
        def start_plotbot():
            plotbot = PlotBot(csv_file=CSV_ANAL_PATH, refresh_interval=UPDATE_INTERVAL)
            plotbot.start()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, start_plotbot)

async def tradeornot(bot, signal: int, qty: float = 0.001) -> None:
    if signal == 1:
        logger.info("Сигнал: ПОКУПКА")
        await bot.place_order_async(SYMBOL, "buy", qty=qty)
    elif signal == -1:
        logger.info("Сигнал: ПРОДАЖА")
        await bot.place_order_async(SYMBOL, "sell", qty=qty)

def _stamp_orders_column(df: pd.DataFrame, signal: int) -> pd.DataFrame:
    if "orders" not in df.columns:
        df["orders"] = 0
    if len(df) > 0:
        last_idx = df.index[-1]
        df.loc[last_idx, "orders"] = 1 if signal == 1 else (-1 if signal == -1 else 0)
    return df

async def write_state_fallback(state_path: str) -> None:
    try:
        data = {"balance": {"total": None, "currency": "USDT"}, "positions": [], "updated": pd.Timestamp.utcnow().isoformat()}
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        import json
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Не смог записать fallback state.json: {e}")

async def trading_loop(bot) -> None:
    logger.info(f"Запущен торговый цикл {type(bot).__name__}")
    try:
        while not stop_event.is_set():
            df = await bot.get_ohlcv_async(SYMBOL, timeframe=TF, limit=100)
            # Унифицируем имя времени для дашборда
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})
            df.to_csv(CSV_RAW_PATH, index=False)

            analytic = Analytic(df.copy(), data_name=f"{SYMBOL_NAME}_{TF}")
            signal = analytic.make_strategy(RSIonly_Strategy, rsi={"period": 14, "lower": 30, "upper": 70})

            df = _stamp_orders_column(df, signal)
            df.to_csv(CSV_ANAL_PATH, index=False)

            await tradeornot(bot, signal)
            if hasattr(bot, "update_state"):
                try:
                    await bot.update_state(SYMBOL, STATE_PATH)
                except Exception as e:
                    logger.error(f"update_state упал: {e}")
            else:
                await write_state_fallback(STATE_PATH)

            await asyncio.sleep(UPDATE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("Торговый цикл отменён")
        raise
    finally:
        if hasattr(bot, "close_async"):
            try:
                await bot.close_async()
            except Exception:
                pass
        logger.info("Торговый цикл завершён")


# ------------ main ------------
async def main() -> None:
    flaskproc: Optional[asyncio.subprocess.Process] = None
    raw_popen = None

    if USE_FLASK:
        # поднимаем дашборд в отдельном окне/сессии и пробрасываем хост/порт
        raw_popen = run_flask_in_new_terminal(host=HOST, port=PORT, log_path=os.path.join(LOGS_DIR, "dashboard.out.log"))
        ok = await _wait_port(HOST, PORT, timeout=10)
        if not ok:
            logger.error(f"Дашборд не поднял порт {HOST}:{PORT}. Смотри LOGS/dashboard.out.log")
        else:
            logger.info(f"Дашборд доступен на http://{HOST}:{PORT}")

    try:
        await asyncio.gather(
            trading_loop(botapi),
            plot_loop(USE_PLOT)
        )
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt. Завершаем...")
        stop_event.set()
    except Exception as e:
        logger.error(f"Ошибка верхнего уровня: {e}", exc_info=True)
        stop_event.set()
    finally:
        await asyncio.sleep(0.5)
        if USE_FLASK:
            stop_flask(raw_popen)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt вне asyncio.run — выходим")
