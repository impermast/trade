"""
Signal aggregation logic for trading strategies.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable
from collections import defaultdict, deque
import numpy as np
import pandas as pd

from CORE.config import Config
from .signals import SignalType, AggregatedDecision, StrategySignal


class SignalAggregator(ABC):
    """Abstract base class for signal aggregation"""
    
    @abstractmethod
    def aggregate(self, signals: List[StrategySignal], **kwargs) -> AggregatedDecision:
        """Aggregates signals into a final decision"""
        pass


class WeightedVotingAggregator(SignalAggregator):
    """Aggregator based on weighted voting"""
    
    def __init__(self, strategy_weights: Optional[Dict[str, float]] = None):
        self.strategy_weights = strategy_weights or Config.TRADING.STRATEGY_WEIGHTS
    
    def aggregate(self, signals: List[StrategySignal], **kwargs) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="No signals from strategies"
            )
        
        # Calculate weighted votes
        weighted_votes = defaultdict(float)
        strategy_votes = {}
        
        for signal in signals:
            weight = self.strategy_weights.get(signal.strategy_name, 1.0)
            weighted_vote = signal.signal * weight * signal.confidence
            weighted_votes[signal.signal] += weighted_vote
            strategy_votes[signal.strategy_name] = signal.signal
        
        # Determine the winning signal
        if weighted_votes[1] > weighted_votes[-1] and weighted_votes[1] > 0.5:
            action = SignalType.BUY
            confidence = min(weighted_votes[1], 1.0)
            reasoning = f"BUY signal with confidence {confidence:.2f}"
        elif weighted_votes[-1] > weighted_votes[1] and weighted_votes[-1] > 0.5:
            action = SignalType.SELL
            confidence = min(weighted_votes[-1], 1.0)
            reasoning = f"SELL signal with confidence {confidence:.2f}"
        else:
            action = SignalType.HOLD
            confidence = 0.0
            reasoning = "Insufficient confidence for action"
        
        return AggregatedDecision(
            action=action,
            confidence=confidence,
            strategy_votes=strategy_votes,
            reasoning=reasoning
        )


class ConsensusAggregator(SignalAggregator):
    """Aggregator based on strategy consensus"""
    
    def __init__(self, min_consensus_ratio: float = 0.7):
        self.min_consensus_ratio = min_consensus_ratio
    
    def aggregate(self, signals: List[StrategySignal], **kwargs) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="No signals from strategies"
            )
        
        # Group signals by type
        signal_counts = defaultdict(int)
        strategy_votes = {}
        
        for signal in signals:
            signal_counts[signal.signal] += 1
            strategy_votes[signal.strategy_name] = signal.signal
        
        total_strategies = len(signals)
        
        # Check consensus for each signal type
        for signal_type, count in signal_counts.items():
            consensus_ratio = count / total_strategies
            if consensus_ratio >= self.min_consensus_ratio:
                action = SignalType(signal_type)
                confidence = consensus_ratio
                reasoning = f"Consensus {consensus_ratio:.1%} for {action.name}"
                
                return AggregatedDecision(
                    action=action,
                    confidence=confidence,
                    strategy_votes=strategy_votes,
                    reasoning=reasoning
                )
        
        # No consensus
        return AggregatedDecision(
            action=SignalType.HOLD,
            confidence=0.0,
            strategy_votes=strategy_votes,
            reasoning=f"No consensus (requires {self.min_consensus_ratio:.1%})"
        )


class AdaptiveAggregator(SignalAggregator):
    """Adaptive aggregator that changes logic based on market conditions"""
    
    def __init__(self, volatility_threshold: float = 0.02):
        self.volatility_threshold = volatility_threshold
        self.voting_aggregator = WeightedVotingAggregator()
        self.consensus_aggregator = ConsensusAggregator()
        self.market_history = deque(maxlen=100)
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculates market volatility"""
        if len(df) < 20:
            return 0.0
        
        returns = df['close'].pct_change().dropna()
        return returns.std()
    
    def _detect_trend(self, df: pd.DataFrame) -> str:
        """Detects market trend"""
        if len(df) < 50:
            return "unknown"
        
        # Simple trend based on SMA
        short_sma = df['close'].rolling(20).mean()
        long_sma = df['close'].rolling(50).mean()
        
        if short_sma.iloc[-1] > long_sma.iloc[-1]:
            return "uptrend"
        elif short_sma.iloc[-1] < long_sma.iloc[-1]:
            return "downtrend"
        else:
            return "sideways"
    
    def aggregate(self, signals: List[StrategySignal], df: Optional[pd.DataFrame] = None, **kwargs) -> AggregatedDecision:
        if not signals:
            return AggregatedDecision(
                action=SignalType.HOLD,
                confidence=0.0,
                strategy_votes={},
                reasoning="No signals from strategies"
            )
        
        # Analyze market conditions
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
        
        # Choose aggregator based on market conditions
        if market_condition == "volatile":
            # In volatile market, use consensus
            decision = self.consensus_aggregator.aggregate(signals)
            decision.reasoning += f" (volatile market, consensus)"
        elif market_condition in ["uptrend", "downtrend"]:
            # In trending market, use weighted voting
            decision = self.voting_aggregator.aggregate(signals)
            decision.reasoning += f" (trending market: {market_condition})"
        else:
            # In normal conditions, use weighted voting
            decision = self.voting_aggregator.aggregate(signals)
            decision.reasoning += " (normal market conditions)"
        
        return decision


class AggregatorFactory:
    """Factory for creating different types of aggregators"""
    
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
        """Creates a custom aggregator"""
        return aggregator_class(**kwargs)