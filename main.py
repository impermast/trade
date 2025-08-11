import asyncio
import os
import re
import webbrowser
from typing import Optional, Iterable

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ------------ Конфиг ------------
from CORE.config import TradingConfig, DashboardConfig, PathConfig, LoggingConfig, APIConfig

# Получаем пути к CSV файлам
csv_paths = TradingConfig.get_csv_paths()
CSV_RAW_PATH = csv_paths['raw']
CSV_ANAL_PATH_RSI = csv_paths['rsi_anal']
CSV_ANAL_PATH_XGB = csv_paths['xgb_anal']
STATE_PATH = PathConfig.STATE_PATH

# === ВАЖНО: логгер инициализируем ПОСЛЕ чистки логов в __main__ ===
logger = None  # будет установлен ниже

# Подключения твоего проекта (после конфигов, но до функций)
from API.bybit_api import BybitAPI  # оставляем на всякий случай
from API.mock_api import MockAPI
from API.dashboard_api import run_flask_in_new_terminal, stop_flask
from BOTS.analbot import Analytic
from BOTS.loggerbot import Logger
from BOTS.PLOTBOTS.plotbot import PlotBot
from STRATEGY.rsi import RSIonly_Strategy
from STRATEGY.XGBstrategy import XGBStrategy

stop_event = asyncio.Event()

# Выбирай API. MockAPI живее всех живых.
if APIConfig.USE_MOCK_API:
    botapi = MockAPI()
elif APIConfig.USE_BYBIT_API:
    botapi = BybitAPI()
else:
    botapi = MockAPI()  # fallback


# ------------ Управление логами ------------
from CORE.log_manager import LogManager, clean_logs_by_age

# Создаем экземпляр менеджера логов
log_manager = LogManager()


# ------------ Управление дашбордом и утилиты ------------
from CORE.dashboard_manager import DashboardManager, write_state_fallback

# Создаем экземпляр менеджера дашборда
dashboard_manager = DashboardManager()


def _resolve_rsi_column(df: pd.DataFrame, period: int) -> str:
    col = "rsi" if period == 14 else f"rsi_{period}"
    if col not in df.columns:
        raise ValueError(f"Не найден столбец '{col}' с рассчитанным RSI(period={period}).")
    return col

def _apply_rsi_orders_series(df: pd.DataFrame, period: int, lower: float, upper: float, out_col: str = "orders_rsi") -> None:
    """
    Векторно проставляет сигналы по всей истории:
      +1 BUY  при пересечении уровня lower (30) снизу вверх
      -1 SELL при пересечении уровня upper (70) снизу вверх
    """
    rsi_col = _resolve_rsi_column(df, period)
    rsi = pd.to_numeric(df[rsi_col], errors="coerce")

    prev = rsi.shift(1)
    cross_buy  = (prev < lower) & (rsi >= lower)
    cross_sell = (prev < upper) & (rsi >= upper)

    orders = np.zeros(len(df), dtype=int)
    orders[cross_sell.fillna(False).to_numpy()] = -1
    only_buy = cross_buy.fillna(False) & ~cross_sell.fillna(False)
    orders[only_buy.to_numpy()] = 1

    df[out_col] = orders


# ------------ Plot (опционально) ------------
async def plot_loop(use_plot: bool) -> None:
    if not use_plot:
        return
    logger.info("Запущен графический цикл PlotBot")
    def _start():
        plotbot = PlotBot(csv_file=CSV_ANAL_PATH_RSI, refresh_interval=TradingConfig.UPDATE_INTERVAL)
        plotbot.start()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start)


# ------------ Торговый цикл RSI ------------
async def trading_loop_rsi(bot) -> None:
    logger.info(f"[RSI] Запущен торговый цикл {type(bot).__name__}")
    period = TradingConfig.RSI_PERIOD
    lower, upper = TradingConfig.RSI_LOWER, TradingConfig.RSI_UPPER

    # внутреннее состояние цикла
    last_action = 0
    position_size = 0.0

    try:
        while not stop_event.is_set():
            # 1) Данные
            df = await bot.get_ohlcv_async(TradingConfig.SYMBOL, timeframe=TradingConfig.TIMEFRAME, limit=200)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})
            df.to_csv(CSV_RAW_PATH, index=False)

            # 2) Аналитика
            data_name = f"{TradingConfig.get_symbol_name()}_{TradingConfig.TIMEFRAME}"
            analytic = Analytic(df.copy(), data_name=data_name, output_file="rsi.csv")

            _ = analytic.make_strategy(
                RSIonly_Strategy,
                inplace=False,
                rsi={"period": period, "lower": lower, "upper": upper},
            )

            # 3) Векторная разметка сигналов
            try:
                _apply_rsi_orders_series(analytic.df, period=period, lower=lower, upper=upper)
            except Exception as e:
                logger.warning(f"[RSI] Повторный расчёт RSI через Analytic.make_calc после ошибки: {e}")
                try:
                    analytic.make_calc(indicators=["rsi"], stratparams={"rsi": {"period": period}}, parallel=False)
                    _apply_rsi_orders_series(analytic.df, period=period, lower=lower, upper=upper)
                except Exception as e2:
                    logger.error(f"[RSI] Не удалось обеспечить RSI: {e2}")
                    if "orders_rsi" not in analytic.df.columns:
                        analytic.df["orders_rsi"] = 0

            # 4) Торговое действие (упрощённо)
            last_sig = int(analytic.df["orders_rsi"].iloc[-1])
            price = float(df["close"].iloc[-1])
            bal = await bot.get_balance_async()
            usdt = float(bal.get("USDT", 0.0))
            target_frac = TradingConfig.TARGET_FRACTION
            max_qty = (usdt * target_frac) / price if price > 0 else 0.0

            if last_sig == 1 and last_action != 1:
                qty = max(0.0, min(max_qty, TradingConfig.MIN_QUANTITY + max_qty * 0.5))
                if qty > 0:
                    await bot.place_order_async(TradingConfig.SYMBOL, "buy", qty=qty)
                    position_size += qty
                    last_action = 1
            elif last_sig == -1 and last_action != -1:
                pos = await bot.get_positions_async(TradingConfig.SYMBOL)
                have = float(pos.get("size", 0.0)) if isinstance(pos, dict) else 0.0
                qty = have
                if qty > 0:
                    await bot.place_order_async(TradingConfig.SYMBOL, "sell", qty=qty)
                    position_size = 0.0
                    last_action = -1

            # 5) Сохранение аналитики
            analytic._save_results_to_csv()

            # 6) Обновляем состояние для дашборда
            if hasattr(bot, "update_state"):
                try:
                    await bot.update_state(TradingConfig.SYMBOL, STATE_PATH)
                except Exception as e:
                    logger.error(f"update_state упал: {e}")
                    await write_state_fallback(STATE_PATH)
            else:
                await write_state_fallback(STATE_PATH)

            await asyncio.sleep(TradingConfig.UPDATE_INTERVAL)
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


# ------------ Торговый цикл XGB (сигнал в колонку) ------------
async def trading_loop_xgb(bot) -> None:
    logger.info(f"[XGB] Запущен торговый цикл {type(bot).__name__}")
    try:
        while not stop_event.is_set():
            df = await bot.get_ohlcv_async(TradingConfig.SYMBOL, timeframe=TradingConfig.TIMEFRAME, limit=200)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})

            data_name = f"{TradingConfig.get_symbol_name()}_{TradingConfig.TIMEFRAME}"
            analytic = Analytic(df.copy(), data_name=data_name, output_file="xgb.csv")

            signal = analytic.make_strategy(
                XGBStrategy,
                inplace=False,
                use_cache=True,
                parallel=True
            )

            if "orders_xgb" not in analytic.df.columns:
                analytic.df["orders_xgb"] = 0
            if len(analytic.df) > 0:
                last_idx = analytic.df.index[-1]
                analytic.df.loc[last_idx, "orders_xgb"] = 1 if signal == 1 else (-1 if signal == -1 else 0)

            analytic._save_results_to_csv()

            await asyncio.sleep(TradingConfig.UPDATE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("[XGB] Торговый цикл отменён")
        raise
    finally:
        logger.info("[XGB] Торговый цикл завершён")


# ------------ main ------------
async def main() -> None:
    raw_popen: Optional[object] = None

    if DashboardConfig.USE_FLASK:
        raw_popen = run_flask_in_new_terminal(
            host=DashboardConfig.HOST,
            port=DashboardConfig.PORT,
            log_path=LoggingConfig.DASHBOARD_LOG_FILE
        )
        ok = await dashboard_manager._wait_for_port(DashboardConfig.HOST, DashboardConfig.PORT, timeout=10)
        if not ok:
            logger.error(f"Дашборд не поднял порт {DashboardConfig.HOST}:{DashboardConfig.PORT}. Смотри {LoggingConfig.DASHBOARD_LOG_FILE}")
        else:
            url = DashboardConfig.get_url()
            logger.info(f"Дашборд доступен на {url}")
            try:
                webbrowser.open_new_tab(url)
            except Exception as e:
                logger.warning(f"Не удалось открыть браузер: {e}")

    try:
        await asyncio.gather(
            trading_loop_rsi(botapi),
            trading_loop_xgb(botapi),
            plot_loop(DashboardConfig.USE_PLOT),
        )
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt. Завершаем...")
        stop_event.set()
    except Exception as e:
        logger.error(f"Ошибка верхнего уровня: {e}", exc_info=True)
        stop_event.set()
    finally:
        await asyncio.sleep(0.5)
        if DashboardConfig.USE_FLASK:
            stop_flask(raw_popen)


if __name__ == "__main__":
    # 1) Трим логов ПО ПАТТЕРНУ ТАЙМСТАМПА — только при ручном запуске
    stats = log_manager.clean_old_logs()
    print(f"[INIT] Trim logs: processed={stats['processed']} changed={stats['changed']} "
          f"saved_bytes={stats['saved_bytes']} (cutoff {LoggingConfig.CLEAN_LOGS_MAX_AGE_HOURS}h)")

    # 2) Теперь поднимаем логгер — безопасно, файлы уже подготовлены
    logger = Logger(
        name=LoggingConfig.MAIN_LOGGER_NAME,
        tag=LoggingConfig.MAIN_LOGGER_TAG,
        logfile=LoggingConfig.MAIN_LOGGER_FILE,
        console=False
    ).get_logger()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt вне asyncio.run — выходим")
