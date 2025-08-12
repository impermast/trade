import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from CORE.config import TradingConfig, DashboardConfig, LoggingConfig, APIConfig
from CORE.dashboard_manager import DashboardManager
from CORE.trading_engine import TradingEngine
from CORE.log_manager import LogManager

# Configuration
STATE_PATH = LoggingConfig.STATE_PATH

# === ВАЖНО: логгер инициализируем ПОСЛЕ чистки логов в __main__ ===
logger = None  # будет установлен ниже

# Подключения твоего проекта (после конфигов, но до функций)
from API.bybit_api import BybitAPI  # оставляем на всякий случай
from API.mock_api import MockAPI
from API.dashboard_api import run_flask_in_new_terminal, stop_flask
from CORE.log_manager import Logger
from BOTS.PLOTBOTS.plotbot import PlotBot

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


# ------------ Plot (опционально) ------------
async def plot_loop(use_plot: bool) -> None:
    if not use_plot:
        return
    logger.info("Запущен графический цикл PlotBot")
    def _start():
        plotbot = PlotBot(csv_file=CSV_ANAL_PATH, refresh_interval=TradingConfig.UPDATE_INTERVAL)
        plotbot.start()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _start)


# ------------ Унифицированный торговый движок ------------
from CORE.trading_engine import TradingEngineFactory

async def unified_trading_loop(bot) -> None:
    """Унифицированный торговый цикл для всех стратегий"""
    logger.info(f"Запущен унифицированный торговый цикл {type(bot).__name__}")
    
    try:
        # Создаем торговый движок с адаптивным агрегатором
        trading_engine = TradingEngineFactory.create_standard_engine(bot, logger)
        
        # Запускаем торговый цикл
        await trading_engine.start_trading_loop(stop_event)
        
    except asyncio.CancelledError:
        logger.info("Унифицированный торговый цикл отменён")
        raise
    except Exception as e:
        logger.error(f"Ошибка в унифицированном торговом цикле: {e}", exc_info=True)
        raise
    finally:
        logger.info("Унифицированный торговый цикл завершён")


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
            unified_trading_loop(botapi),
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
    
    # 2) Теперь поднимаем логгер — безопасно, файлы уже подготовлены
    logger = Logger(
        name=LoggingConfig.MAIN_LOGGER_NAME,
        tag=LoggingConfig.MAIN_LOGGER_TAG,
        logfile=LoggingConfig.MAIN_LOGGER_FILE,
        console=False
    ).get_logger()
    
    # Логируем информацию о тримминге
    logger.info(f"[INIT] Trim logs: processed={stats['processed']} changed={stats['changed']} "
                f"saved_bytes={stats['saved_bytes']} (cutoff {LoggingConfig.CLEAN_LOGS_MAX_AGE_HOURS}h)")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt вне asyncio.run — выходим")
