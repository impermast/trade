# Strategy Manager - Руководство по использованию

## Обзор

`StrategyManager` - это централизованная система управления торговыми стратегиями, которая:

1. **Агрегирует сигналы** от всех активных стратегий
2. **Принимает умные решения** о покупке/продаже
3. **Управляет торговыми циклами** через `TradingEngine`
4. **Предоставляет аналитику** производительности стратегий

## Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Стратегии     │    │ StrategyManager  │    │ TradingEngine   │
│                 │    │                  │    │                 │
│ • RSI Strategy  │───▶│ • Агрегация      │───▶│ • Торговый      │
│ • XGB Strategy  │    │ • Принятие       │    │   цикл          │
│ • Custom...     │    │   решений        │    │ • Выполнение    │
└─────────────────┘    │ • Мониторинг     │    │   ордеров       │
                       └──────────────────┘    └─────────────────┘
```

## Основные компоненты

### 1. StrategyManager

Центральный класс для управления стратегиями:

```python
from CORE.strategy_manager import StrategyManager

# Создание с настройками по умолчанию
manager = StrategyManager()

# Регистрация пользовательской стратегии
manager.register_strategy("MyStrategy", my_strategy_instance)

# Получение решения
decision = manager.make_decision(market_data)
```

### 2. Агрегаторы сигналов

#### WeightedVotingAggregator
Взвешенное голосование стратегий:

```python
from CORE.strategy_manager import AggregatorFactory

# Создание с пользовательскими весами
weights = {"RSI": 0.4, "XGB": 0.6}
aggregator = AggregatorFactory.create_weighted_voting(weights)
```

#### ConsensusAggregator
Консенсус стратегий:

```python
# Создание с минимальным соотношением консенсуса
aggregator = AggregatorFactory.create_consensus(min_ratio=0.7)
```

#### AdaptiveAggregator (по умолчанию)
Адаптивный выбор агрегатора в зависимости от рыночных условий:

```python
# Автоматически выбирает между взвешенным голосованием и консенсусом
# в зависимости от волатильности и тренда
aggregator = AggregatorFactory.create_adaptive(volatility_threshold=0.02)
```

### 3. TradingEngine

Унифицированный торговый движок:

```python
from CORE.trading_engine import TradingEngineFactory

# Создание стандартного движка
engine = TradingEngineFactory.create_standard_engine(bot_api)

# Запуск торгового цикла
await engine.start_trading_loop(stop_event)
```

## Использование

### Базовое использование

```python
import asyncio
from CORE.strategy_manager import StrategyManager
from CORE.trading_engine import TradingEngineFactory

async def main():
    # 1. Создаем менеджер стратегий
    strategy_manager = StrategyManager()
    
    # 2. Создаем торговый движок
    trading_engine = TradingEngineFactory.create_standard_engine(
        bot_api, 
        strategy_manager=strategy_manager
    )
    
    # 3. Запускаем торговый цикл
    stop_event = asyncio.Event()
    await trading_engine.start_trading_loop(stop_event)

# Запуск
asyncio.run(main())
```

### Добавление пользовательской стратегии

```python
from STRATEGY.base import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(name="MyCustom", indicators=["rsi", "macd"])
    
    def default_params(self):
        return {"rsi": {"period": 14}}
    
    def get_signals(self, df):
        # Ваша логика здесь
        return 1  # BUY, -1 SELL, 0 HOLD

# Регистрация
strategy_manager.register_strategy("Custom", MyCustomStrategy())
```

### Настройка агрегатора

```python
# Изменение типа агрегатора
trading_engine.set_aggregator("consensus", min_ratio=0.8)

# Или создание с пользовательскими настройками
custom_aggregator = AggregatorFactory.create_weighted_voting({
    "RSI": 0.3,
    "XGB": 0.5,
    "Custom": 0.2
})
trading_engine.strategy_manager.aggregator = custom_aggregator
```

## Конфигурация

### Параметры стратегий

```python
# RSI стратегия
rsi_params = {
    "rsi": {
        "period": 14,
        "lower": 30.0,
        "upper": 70.0
    }
}

# XGB стратегия
xgb_params = {
    "model_path": "path/to/model.joblib",
    "features_path": "path/to/features.joblib"
}
```

### Настройки агрегаторов

```python
# Взвешенное голосование
weighted_config = {
    "strategy_weights": {
        "RSI": 0.4,
        "XGB": 0.6
    }
}

# Консенсус
consensus_config = {
    "min_consensus_ratio": 0.7
}

# Адаптивный
adaptive_config = {
    "volatility_threshold": 0.02
}
```

## Мониторинг и аналитика

### Статистика торговли

```python
# Получение статистики
stats = trading_engine.get_trading_stats()
print(f"Всего сделок: {stats['trade_count']}")
print(f"Покупки: {stats['buy_count']}")
print(f"Продажи: {stats['sell_count']}")
```

### Производительность стратегий

```python
# Анализ стратегий
performance = strategy_manager.get_strategy_performance()
for name, stats in performance.items():
    print(f"{name}: {stats['total_signals']} сигналов, "
          f"средняя уверенность: {stats['avg_confidence']:.2f}")
```

### История решений

```python
# Последние решения
recent_decisions = strategy_manager.get_decision_history(limit=10)
for decision in recent_decisions:
    print(f"{decision.timestamp}: {decision.action.name} "
          f"(уверенность: {decision.confidence:.2f})")
```

## Расширенное использование

### Создание пользовательского агрегатора

```python
from CORE.strategy_manager import SignalAggregator, StrategySignal, AggregatedDecision, SignalType

class MyCustomAggregator(SignalAggregator):
    def aggregate(self, signals: List[StrategySignal]) -> AggregatedDecision:
        # Ваша логика агрегации
        total_buy = sum(s.signal * s.confidence for s in signals if s.signal == 1)
        total_sell = sum(s.signal * s.confidence for s in signals if s.signal == -1)
        
        if total_buy > total_sell and total_buy > 0.5:
            action = SignalType.BUY
            confidence = min(total_buy, 1.0)
        elif total_sell > total_buy and total_sell > 0.5:
            action = SignalType.SELL
            confidence = min(total_sell, 1.0)
        else:
            action = SignalType.HOLD
            confidence = 0.0
        
        return AggregatedDecision(
            action=action,
            confidence=confidence,
            strategy_votes={s.strategy_name: s.signal for s in signals},
            reasoning=f"Пользовательская логика: BUY={total_buy:.2f}, SELL={total_sell:.2f}"
        )

# Использование
custom_aggregator = MyCustomAggregator()
strategy_manager.aggregator = custom_aggregator
```

### Интеграция с внешними системами

```python
# Отправка решений в внешнюю систему
async def send_decision_to_external(decision):
    external_data = {
        "action": decision.action.name,
        "confidence": decision.confidence,
        "timestamp": decision.timestamp.isoformat(),
        "reasoning": decision.reasoning
    }
    
    # Отправка через API, WebSocket, etc.
    await external_api.send(external_data)

# Интеграция в торговый цикл
async def _trading_iteration(self):
    # ... получение данных и принятие решения ...
    
    # Отправка во внешнюю систему
    await send_decision_to_external(decision)
```

## Тестирование

### Запуск тестов

```bash
# Тестирование всей архитектуры
python test_strategy_manager.py

# Тестирование отдельных компонентов
python -c "
from CORE.strategy_manager import StrategyManager
manager = StrategyManager()
print('StrategyManager создан успешно')
"
```

### Создание тестовых данных

```python
import pandas as pd
import numpy as np

def create_test_data(periods=100):
    """Создает тестовые рыночные данные"""
    dates = pd.date_range('2024-01-01', periods=periods, freq='1min')
    
    # Простое случайное блуждание
    returns = np.random.normal(0, 0.001, periods)
    prices = 100 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'time': dates,
        'open': prices * (1 + np.random.normal(0, 0.0005, periods)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.001, periods))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.001, periods))),
        'close': prices,
        'volume': np.random.randint(1000, 2000, periods)
    })

# Использование
test_df = create_test_data(1000)
decision = strategy_manager.make_decision(test_df)
```

## Устранение неполадок

### Частые проблемы

1. **Ошибка импорта стратегий**
   ```python
   # Убедитесь, что стратегия наследуется от BaseStrategy
   from STRATEGY.base import BaseStrategy
   
   class MyStrategy(BaseStrategy):
       def get_signals(self, df):
           return 0
   ```

2. **Стратегия не генерирует сигналы**
   ```python
   # Проверьте, что стратегия активна
   print(strategy_manager.strategy_status)
   
   # Проверьте логи
   strategy_manager.logger.setLevel(logging.DEBUG)
   ```

3. **Ошибки в агрегаторе**
   ```python
   # Используйте простой агрегатор для отладки
   simple_agg = AggregatorFactory.create_weighted_voting()
   strategy_manager.aggregator = simple_agg
   ```

### Логирование

```python
import logging

# Настройка детального логирования
logging.basicConfig(level=logging.DEBUG)

# Логирование конкретного компонента
strategy_manager.logger.setLevel(logging.DEBUG)
trading_engine.logger.setLevel(logging.DEBUG)
```

## Производительность

### Оптимизация

1. **Кэширование результатов стратегий**
2. **Параллельная обработка индикаторов**
3. **Ограничение размера истории**
4. **Использование эффективных агрегаторов**

### Мониторинг

```python
import time

# Измерение времени выполнения
start_time = time.time()
decision = strategy_manager.make_decision(df)
execution_time = time.time() - start_time

print(f"Время принятия решения: {execution_time:.3f} сек")
```

## Заключение

`StrategyManager` предоставляет мощную и гибкую архитектуру для управления торговыми стратегиями. Основные преимущества:

- **Централизованное управление** всеми стратегиями
- **Умная агрегация** сигналов с различными алгоритмами
- **Легкое расширение** новыми стратегиями и агрегаторами
- **Мониторинг и аналитика** производительности
- **Унифицированный торговый цикл** через `TradingEngine`

Для получения дополнительной информации обратитесь к исходному коду и примерам использования.
