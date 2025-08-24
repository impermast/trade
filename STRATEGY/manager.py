"""
Strategy Manager

This module contains the StrategyManager class, which is responsible for
managing the lifecycle of trading strategies, collecting signals, and making
trading decisions by using a signal aggregator.
"""

import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from .base import BaseStrategy
from .signals import StrategySignal, AggregatedDecision, StrategyStatus, SignalType
from .aggregators import SignalAggregator, AdaptiveAggregator


class StrategyManager:
    """Manages the registration, signal collection, and decision making of strategies."""
    
    def __init__(
        self,
        aggregator: Optional[SignalAggregator] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.aggregator = aggregator or AdaptiveAggregator()
        
        # Registered strategies
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_status: Dict[str, StrategyStatus] = {}
        
        # Signal and decision history
        self.signal_history: List[StrategySignal] = []
        self.decision_history: List[AggregatedDecision] = []
        
        # Configuration
        self.max_history_size = 1000
        self.min_signals_for_decision = 1
        
        # Register default strategies from registry
        self._register_strategies_from_registry()

    def _register_strategies_from_registry(self) -> None:
        """Registers strategy instances based on the STRATEGY_REGISTRY and active strategies from config."""
        from . import STRATEGY_REGISTRY
        from CORE.config import Config
        active_strategies = Config.TRADING.STRATEGIES
        self.logger.info(f"Registering active strategies: {active_strategies}")
        for name in active_strategies:
            if name in STRATEGY_REGISTRY:
                try:
                    info = STRATEGY_REGISTRY[name]
                    instance = info["class"](params=info.get("params", {}))
                    self.register_strategy(name, instance)
                except Exception as e:
                    self.logger.error(f"Error registering strategy '{name}': {e}", exc_info=True)
            else:
                self.logger.warning(f"Strategy '{name}' is in config but not found in STRATEGY_REGISTRY.")

    def register_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """Registers a new strategy"""
        if name in self.strategies:
            self.logger.warning(f"Strategy {name} already registered, overwriting")
        
        self.strategies[name] = strategy
        self.strategy_status[name] = StrategyStatus.ACTIVE
        self.logger.info(f"Strategy {name} registered")
    
    def unregister_strategy(self, name: str) -> None:
        """Unregisters a strategy"""
        if name in self.strategies:
            del self.strategies[name]
            del self.strategy_status[name]
            self.logger.info(f"Strategy {name} unregistered")
    
    def set_strategy_status(self, name: str, status: StrategyStatus) -> None:
        """Sets the status of a strategy"""
        if name in self.strategy_status:
            self.strategy_status[name] = status
            self.logger.info(f"Strategy {name} status changed to {status.value}")
    
    def get_all_signals(self, df: pd.DataFrame) -> List[StrategySignal]:
        """Gets signals from all active strategies"""
        signals = []
        
        for name, strategy in self.strategies.items():
            if self.strategy_status[name] != StrategyStatus.ACTIVE:
                continue
            
            try:
                signal_value = strategy.get_signals(df)
                
                # Calculate confidence based on historical data
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
                
                self.logger.debug(f"Strategy {name} emitted signal {signal_value} with confidence {confidence:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error getting signal from strategy {name}: {e}")
                self.set_strategy_status(name, StrategyStatus.ERROR)
        
        return signals
    
    def _calculate_strategy_confidence(self, strategy_name: str, signal: int, df: pd.DataFrame) -> float:
        """Calculates strategy confidence based on historical data"""
        if signal == 0:
            return 0.0
        
        # Simple heuristic: more data = more confidence
        base_confidence = min(len(df) / 100, 1.0)
        
        # Additional factors can be added here
        # For example, quality of indicators, signal stability, etc.
        
        return base_confidence
    
    def make_decision(self, df: pd.DataFrame) -> AggregatedDecision:
        """Makes a final decision based on all signals"""
        # Get signals from all strategies
        signals = self.get_all_signals(df)
        
        # Save signal history
        self.signal_history.extend(signals)
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
        
        # Check minimum number of signals
        if len(signals) < self.min_signals_for_decision:
            decision = AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning=f"Insufficient signals: {len(signals)} < {self.min_signals_for_decision}"
            )
        else:
            # Aggregate signals
            try:
                decision = self.aggregator.aggregate(signals, df=df)
            except TypeError:
                # If aggregator does not support df, call without it
                decision = self.aggregator.aggregate(signals)
        
        # Save decision history
        self.decision_history.append(decision)
        if len(self.decision_history) > self.max_history_size:
            self.decision_history = self.decision_history[-self.max_history_size:]
        
        self.logger.info(f"Decision made: {decision.action.name} with confidence {decision.confidence:.2f}")
        self.logger.debug(f"Reasoning: {decision.reasoning}")
        
        return decision
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Returns strategy performance statistics"""
        performance = {}
        
        for name in self.strategies:
            # Analyze signal history
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
        """Returns decision history"""
        if limit is None:
            return self.decision_history.copy()
        return self.decision_history[-limit:]
    
    def clear_history(self) -> None:
        """Clears signal and decision history"""
        self.signal_history.clear()
        self.decision_history.clear()
        self.logger.info("Signal and decision history cleared")
