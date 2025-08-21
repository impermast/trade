"""
Data structures for trading signals and aggregated decisions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any


class SignalType(Enum):
    """Types of trading signals"""
    BUY = 1
    SELL = -1
    HOLD = 0


class StrategyStatus(Enum):
    """Status of a strategy"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class StrategySignal:
    """Structure of a signal from a strategy"""
    strategy_name: str
    signal: int  # 1, -1, 0
    confidence: float = 1.0  # confidence in the signal (0.0 - 1.0)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.signal not in [-1, 0, 1]:
            raise ValueError(f"Signal must be -1, 0, or 1, got {self.signal}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class AggregatedDecision:
    """Final decision after aggregating signals"""
    action: SignalType
    confidence: float
    strategy_votes: Dict[str, int]  # strategy -> vote
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not isinstance(self.action, SignalType):
            raise ValueError(f"Action must be SignalType, got {type(self.action)}")