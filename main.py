# === main.py ===
import asyncio
import os
import sys
from typing import Optional

import pandas as pd

# Подключения твоего проекта
from API.bybit_api import BybitAPI  # если захотелось боли в реальном времени
from API.mock_api import MockAPI
from API.dashboard_api import run_flask_in_new_terminal, stop_flask
from BOTS.analbot import Analytic
from BOTS.loggerbot import Logger
from BOTS.PLOTBOTS.plotbot import PlotBot
from STRATEGY.rsi import RSIonly_Strategy
from STRATEGY.XGBstrategy import XGBStrategy

# ------------ Конфиг ------------
UPDATE_INTERVAL = 60  # сек между тиками
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
CSV_ANAL_PATH_RSI = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}_anal.csv")
CSV_ANAL_PATH_XGB = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}_xgb.csv")
STATE_PATH = os.path.join(STATIC_DIR, "state.json")

logger = Logger(
    name="MainBot",
    tag="[MAIN]",
    logfile=os.path.join(LOGS_DIR, "mainbot.log"),
    console=False
).get_logger()

stop_event = asyncio.Event()

# Выбирай API. MockAPI живее всех живых.
botapi = MockAPI()
# botapi = BybitAPI()


# ------------ Утилиты ------------
def _is_port_open(host: str, port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False

async def _wait_port(host: str, port: int, timeout: float = 10.0) -> bool:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if _is_port_open(host, port):
            return True
        await asyncio.sleep(0.2)
    return False

async def write_state_fallback(state_path: str) -> None:
    # Если настоящий API не пишет state.json
    try:
        data = {
            "balance": {"total": None, "currency": "USDT"},
            "positions": [],
            "updated": pd.Timestamp.utcnow().isoformat()
        }
        import json
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Не смог записать fallback state.json: {e}")

def _stamp_orders_column(df: pd.DataFrame, signal: int, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = 0
    if len(df) > 0:
        last_idx = df.index[-1]
        df.loc[last_idx, col] = 1 if signal == 1 else (-1 if signal == -1 else 0)
    return df


# ------------ Plot (опционально) ------------
async def plot_loop(use_plot: bool) -> None:
    if not use_plot:
        return
    logger.info("Запущен графический цикл PlotBot")
    def _start():
        # Рисуем по RSI-файлу, как привык твой фронт
        plotbot = PlotBot(csv_file=CSV_ANAL_PATH_RSI, refresh_interval=UPDATE_INTERVAL)
        plotbot.start()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start)


# ------------ Торговый цикл RSI ------------
async def trading_loop_rsi(bot) -> None:
    logger.info(f"[RSI] Запущен торговый цикл {type(bot).__name__}")
    try:
        while not stop_event.is_set():
            # 1) Забираем данные
            df = await bot.get_ohlcv_async(SYMBOL, timeframe=TF, limit=100)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})

            # 2) Сохраняем сырые данные для спокойствия души
            df.to_csv(CSV_RAW_PATH, index=False)

            # 3) Считаем RSI-аналитику и сохраняем _anal.csv
            analytic = Analytic(df.copy(), data_name=f"{SYMBOL_NAME}_{TF}")
            signal = analytic.make_strategy(
                RSIonly_Strategy,
                rsi={"period": 14, "lower": 30, "upper": 70},
            )

            df = _stamp_orders_column(df, signal, col="orders_rsi")
            df.to_csv(CSV_ANAL_PATH_RSI, index=False)

            # 4) Торгуем
            if signal == 1:
                await bot.place_order_async(SYMBOL, "buy", qty=0.001)
            elif signal == -1:
                await bot.place_order_async(SYMBOL, "sell", qty=0.001)

            # 5) Обновляем состояние для дашборда
            if hasattr(bot, "update_state"):
                try:
                    await bot.update_state(SYMBOL, STATE_PATH)
                except Exception as e:
                    logger.error(f"update_state упал: {e}")
                    await write_state_fallback(STATE_PATH)
            else:
                await write_state_fallback(STATE_PATH)

            await asyncio.sleep(UPDATE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("[RSI] Торговый цикл отменён")
        raise
    finally:
        if hasattr(bot, "close_async"):
            try:
                await bot.close_async()
            except Exception:
                pass
        logger.info("[RSI] Торговый цикл завершён")


# ------------ Торговый цикл XGB ------------
async def trading_loop_xgb(bot) -> None:
    logger.info(f"[XGB] Запущен торговый цикл {type(bot).__name__}")
    try:
        while not stop_event.is_set():
            # 1) Забираем те же данные
            df = await bot.get_ohlcv_async(SYMBOL, timeframe=TF, limit=100)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})

            # 2) Аналитика для XGB. ВАЖНО: НЕ передавать DataFrame в params!
            data_name = f"{SYMBOL_NAME}_{TF}"
            analytic = Analytic(df.copy(), data_name=data_name, output_file="xgb.csv")

            # Никаких df=..., data_name=... в params.
            # Только простые типы, если надо (batch_size, quantization и т.д.)
            signal = analytic.make_strategy(
                XGBStrategy,
                use_cache=True,
                parallel=True
            )

            # 3) Отметим действие в своем CSV и сохраним отдельно
            df = _stamp_orders_column(df, signal, col="orders_xgb")
            df.to_csv(CSV_ANAL_PATH_XGB, index=False)

            # 4) Торгуем поменьше размером, чтобы две стратегии не жрали депозит в обе стороны
            if signal == 1:
                await bot.place_order_async(SYMBOL, "buy", qty=0.0005)
            elif signal == -1:
                await bot.place_order_async(SYMBOL, "sell", qty=0.0005)

            # state.json трогает только RSI-цикл
            await asyncio.sleep(UPDATE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("[XGB] Торговый цикл отменён")
        raise
    finally:
        logger.info("[XGB] Торговый цикл завершён")


# ------------ main ------------
async def main() -> None:
    raw_popen: Optional[object] = None

    if USE_FLASK:
        raw_popen = run_flask_in_new_terminal(
            host=HOST,
            port=PORT,
            log_path=os.path.join(LOGS_DIR, "dashboard.out.log")
        )
        ok = await _wait_port(HOST, PORT, timeout=10)
        if not ok:
            logger.error(f"Дашборд не поднял порт {HOST}:{PORT}. Смотри LOGS/dashboard.out.log")
        else:
            logger.info(f"Дашборд доступен на http://{HOST}:{PORT}")

    try:
        await asyncio.gather(
            trading_loop_rsi(botapi),
            trading_loop_xgb(botapi),
            plot_loop(USE_PLOT),
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
