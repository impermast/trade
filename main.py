import asyncio
import os
import re
import time
from typing import Optional, Iterable

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ------------ Конфиг ------------
UPDATE_INTERVAL = 10   # сек между тиками для симуляции поживее
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

# Возраст логов для обрезки (часы) — можно переопределить через ENV
CLEAN_LOGS_MAX_AGE_HOURS = int(os.getenv("CLEAN_LOGS_MAX_AGE_HOURS", "24"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

CSV_RAW_PATH = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}.csv")
CSV_ANAL_PATH_RSI = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}_anal.csv")
CSV_ANAL_PATH_XGB = os.path.join(DATA_DIR, f"{SYMBOL_NAME}_{TF}_xgb.csv")
STATE_PATH = os.path.join(STATIC_DIR, "state.json")

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
botapi = MockAPI()
# botapi = BybitAPI()


# ------------ Очистка логов по таймстампу ------------

_TS_REGEX = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)\b")

def _parse_log_dt(line: str) -> Optional[datetime]:
    """
    Пытается распарсить таймстамп из начала строки.
    Формат: 'YYYY-MM-DD HH:MM:SS,ffffff'
    Возвращает naive datetime (локальное время).
    """
    m = _TS_REGEX.match(line)
    if not m:
        return None
    ts = m.group("ts")
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")
    except Exception:
        return None

def _iter_trimmed_lines(lines: Iterable[str], cutoff_dt: datetime) -> Iterable[str]:
    """
    Оставляет только записи (и их хвосты), чей заголовок >= cutoff_dt.
    'Хвост' — строки без таймстампа, следующие за сохранённой записью (например, traceback).
    """
    keep_block = False
    for line in lines:
        dt = _parse_log_dt(line)
        if dt is not None:
            keep_block = dt >= cutoff_dt
        if keep_block:
            yield line

def _trim_log_file(path: str, cutoff_dt: datetime) -> tuple[int, int]:
    """
    Тримит один .log-файл по времени.
    Возвращает (bytes_before, bytes_after).
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as src:
            # потоковая фильтрация без загрузки целиком в память
            tmp_path = path + ".tmp~"
            with open(tmp_path, "w", encoding="utf-8") as dst:
                for out_line in _iter_trimmed_lines(src, cutoff_dt):
                    dst.write(out_line)
        before = os.path.getsize(path)
        after = os.path.getsize(tmp_path)
        # атомарная замена
        os.replace(tmp_path, path)
        return before, after
    except FileNotFoundError:
        return (0, 0)
    except IsADirectoryError:
        return (0, 0)
    except Exception:
        # В случае ошибки не трогаем исходник
        try:
            if os.path.exists(path + ".tmp~"):
                os.remove(path + ".tmp~")
        except Exception:
            pass
        return (0, 0)

def _trim_logs_by_age(log_dir: str, max_age_hours: int) -> dict:
    """
    Проходит по *.log в каталоге, оставляет записи за последние max_age_hours.
    Возвращает словарь с короткой статистикой.
    """
    if max_age_hours <= 0:
        return {"processed": 0, "changed": 0, "saved_bytes": 0}

    now_local = datetime.now()  # формат логов — без TZ, считаем локальным временем
    cutoff = now_local - timedelta(hours=max_age_hours)

    processed = 0
    changed = 0
    saved = 0

    try:
        for entry in os.scandir(log_dir):
            if not entry.is_file() or not entry.name.endswith(".log"):
                continue
            processed += 1
            before, after = _trim_log_file(entry.path, cutoff)
            if after > 0 and before >= after:
                if before != after:
                    changed += 1
                    saved += (before - after)
            # если after == 0 — файл стал пустым, это тоже изменение
            elif after == 0 and before > 0:
                changed += 1
                saved += before
    except FileNotFoundError:
        pass

    return {"processed": processed, "changed": changed, "saved_bytes": saved}


# ------------ Утилиты прочие ------------

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
        # может быть ещё без логгера
        try:
            if logger:
                logger.error(f"Не смог записать fallback state.json: {e}")
        except Exception:
            pass

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
        plotbot = PlotBot(csv_file=CSV_ANAL_PATH_RSI, refresh_interval=UPDATE_INTERVAL)
        plotbot.start()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start)


# ------------ Торговый цикл RSI ------------
async def trading_loop_rsi(bot) -> None:
    logger.info(f"[RSI] Запущен торговый цикл {type(bot).__name__}")
    period = 14
    lower, upper = 30.0, 70.0

    # внутреннее состояние цикла
    last_action = 0
    position_size = 0.0

    try:
        while not stop_event.is_set():
            # 1) Данные
            df = await bot.get_ohlcv_async(SYMBOL, timeframe=TF, limit=200)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})
            df.to_csv(CSV_RAW_PATH, index=False)

            # 2) Аналитика
            data_name = f"{SYMBOL_NAME}_{TF}"
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
            target_frac = 0.25
            max_qty = (usdt * target_frac) / price if price > 0 else 0.0

            if last_sig == 1 and last_action != 1:
                qty = max(0.0, min(max_qty, 0.001 + max_qty * 0.5))
                if qty > 0:
                    await bot.place_order_async(SYMBOL, "buy", qty=qty)
                    position_size += qty
                    last_action = 1
            elif last_sig == -1 and last_action != -1:
                pos = await bot.get_positions_async(SYMBOL)
                have = float(pos.get("size", 0.0)) if isinstance(pos, dict) else 0.0
                qty = have
                if qty > 0:
                    await bot.place_order_async(SYMBOL, "sell", qty=qty)
                    position_size = 0.0
                    last_action = -1

            # 5) Сохранение аналитики
            analytic._save_results_to_csv()

            # 6) Обновляем состояние для дашборда
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


# ------------ Торговый цикл XGB (сигнал в колонку) ------------
async def trading_loop_xgb(bot) -> None:
    logger.info(f"[XGB] Запущен торговый цикл {type(bot).__name__}")
    try:
        while not stop_event.is_set():
            df = await bot.get_ohlcv_async(SYMBOL, timeframe=TF, limit=200)
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})

            data_name = f"{SYMBOL_NAME}_{TF}"
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
    # 1) Трим логов ПО ПАТТЕРНУ ТАЙМСТАМПА — только при ручном запуске
    stats = _trim_logs_by_age(LOGS_DIR, CLEAN_LOGS_MAX_AGE_HOURS)
    print(f"[INIT] Trim logs: processed={stats['processed']} changed={stats['changed']} "
          f"saved_bytes={stats['saved_bytes']} (cutoff {CLEAN_LOGS_MAX_AGE_HOURS}h)")

    # 2) Теперь поднимаем логгер — безопасно, файлы уже подготовлены
    logger = Logger(
        name="MainBot",
        tag="[MAIN]",
        logfile=os.path.join(LOGS_DIR, "mainbot.log"),
        console=False
    ).get_logger()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt вне asyncio.run — выходим")
