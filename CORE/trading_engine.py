"""
Trading engine for the Trade Project.

This module provides the core trading logic and strategy execution
for the automated trading system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd

from CORE.config import TradingConfig, LoggingConfig
from CORE.security import SecurityManager
from STRATEGY.base import BaseStrategy
from CORE.strategy_manager import StrategyManager, AggregatorFactory, SignalType
from CORE.dashboard_manager import write_state_fallback


class TradingEngine:
    """
    Унифицированный торговый движок для всех стратегий.
    
    Заменяет отдельные торговые циклы RSI и XGB,
    используя StrategyManager для агрегации сигналов.
    """
    
    def __init__(self, api_client=None, strategies: List[BaseStrategy] = None):
        """
        Initialize the TradingEngine.
        
        Args:
            api_client: API client for exchange communication
            strategies: List of trading strategies to use
        """
        self.api_client = api_client
        self.strategies = strategies or []
        self.is_running = False
        self.last_update = None
        
        # Configuration
        self.symbol = TradingConfig.SYMBOL
        self.timeframe = TradingConfig.TIMEFRAME
        self.update_interval = TradingConfig.UPDATE_INTERVAL
        self.target_fraction = TradingConfig.TARGET_FRACTION
        self.min_quantity = TradingConfig.MIN_QUANTITY
        
        # Пути для сохранения данных
        self.csv_raw_path = TradingConfig.get_csv_paths()['raw']
        self.csv_anal_path = TradingConfig.get_csv_paths()['anal']  # единый файл для всех стратегий
        self.state_path = LoggingConfig.STATE_PATH
        
        self.logger.info(f"TradingEngine инициализирован для {self.symbol}")
    
    async def start_trading_loop(self, stop_event: asyncio.Event) -> None:
        """
        Основной торговый цикл.
        
        Args:
            stop_event: Событие для остановки цикла
        """
        self.logger.info(f"Запущен унифицированный торговый цикл для {self.symbol}")
        
        try:
            while not stop_event.is_set():
                await self._trading_iteration()
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Торговый цикл отменён")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка в торговом цикле: {e}", exc_info=True)
            raise
        finally:
            await self._cleanup()
            self.logger.info("Торговый цикл завершён")
    
    async def _trading_iteration(self) -> None:
        """Одна итерация торгового цикла"""
        try:
            # 1. Получаем данные
            df = await self._get_market_data()
            if df is None or df.empty:
                self.logger.warning("Не удалось получить рыночные данные")
                return
            
            # 2. Сохраняем сырые данные
            df.to_csv(self.csv_raw_path, index=False)
            
            # 3. Получаем решение от менеджера стратегий
            decision = self.strategy_manager.make_decision(df)
            
            # 4. Выполняем торговое действие
            await self._execute_trading_decision(decision, df)
            
            # 5. Сохраняем аналитику
            await self._save_analytics(df)
            
            # 6. Обновляем состояние для дашборда
            await self._update_dashboard_state()
            
            # 7. Логируем статистику
            self._log_trading_stats(decision)
            
        except Exception as e:
            self.logger.error(f"Ошибка в итерации торгового цикла: {e}", exc_info=True)
    
    async def _get_market_data(self) -> Optional[pd.DataFrame]:
        """Получает рыночные данные"""
        try:
            df = await self.bot_api.get_ohlcv_async(
                self.symbol,
                timeframe=self.timeframe,
                limit=200
            )
            
            # Нормализуем названия колонок
            if "timestamp" in df.columns and "time" not in df.columns:
                df = df.rename(columns={"timestamp": "time"})
            
            return df
            
        except Exception as e:
            self.logger.error(f"Ошибка получения рыночных данных: {e}")
            return None
    
    async def _execute_trading_decision(
        self,
        decision,
        df: pd.DataFrame
    ) -> None:
        """Выполняет торговое решение"""
        try:
            current_price = float(df["close"].iloc[-1])
            
            if decision.action == SignalType.BUY and self.last_action != 1:
                await self._execute_buy(current_price)
                
            elif decision.action == SignalType.SELL and self.last_action != -1:
                await self._execute_sell(current_price)
                
            elif decision.action == SignalType.HOLD:
                self.hold_count += 1
                self.logger.debug(f"HOLD: {decision.reasoning}")
            
            self.last_decision_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения торгового решения: {e}")
    
    async def _execute_buy(self, price: float) -> None:
        """Выполняет покупку"""
        try:
            # Получаем баланс
            balance = await self.bot_api.get_balance_async()
            usdt_balance = float(balance.get("USDT", 0.0))
            
            # Вычисляем размер позиции
            max_quantity = (usdt_balance * self.target_fraction) / price if price > 0 else 0.0
            quantity = max(0.0, min(max_quantity, self.min_quantity + max_quantity * 0.5))
            
            if quantity > 0:
                # Размещаем ордер
                order_result = await self.bot_api.place_order_async(
                    self.symbol, "buy", qty=quantity
                )
                
                # Обновляем состояние
                self.position_size += quantity
                self.last_action = 1
                self.buy_count += 1
                self.trade_count += 1
                
                self.logger.info(
                    f"BUY: {quantity} {self.symbol} по цене {price:.4f} "
                    f"(баланс: {usdt_balance:.2f} USDT)"
                )
                
                # Логируем детали ордера
                if hasattr(order_result, 'get'):
                    order_id = order_result.get('id', 'unknown')
                    self.logger.info(f"Ордер размещен: {order_id}")
            else:
                self.logger.warning(f"Недостаточно средств для покупки: {usdt_balance:.2f} USDT")
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения покупки: {e}")
    
    async def _execute_sell(self, price: float) -> None:
        """Выполняет продажу"""
        try:
            # Получаем текущие позиции
            positions = await self.bot_api.get_positions_async(self.symbol)
            
            if isinstance(positions, dict):
                position_size = float(positions.get("size", 0.0))
            else:
                position_size = 0.0
            
            # Используем размер из позиции или текущий размер
            quantity = max(position_size, self.position_size)
            
            if quantity > 0:
                # Размещаем ордер
                order_result = await self.bot_api.place_order_async(
                    self.symbol, "sell", qty=quantity
                )
                
                # Обновляем состояние
                self.position_size = 0.0
                self.last_action = -1
                self.sell_count += 1
                self.trade_count += 1
                
                self.logger.info(
                    f"SELL: {quantity} {self.symbol} по цене {price:.4f}"
                )
                
                # Логируем детали ордера
                if hasattr(order_result, 'get'):
                    order_id = order_result.get('id', 'unknown')
                    self.logger.info(f"Ордер размещен: {order_id}")
            else:
                self.logger.warning("Нет позиции для продажи")
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения продажи: {e}")
    
    async def _save_analytics(self, df: pd.DataFrame) -> None:
        """Сохраняет аналитические данные"""
        try:
            # Создаем аналитический DataFrame с сигналами от всех стратегий
            anal_df = df.copy()
            
            # Добавляем колонки для сигналов от всех стратегий
            for strategy_name in self.strategy_manager.strategies:
                signal_col = f"orders_{strategy_name.lower()}"
                if signal_col not in anal_df.columns:
                    anal_df[signal_col] = 0.0
            
            # Добавляем финальное решение
            if "final_decision" not in anal_df.columns:
                anal_df["final_decision"] = 0.0
            
            # Получаем последнее решение
            if self.strategy_manager.decision_history:
                last_decision = self.strategy_manager.decision_history[-1]
                anal_df.loc[anal_df.index[-1], "final_decision"] = last_decision.action.value
            
            # Сохраняем аналитику
            anal_df.to_csv(self.csv_anal_path, index=False)
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения аналитики: {e}")
    
    async def _update_dashboard_state(self) -> None:
        """Обновляет состояние для дашборда"""
        try:
            if hasattr(self.bot_api, "update_state"):
                await self.bot_api.update_state(self.symbol, self.state_path)
            else:
                await write_state_fallback(self.state_path)
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления состояния дашборда: {e}")
            await write_state_fallback(self.state_path)
    
    def _log_trading_stats(self, decision) -> None:
        """Логирует торговую статистику"""
        if self.trade_count % 10 == 0:  # каждые 10 сделок
            self.logger.info(
                f"Статистика торговли: "
                f"Всего: {self.trade_count}, "
                f"BUY: {self.buy_count}, "
                f"SELL: {self.sell_count}, "
                f"HOLD: {self.hold_count}"
            )
    
    async def _cleanup(self) -> None:
        """Очистка ресурсов при завершении"""
        try:
            if hasattr(self.bot_api, "close_async"):
                await self.bot_api.close_async()
        except Exception as e:
            self.logger.error(f"Ошибка при закрытии API: {e}")
    
    def get_trading_stats(self) -> Dict[str, Any]:
        """Возвращает торговую статистику"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "trade_count": self.trade_count,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "hold_count": self.hold_count,
            "position_size": self.position_size,
            "last_action": self.last_action,
            "last_decision_time": self.last_decision_time,
            "strategy_performance": self.strategy_manager.get_strategy_performance()
        }
    
    def get_recent_decisions(self, limit: int = 10) -> List[Any]:
        """Возвращает последние решения"""
        return self.strategy_manager.get_decision_history(limit)
    
    def add_custom_strategy(self, name: str, strategy) -> None:
        """Добавляет пользовательскую стратегию"""
        self.strategy_manager.register_strategy(name, strategy)
        self.logger.info(f"Пользовательская стратегия {name} добавлена")
    
    def set_aggregator(self, aggregator_type: str, **kwargs) -> None:
        """Устанавливает тип агрегатора сигналов"""
        if aggregator_type == "weighted":
            aggregator = AggregatorFactory.create_weighted_voting(**kwargs)
        elif aggregator_type == "consensus":
            aggregator = AggregatorFactory.create_consensus(**kwargs)
        elif aggregator_type == "adaptive":
            aggregator = AggregatorFactory.create_adaptive(**kwargs)
        else:
            raise ValueError(f"Неизвестный тип агрегатора: {aggregator_type}")
        
        self.strategy_manager.aggregator = aggregator
        self.logger.info(f"Агрегатор изменен на {aggregator_type}")


# Фабрика для создания торгового движка
class TradingEngineFactory:
    """Фабрика для создания торгового движка с различными конфигурациями"""
    
    @staticmethod
    def create_standard_engine(
        bot_api,
        logger: Optional[logging.Logger] = None
    ) -> TradingEngine:
        """Создает стандартный торговый движок"""
        return TradingEngine(bot_api, logger=logger)
    
    @staticmethod
    def create_engine_with_custom_aggregator(
        bot_api,
        aggregator_type: str,
        logger: Optional[logging.Logger] = None,
        **aggregator_kwargs
    ) -> TradingEngine:
        """Создает движок с пользовательским агрегатором"""
        engine = TradingEngine(bot_api, logger=logger)
        engine.set_aggregator(aggregator_type, **aggregator_kwargs)
        return engine
    
    @staticmethod
    def create_engine_with_custom_strategies(
        bot_api,
        custom_strategies: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ) -> TradingEngine:
        """Создает движок с пользовательскими стратегиями"""
        engine = TradingEngine(bot_api, logger=logger)
        
        for name, strategy in custom_strategies.items():
            engine.add_custom_strategy(name, strategy)
        
        return engine


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(level=logging.INFO)
    
    # Создаем мок API для тестирования
    class MockBotAPI:
        async def get_ohlcv_async(self, symbol, timeframe, limit):
            return pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=limit, freq='1min'),
                'open': [100] * limit,
                'high': [101] * limit,
                'low': [99] * limit,
                'close': [100 + i * 0.1 for i in range(limit)],
                'volume': [1000 + i * 10 for i in range(limit)]
            })
        
        async def get_balance_async(self):
            return {"USDT": 10000.0}
        
        async def get_positions_async(self, symbol):
            return {"size": 0.0}
        
        async def place_order_async(self, symbol, side, qty):
            return {"id": f"mock_order_{side}_{qty}"}
    
    # Тестируем движок
    async def test_engine():
        mock_api = MockBotAPI()
        engine = TradingEngineFactory.create_standard_engine(mock_api)
        
        # Создаем событие остановки
        stop_event = asyncio.Event()
        
        # Запускаем на несколько итераций
        try:
            for i in range(3):
                await engine._trading_iteration()
                await asyncio.sleep(1)
                stop_event.set()
        except Exception as e:
            logging.error(f"Ошибка тестирования: {e}")
        
        # Показываем статистику
        stats = engine.get_trading_stats()
        logging.info(f"Статистика: {stats}")
    
    # Запускаем тест
    asyncio.run(test_engine())
