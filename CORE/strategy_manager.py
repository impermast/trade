"""
Strategy Manager - централизованное управление торговыми стратегиями.

Этот модуль:
1. Получает сигналы от всех активных стратегий
2. Агрегирует их с помощью умного алгоритма
3. Принимает финальное решение о покупке/продаже
4. Управляет торговыми циклами
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict, deque
import numpy as np
import pandas as pd

from STRATEGY.base import BaseStrategy
from STRATEGY.rsi import RSIonly_Strategy
from STRATEGY.XGBstrategy import XGBStrategy


class SignalType(Enum):
    """Типы торговых сигналов"""
    BUY = 1
    SELL = -1
    HOLD = 0


class StrategyStatus(Enum):
    """Статус стратегии"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class StrategySignal:
    """Структура сигнала от стратегии"""
    strategy_name: str
    signal: int  # 1, -1, 0
    confidence: float = 1.0  # уверенность в сигнале (0.0 - 1.0)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.signal not in [-1, 0, 1]:
            raise ValueError(f"Signal must be -1, 0, or 1, got {self.signal}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class AggregatedDecision:
    """Финальное решение после агрегации сигналов"""
    action: SignalType
    confidence: float
    strategy_votes: Dict[str, int]  # стратегия -> голос
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not isinstance(self.action, SignalType):
            raise ValueError(f"Action must be SignalType, got {type(self.action)}")


class SignalAggregator(ABC):
    """Абстрактный класс для агрегации сигналов"""
    
    @abstractmethod
    def aggregate(self, signals: List[StrategySignal]) -> AggregatedDecision:
        """Агрегирует сигналы в финальное решение"""
        pass


class WeightedVotingAggregator(SignalAggregator):
    """Агрегатор на основе взвешенного голосования"""
    
    def __init__(self, strategy_weights: Optional[Dict[str, float]] = None):
        self.strategy_weights = strategy_weights or {
            "RSIonly_Strategy": 0.4,
            "XGBStrategy": 0.6
        }
    
    def aggregate(self, signals: List[StrategySignal]) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="Нет сигналов от стратегий"
            )
        
        # Подсчитываем взвешенные голоса
        weighted_votes = defaultdict(float)
        strategy_votes = {}
        
        for signal in signals:
            weight = self.strategy_weights.get(signal.strategy_name, 1.0)
            weighted_vote = signal.signal * weight * signal.confidence
            weighted_votes[signal.signal] += weighted_vote
            strategy_votes[signal.strategy_name] = signal.signal
        
        # Определяем победивший сигнал
        if weighted_votes[1] > weighted_votes[-1] and weighted_votes[1] > 0.5:
            action = SignalType.BUY
            confidence = min(weighted_votes[1], 1.0)
            reasoning = f"BUY сигнал с уверенностью {confidence:.2f}"
        elif weighted_votes[-1] > weighted_votes[1] and weighted_votes[-1] > 0.5:
            action = SignalType.SELL
            confidence = min(weighted_votes[-1], 1.0)
            reasoning = f"SELL сигнал с уверенностью {confidence:.2f}"
        else:
            action = SignalType.HOLD
            confidence = 0.0
            reasoning = "Недостаточно уверенности для действия"
        
        return AggregatedDecision(
            action=action,
            confidence=confidence,
            strategy_votes=strategy_votes,
            reasoning=reasoning
        )


class ConsensusAggregator(SignalAggregator):
    """Агрегатор на основе консенсуса стратегий"""
    
    def __init__(self, min_consensus_ratio: float = 0.7):
        self.min_consensus_ratio = min_consensus_ratio
    
    def aggregate(self, signals: List[StrategySignal]) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="Нет сигналов от стратегий"
            )
        
        # Группируем сигналы по типам
        signal_counts = defaultdict(int)
        strategy_votes = {}
        
        for signal in signals:
            signal_counts[signal.signal] += 1
            strategy_votes[signal.strategy_name] = signal.signal
        
        total_strategies = len(signals)
        
        # Проверяем консенсус для каждого типа сигнала
        for signal_type, count in signal_counts.items():
            consensus_ratio = count / total_strategies
            if consensus_ratio >= self.min_consensus_ratio:
                action = SignalType(signal_type)
                confidence = consensus_ratio
                reasoning = f"Консенсус {consensus_ratio:.1%} для {action.name}"
                
                return AggregatedDecision(
                    action=action,
                    confidence=confidence,
                    strategy_votes=strategy_votes,
                    reasoning=reasoning
                )
        
        # Нет консенсуса
        return AggregatedDecision(
            action=SignalType.HOLD,
            confidence=0.0,
            strategy_votes=strategy_votes,
            reasoning=f"Нет консенсуса (требуется {self.min_consensus_ratio:.1%})"
        )


class AdaptiveAggregator(SignalAggregator):
    """Адаптивный агрегатор, который меняет логику в зависимости от рыночных условий"""
    
    def __init__(self, volatility_threshold: float = 0.02):
        self.volatility_threshold = volatility_threshold
        self.voting_aggregator = WeightedVotingAggregator()
        self.consensus_aggregator = ConsensusAggregator()
        self.market_history = deque(maxlen=100)
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Вычисляет волатильность рынка"""
        if len(df) < 20:
            return 0.0
        
        returns = df['close'].pct_change().dropna()
        return returns.std()
    
    def _detect_trend(self, df: pd.DataFrame) -> str:
        """Определяет тренд рынка"""
        if len(df) < 50:
            return "unknown"
        
        # Простой тренд на основе SMA
        short_sma = df['close'].rolling(20).mean()
        long_sma = df['close'].rolling(50).mean()
        
        if short_sma.iloc[-1] > long_sma.iloc[-1]:
            return "uptrend"
        elif short_sma.iloc[-1] < long_sma.iloc[-1]:
            return "downtrend"
        else:
            return "sideways"
    
    def aggregate(self, signals: List[StrategySignal], df: Optional[pd.DataFrame] = None) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="Нет сигналов от стратегий"
            )
        
        # Анализируем рыночные условия
        market_condition = "normal"
        if df is not None:
            volatility = self._calculate_volatility(df)
            trend = self._detect_trend(df)
            
            if volatility > self.volatility_threshold:
                market_condition = "volatile"
            elif trend == "uptrend":
                market_condition = "uptrend"
            elif trend == "downtrend":
                market_condition = "downtrend"
        
        # Выбираем агрегатор в зависимости от рыночных условий
        if market_condition == "volatile":
            # В волатильном рынке используем консенсус
            decision = self.consensus_aggregator.aggregate(signals)
            decision.reasoning += f" (волатильный рынок, консенсус)"
        elif market_condition in ["uptrend", "downtrend"]:
            # В трендовом рынке используем взвешенное голосование
            decision = self.voting_aggregator.aggregate(signals)
            decision.reasoning += f" (трендовый рынок: {market_condition})"
        else:
            # В обычных условиях используем взвешенное голосование
            decision = self.voting_aggregator.aggregate(signals)
            decision.reasoning += " (обычные рыночные условия)"
        
        return decision


class StrategyManager:
    """Менеджер стратегий - централизованное управление торговыми стратегиями"""
    
    def __init__(
        self,
        aggregator: Optional[SignalAggregator] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.aggregator = aggregator or AdaptiveAggregator()
        
        # Регистрированные стратегии
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_status: Dict[str, StrategyStatus] = {}
        
        # История сигналов и решений
        self.signal_history: List[StrategySignal] = []
        self.decision_history: List[AggregatedDecision] = []
        
        # Конфигурация
        self.max_history_size = 1000
        self.min_signals_for_decision = 1
        
        # Регистрируем стандартные стратегии
        self._register_default_strategies()
    
    def _register_default_strategies(self) -> None:
        """Регистрирует стандартные стратегии"""
        try:
            rsi_strategy = RSIonly_Strategy()
            self.register_strategy("RSI", rsi_strategy)
            self.logger.info("RSI стратегия зарегистрирована")
        except Exception as e:
            self.logger.error(f"Ошибка регистрации RSI стратегии: {e}")
        
        try:
            xgb_strategy = XGBStrategy()
            self.register_strategy("XGB", xgb_strategy)
            self.logger.info("XGB стратегия зарегистрирована")
        except Exception as e:
            self.logger.error(f"Ошибка регистрации XGB стратегии: {e}")
    
    def register_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """Регистрирует новую стратегию"""
        if name in self.strategies:
            self.logger.warning(f"Стратегия {name} уже зарегистрирована, перезаписываем")
        
        self.strategies[name] = strategy
        self.strategy_status[name] = StrategyStatus.ACTIVE
        self.logger.info(f"Стратегия {name} зарегистрирована")
    
    def unregister_strategy(self, name: str) -> None:
        """Удаляет стратегию"""
        if name in self.strategies:
            del self.strategies[name]
            del self.strategy_status[name]
            self.logger.info(f"Стратегия {name} удалена")
    
    def set_strategy_status(self, name: str, status: StrategyStatus) -> None:
        """Устанавливает статус стратегии"""
        if name in self.strategy_status:
            self.strategy_status[name] = status
            self.logger.info(f"Статус стратегии {name} изменен на {status.value}")
    
    def get_all_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        """Получает сигналы от всех активных стратегий"""
        signals = []
        
        for name, strategy in self.strategies.items():
            if self.strategy_status[name] != StrategyStatus.ACTIVE:
                continue
            
            try:
                signal_value = strategy.get_signals(df)
                
                # Вычисляем уверенность на основе исторических данных
                confidence = self._calculate_strategy_confidence(name, signal_value, df)
                
                signal = StrategySignal(
                    strategy_name=name,
                    signal=signal_value,
                    confidence=confidence,
                    metadata={
                        "strategy_type": type(strategy).__name__,
                        "data_length": len(df)
                    }
                )
                signals.append(signal)
                
                self.logger.debug(f"Стратегия {name} выдала сигнал {signal_value} с уверенностью {confidence:.2f}")
                
            except Exception as e:
                self.logger.error(f"Ошибка получения сигнала от стратегии {name}: {e}")
                self.set_strategy_status(name, StrategyStatus.ERROR)
        
        return signals
    
    def _calculate_strategy_confidence(self, strategy_name: str, signal: int, df: pd.DataFrame) -> float:
        """Вычисляет уверенность стратегии на основе исторических данных"""
        if signal == 0:
            return 0.0
        
        # Простая эвристика: больше данных = больше уверенности
        base_confidence = min(len(df) / 100, 1.0)
        
        # Дополнительные факторы можно добавить здесь
        # Например, качество индикаторов, стабильность сигналов и т.д.
        
        return base_confidence
    
    def make_decision(self, df: pd.DataFrame) -> AggregatedDecision:
        """Принимает финальное решение на основе всех сигналов"""
        # Получаем сигналы от всех стратегий
        signals = self.get_all_signals(df)
        
        # Сохраняем историю сигналов
        self.signal_history.extend(signals)
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
        
        # Проверяем минимальное количество сигналов
        if len(signals) < self.min_signals_for_decision:
            decision = AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning=f"Недостаточно сигналов: {len(signals)} < {self.min_signals_for_decision}"
            )
        else:
            # Агрегируем сигналы
            if hasattr(self.aggregator, 'aggregate') and callable(getattr(self.aggregator, 'aggregate')):
                # Проверяем, поддерживает ли агрегатор дополнительный параметр df
                try:
                    decision = self.aggregator.aggregate(signals, df)
                except TypeError:
                    # Если агрегатор не поддерживает df, вызываем без него
                    decision = self.aggregator.aggregate(signals)
            else:
                decision = self.aggregator.aggregate(signals)
        
        # Сохраняем историю решений
        self.decision_history.append(decision)
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size:]
        
        self.logger.info(f"Принято решение: {decision.action.name} с уверенностью {decision.confidence:.2f}")
        self.logger.debug(f"Обоснование: {decision.reasoning}")
        
        return decision
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает статистику производительности стратегий"""
        performance = {}
        
        for name in self.strategies:
            # Анализируем историю сигналов
            strategy_signals = [s for s in self.signal_history if s.strategy_name == name]
            
            if not strategy_signals:
                performance[name] = {
                    "status": self.strategy_status[name].value,
                    "total_signals": 0,
                    "buy_signals": 0,
                    "sell_signals": 0,
                    "hold_signals": 0,
                    "avg_confidence": 0.0
                }
                continue
            
            buy_count = sum(1 for s in strategy_signals if s.signal == 1)
            sell_count = sum(1 for s in strategy_signals if s.signal == -1)
            hold_count = sum(1 for s in strategy_signals if s.signal == 0)
            avg_confidence = np.mean([s.confidence for s in strategy_signals])
            
            performance[name] = {
                "status": self.strategy_status[name].value,
                "total_signals": len(strategy_signals),
                "buy_signals": buy_count,
                "sell_signals": sell_count,
                "hold_signals": hold_count,
                "avg_confidence": avg_confidence
            }
        
        return performance
    
    def get_decision_history(self, limit: Optional[int] = None) -> List[AggregatedDecision]:
        """Возвращает историю решений"""
        if limit is None:
            return self.decision_history.copy()
        return self.decision_history[-limit:]
    
    def clear_history(self) -> None:
        """Очищает историю сигналов и решений"""
        self.signal_history.clear()
        self.decision_history.clear()
        self.logger.info("История сигналов и решений очищена")


# Фабрика для создания агрегаторов
class AggregatorFactory:
    """Фабрика для создания различных типов агрегаторов"""
    
    @staticmethod
    def create_weighted_voting(weights: Optional[Dict[str, float]] = None) -> WeightedVotingAggregator:
        return WeightedVotingAggregator(weights)
    
    @staticmethod
    def create_consensus(min_ratio: float = 0.7) -> ConsensusAggregator:
        return ConsensusAggregator(min_ratio)
    
    @staticmethod
    def create_adaptive(volatility_threshold: float = 0.02) -> AdaptiveAggregator:
        return AdaptiveAggregator(volatility_threshold)
    
    @staticmethod
    def create_custom(aggregator_class: type, **kwargs) -> SignalAggregator:
        """Создает пользовательский агрегатор"""
        return aggregator_class(**kwargs)


if __name__ == "__main__":
    # Тестирование
    logging.basicConfig(level=logging.INFO)
    
    # Создаем менеджер стратегий
    manager = StrategyManager()
    
    # Создаем тестовые данные
    test_df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    # Получаем решение
    decision = manager.make_decision(test_df)
    print(f"Решение: {decision.action.name}")
    print(f"Уверенность: {decision.confidence:.2f}")
    print(f"Обоснование: {decision.reasoning}")
    
    # Показываем производительность стратегий
    performance = manager.get_strategy_performance()
    print("\nПроизводительность стратегий:")
    for name, stats in performance.items():
        print(f"{name}: {stats}")
